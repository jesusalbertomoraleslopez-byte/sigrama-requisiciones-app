"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo 3: Panel de Control (Dashboard), Vista Lista Odoo, Kanban y Expedientes
=============================================================================
"""

import os
import re
import datetime
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st
import pandas as pd

from config import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_BORDER,
    AREAS_IMPACTO_DEFAULT,
    ESTATUS_ESPERA_COTIZACION,
    ESTATUS_PENDIENTE_AUTORIZACION,
    ESTATUS_PO_GENERADA,
    ESTATUS_ARCHIVADO,
    STATUS_CONFIG,
    REQUISICIONES_DIR,
    normalize_req_id,
    get_folder_name_for_req,
    get_req_directory
)
from database import (
    load_requisiciones,
    load_cotizaciones,
    get_requisicion_by_id,
    load_catalogos,
    update_requisicion_descripcion,
    update_requisicion_detalles
)
from email_generator import (
    build_consolidated_requisitions_eml,
    get_user_email
)


@st.dialog("✏️ Modificar Descripción y Área de la Requisición")
def modal_editar_descripcion(default_req_id: str = ""):
    """Modal emergente para modificar la descripción breve y el área de impacto de cualquier requisición."""
    df_reqs = load_requisiciones()
    if df_reqs.empty:
        st.warning("No hay requisiciones registradas en la base de datos.")
        return

    catalogos = load_catalogos()
    areas_list = list(catalogos.get("areas_impacto", AREAS_IMPACTO_DEFAULT))

    options = df_reqs["id_requisicion"].tolist()
    labels = {}
    for _, r in df_reqs.iterrows():
        sol_tag = f"[{r.get('folio_solicitud', '')}] " if r.get("folio_solicitud") else ""
        area_tag = f"({r.get('area_impacto', '')}) " if r.get("area_impacto") else ""
        desc_preview = (str(r.get("descripcion_breve") or "")).strip()[:38]
        labels[r["id_requisicion"]] = f"{sol_tag}{r['id_requisicion']} — {area_tag}{desc_preview}"

    idx_default = 0
    if default_req_id and default_req_id in options:
        idx_default = options.index(default_req_id)

    selected_id = st.selectbox(
        "Requisición a Modificar:",
        options=options,
        index=idx_default,
        format_func=lambda x: labels.get(x, x),
        key="modal_edit_sel_req_id"
    )

    rec = df_reqs[df_reqs["id_requisicion"] == selected_id].iloc[0]

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown(f"**Consecutivo Interno:** `{rec.get('folio_solicitud', 'N/A')}`")
        st.markdown(f"**Folio Oficial:** `{rec['id_requisicion']}`")
    with col_info2:
        st.markdown(f"**Solicitante:** {rec.get('solicitante', 'N/A')}")
        st.markdown(f"**Estatus:** {rec.get('estatus', 'N/A')}")

    # Selector de Área de Impacto
    cur_area = rec.get("area_impacto", "")
    area_opts = list(areas_list)
    if cur_area and cur_area not in area_opts:
        area_opts.append(cur_area)
    idx_area = area_opts.index(cur_area) if cur_area in area_opts else 0

    col_m1, col_m2 = st.columns([1.1, 2.3])
    with col_m1:
        new_area = st.selectbox(
            "Área de Impacto:",
            options=area_opts,
            index=idx_area,
            key=f"modal_sel_area_{selected_id}",
            help="Selecciona el área de impacto correspondiente para clasificar y entender mejor la solicitud."
        )
    with col_m2:
        current_desc = str(rec.get("descripcion_breve", "") or "")
        new_desc = st.text_area(
            "Descripción de la Solicitud:",
            value=current_desc,
            height=90,
            help="Escribe la descripción actualizada para esta requisición.",
            key=f"modal_txt_desc_{selected_id}"
        )

    col_btn1, col_btn2 = st.columns([1.2, 1])
    with col_btn1:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True, key="modal_btn_save_desc"):
            if not new_desc.strip():
                st.error("La descripción no puede estar vacía.")
            else:
                success = update_requisicion_detalles(selected_id, nueva_descripcion=new_desc, nueva_area=new_area)
                if success:
                    st.toast(f"✅ Requisición {rec.get('folio_solicitud') or selected_id} actualizada", icon="✅")
                    st.success("✅ Descripción y Área guardadas exitosamente en la base de datos.")
                    st.rerun()
                else:
                    st.error("Ocurrió un error al actualizar el registro.")
    with col_btn2:
        if st.button("Cerrar", use_container_width=True, key="modal_btn_cancel_desc"):
            st.rerun()


def render_dashboard():
    """Renderiza el panel de control ejecutivo con Vista Lista tipo Odoo y Tablero Kanban."""
    st.markdown("""
    <div style="background-color:#FFFFFF; border-left:5px solid #EC2024; padding:16px 20px; border-radius:6px; margin-bottom:18px; box-shadow:0 2px 6px rgba(0,0,0,0.04); border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0; border-bottom:1px solid #E2E8F0;">
        <div style="font-size:18px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.5px;">
            📊 Control Operativo de Requisiciones (Estilo Odoo ERP)
        </div>
        <div style="font-size:13px; color:#64748B; margin-top:4px;">
            Industria SIGRAMA S.A. de C.V. &bull; Gestión centralizada por fases, agrupación multidimensional y expediente digital permanente.
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_reqs = load_requisiciones()
    catalogos = load_catalogos()
    areas_list = catalogos.get("areas_impacto", AREAS_IMPACTO_DEFAULT)

    # =========================================================================
    # BARRA DE CONTROL SUPERIOR ESTILO ODOO (Filtros, Búsqueda y Agrupación)
    # =========================================================================
    with st.container():
        f_col1, f_col2, f_col3, f_col4 = st.columns([2.5, 1.5, 1.5, 1.5])
        
        with f_col1:
            search_text = st.text_input(
                "🔍 Buscar (Folio, Solicitante, Descripción o PO):",
                placeholder="Escribe para filtrar al instante...",
                key="odoo_search_input"
            ).strip().lower()

        with f_col2:
            area_filter = st.selectbox(
                "🎯 Filtrar por Área:",
                options=["Todas las Áreas"] + areas_list,
                index=0,
                key="odoo_area_filter"
            )

        with f_col3:
            group_by = st.selectbox(
                "📂 Agrupar por (Odoo Group):",
                options=["(Sin agrupar)", "Estatus", "Área de Impacto", "Solicitante"],
                index=0,
                key="odoo_group_by"
            )

        with f_col4:
            view_mode = st.radio(
                "Modo de Vista:",
                options=["📋 Lista Odoo", "🗂️ Kanban Odoo"],
                horizontal=True,
                key="odoo_view_mode"
            )

    # Filtros Rápidos por Estado (Odoo Filter Chips)
    c_all, c_esp, c_pen, c_po, c_arc = st.columns(5)
    counts = {
        "all": len(df_reqs),
        "esp": len(df_reqs[df_reqs["estatus"] == ESTATUS_ESPERA_COTIZACION]),
        "pen": len(df_reqs[df_reqs["estatus"] == ESTATUS_PENDIENTE_AUTORIZACION]),
        "po": len(df_reqs[df_reqs["estatus"] == ESTATUS_PO_GENERADA]),
        "arc": len(df_reqs[df_reqs["estatus"] == ESTATUS_ARCHIVADO])
    }

    if "odoo_status_filter" not in st.session_state:
        st.session_state["odoo_status_filter"] = "Todos"

    with c_all:
        if st.button(f"🌐 Todos ({counts['all']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = "Todos"
    with c_esp:
        if st.button(f"⏳ En Espera ({counts['esp']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_ESPERA_COTIZACION
    with c_pen:
        if st.button(f"📋 Pendientes ({counts['pen']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_PENDIENTE_AUTORIZACION
    with c_po:
        if st.button(f"✅ Con PO ({counts['po']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_PO_GENERADA
    with c_arc:
        if st.button(f"📁 Histórico ({counts['arc']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_ARCHIVADO

    # Aplicar Filtros de Estado, Área y Búsqueda
    df_filtered = df_reqs.copy()
    if st.session_state["odoo_status_filter"] != "Todos":
        df_filtered = df_filtered[df_filtered["estatus"] == st.session_state["odoo_status_filter"]]

    if area_filter != "Todas las Áreas":
        df_filtered = df_filtered[df_filtered["area_impacto"] == area_filter]

    if search_text:
        mask = (
            df_filtered["id_requisicion"].str.lower().str.contains(search_text) |
            df_filtered.get("folio_solicitud", pd.Series("", index=df_filtered.index)).str.lower().str.contains(search_text) |
            df_filtered["solicitante"].str.lower().str.contains(search_text) |
            df_filtered["descripcion_breve"].str.lower().str.contains(search_text) |
            df_filtered["folio_po"].str.lower().str.contains(search_text) |
            df_filtered["proveedor_seleccionado"].str.lower().str.contains(search_text)
        )
        df_filtered = df_filtered[mask]

    # Indicador de filtro activo
    if st.session_state["odoo_status_filter"] != "Todos":
        st.caption(f"Filtro activo: **{st.session_state['odoo_status_filter']}** &bull; Mostrando {len(df_filtered)} de {len(df_reqs)} registros")

    # =========================================================================
    # TARJETAS DE INDICADORES CLAVE (KPIS RESUMEN)
    # =========================================================================
    monto_total_est = df_filtered["monto_estimado"].sum()
    monto_total_po = df_filtered[df_filtered["estatus"].isin([ESTATUS_PO_GENERADA, ESTATUS_ARCHIVADO])]["monto_po"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Registros Mostrados", len(df_filtered), delta=f"{len(df_filtered)} requisiciones", delta_color="off")
    k2.metric("Pendientes de Autorización", len(df_filtered[df_filtered["estatus"] == ESTATUS_PENDIENTE_AUTORIZACION]))
    k3.metric("En Espera de Cotización", len(df_filtered[df_filtered["estatus"] == ESTATUS_ESPERA_COTIZACION]))
    k4.metric("Presupuesto en Trámite ($)", f"${monto_total_est:,.2f}")

    st.markdown("---")

    # =========================================================================
    # VISTA 1: LISTA ESTILO ODOO (LIST VIEW CON ODOO BADGES Y AGRUPACIÓN)
    # =========================================================================
    if view_mode == "📋 Lista Odoo":
        col_list_title, col_btn_modal = st.columns([2.7, 1.3])
        with col_list_title:
            st.markdown(f"##### 📋 Listado Oficial de Requisiciones ({len(df_filtered)})")
        with col_btn_modal:
            if st.button("✏️ Modificar Descripción y Área", key="btn_open_modal_edit_desc", use_container_width=True, help="Modifica la descripción técnica o el área de impacto de cualquier requisición"):
                modal_editar_descripcion()

        if df_filtered.empty:
            st.info("No hay requisiciones que coincidan con los filtros seleccionados.")
            return

        # Controles de Ordenamiento y Resaltado de Color (Estilo Remisiones)
        ord_col1, ord_col2 = st.columns([1.3, 1.3])
        with ord_col1:
            sort_order = st.selectbox(
                "↕️ Ordenar Requisiciones por:",
                options=[
                    "⚡ Últimas subidas / registradas primero (Nuevas arriba)",
                    "📅 Fecha de Documento: Más recientes primero",
                    "📅 Fecha de Documento: Más antiguas primero (Cronológico)",
                    "🏷️ Consecutivo Interno: Mayor a menor (SOL descendente)",
                    "🏷️ Consecutivo Interno: Menor a mayor (SOL ascendente)",
                    "🔢 Folio Oficial: Mayor a menor (REQ descendente)",
                    "🔢 Folio Oficial: Menor a mayor (REQ ascendente)"
                ],
                index=0,
                key="odoo_sort_order"
            )
        with ord_col2:
            highlight_mode = st.selectbox(
                "🎨 Resaltado de Nuevas / Últimas (Estilo Remisiones):",
                options=[
                    "✨ Resaltar últimas requisiciones cargadas (Amarillo #FFF59D)",
                    "⚪ Sin resaltar color"
                ],
                index=0,
                key="odoo_highlight_mode"
            )

        # Funciones para extraer números de orden
        def extract_req_num(id_val):
            id_str = str(id_val).strip()
            match = re.search(r'\d+', id_str)
            if match:
                return int(match.group(0))
            return 0

        def extract_sol_num(id_val):
            id_str = str(id_val).strip()
            match = re.search(r'\d+', id_str)
            if match:
                return int(match.group(0))
            return 0

        # Determinar folios de las últimas requisiciones cargadas
        max_reg = df_reqs["fecha_registro"].max() if "fecha_registro" in df_reqs.columns and not df_reqs.empty else ""
        ultimas_reg_folios = set(df_reqs[df_reqs["fecha_registro"] == max_reg]["id_requisicion"]) if max_reg else set()
        top5_cargadas = set(df_reqs.assign(_snum=df_reqs.get("folio_solicitud", pd.Series("", index=df_reqs.index)).apply(extract_sol_num)).sort_values(by=["fecha_registro", "_snum"], ascending=[False, False]).head(5)["id_requisicion"]) if not df_reqs.empty else set()
        max_date = df_reqs["fecha_requisicion"].max() if not df_reqs.empty else ""
        ultimas_fecha_folios = set(df_reqs[df_reqs["fecha_requisicion"] == max_date]["id_requisicion"]) if max_date else set()
        top5_folios = set(df_reqs.assign(_fnum=df_reqs["id_requisicion"].apply(extract_req_num)).sort_values(by="_fnum", ascending=False).head(5)["id_requisicion"]) if not df_reqs.empty else set()
        session_recent = set(st.session_state.get("ultimos_folios_cargados", []))
        ultimas_cargadas_set = session_recent.union(ultimas_reg_folios).union(top5_cargadas).union(ultimas_fecha_folios).union(top5_folios)

        # Aplicar ordenamiento al DataFrame filtrado
        df_filtered["_sort_num"] = df_filtered["id_requisicion"].apply(extract_req_num)
        df_filtered["_sort_sol"] = df_filtered.get("folio_solicitud", pd.Series("", index=df_filtered.index)).apply(extract_sol_num)
        df_filtered["_reg_str"] = df_filtered.get("fecha_registro", pd.Series("", index=df_filtered.index)).astype(str)

        if "Últimas subidas" in sort_order:
            df_filtered = df_filtered.sort_values(by=["_reg_str", "_sort_sol", "fecha_requisicion", "_sort_num"], ascending=[False, False, False, False])
        elif "Fecha de Documento: Más recientes primero" in sort_order or "Más recientes primero" in sort_order:
            df_filtered = df_filtered.sort_values(by=["fecha_requisicion", "_reg_str", "_sort_sol", "_sort_num"], ascending=[False, False, False, False])
        elif "Fecha de Documento: Más antiguas primero" in sort_order or "Más antiguas primero" in sort_order:
            df_filtered = df_filtered.sort_values(by=["fecha_requisicion", "_reg_str", "_sort_sol", "_sort_num"], ascending=[True, True, True, True])
        elif "Consecutivo Interno: Mayor a menor" in sort_order:
            df_filtered = df_filtered.sort_values(by=["_sort_sol", "_reg_str", "fecha_requisicion"], ascending=[False, False, False])
        elif "Consecutivo Interno: Menor a mayor" in sort_order:
            df_filtered = df_filtered.sort_values(by=["_sort_sol", "_reg_str", "fecha_requisicion"], ascending=[True, True, True])
        elif "Folio Oficial: Mayor a menor" in sort_order:
            df_filtered = df_filtered.sort_values(by=["_sort_num", "fecha_requisicion"], ascending=[False, False])
        elif "Folio Oficial: Menor a mayor" in sort_order:
            df_filtered = df_filtered.sort_values(by=["_sort_num", "fecha_requisicion"], ascending=[True, True])

        df_filtered = df_filtered.drop(columns=["_sort_num", "_sort_sol", "_reg_str"]).reset_index(drop=True)

        # Leyenda de color si está activo el resaltado
        if "Amarillo" in highlight_mode and ultimas_cargadas_set:
            recientes_visibles = len(ultimas_cargadas_set.intersection(set(df_filtered["id_requisicion"])))
            st.markdown(f"""
            <div style="background-color:#FFFDE7; border:1px solid #FFE082; border-left:4px solid #FBC02D; padding:7px 14px; border-radius:6px; margin:8px 0 12px 0; font-size:12.5px; color:#424242; display:flex; align-items:center; gap:8px;">
                <span>✨ <strong>Filas resaltadas en amarillo (#FFF59D):</strong> Requisiciones más recientes / últimas cargadas al sistema ({recientes_visibles} visibles en este listado).</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background-color:#F0FDF4; border:1px solid #BBF7D0; border-left:4px solid #16A34A; padding:8px 14px; border-radius:6px; margin:4px 0 10px 0; font-size:12.5px; color:#14532D; display:flex; align-items:center; gap:8px;">
            <span>✏️ <strong>Edición Directa en la Tabla:</strong> Puedes hacer doble clic en cualquier celda de <strong>Descripción</strong> para escribir directamente, o hacer clic en <strong>Área de Impacto</strong> para elegir el área deseada (Producción, Laser, Lijado, Doblez, Pintura, Embarque, Calidad, Inspección, etc.). Los cambios se guardan automáticamente en la base de datos.</span>
        </div>
        """, unsafe_allow_html=True)

        # Función auxiliar para renderizar una tabla de registros estilo Odoo con casillas de verificación
        def render_odoo_table_section(sub_df: pd.DataFrame, group_title: str = "", table_key: str = "tabla_odoo_main"):
            if group_title:
                sub_total_monto = sub_df["monto_estimado"].sum()
                st.markdown(f"""
                <div style="background-color:#F1F5F9; border-left:4px solid #0F172A; padding:8px 14px; border-radius:4px; margin:16px 0 8px 0; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:800; font-size:13px; color:#0F172A; text-transform:uppercase;">📂 {group_title} ({len(sub_df)})</span>
                    <span style="font-size:12px; font-weight:700; color:#475569;">Subtotal: ${sub_total_monto:,.2f} MXN</span>
                </div>
                """, unsafe_allow_html=True)

            # Formatear datos para presentación impecable
            display_df = sub_df.reset_index(drop=True).copy()
            
            # Formatear montos con moneda
            display_df["Interno"] = display_df.get("folio_solicitud", "")
            display_df["Monto ($)"] = display_df["monto_estimado"].apply(lambda v: f"${float(v):,.2f}" if float(v) > 0 else "-")
            display_df["Folio"] = display_df["id_requisicion"]
            display_df["Fecha"] = display_df["fecha_requisicion"]
            display_df["Solicitante"] = display_df["solicitante"].apply(lambda s: s.split("(")[0].strip() if "(" in s else s)
            display_df["Área"] = display_df["area_impacto"]
            display_df["Descripción"] = display_df["descripcion_breve"]
            display_df["Cot."] = display_df["num_cotizaciones"].astype(int)
            display_df["Estatus Odoo"] = display_df["estatus"]
            display_df["Folio PO"] = display_df["folio_po"].apply(lambda p: p if p else "-")
            display_df.insert(0, "Sel.", False)

            cols_to_show = ["Sel.", "Interno", "Folio", "Fecha", "Estatus Odoo", "Área", "Solicitante", "Descripción", "Cot.", "Monto ($)", "Folio PO"]
            
            # Aplicar estilo de color a las últimas cargadas (exactamente como en Remisiones #FFF59D)
            if "Amarillo" in highlight_mode:
                def highlight_recientes(row):
                    is_recent = row["Folio"] in ultimas_cargadas_set
                    return ['background-color: #FFF59D; color: #0F172A;' if is_recent else '' for _ in row]
                data_to_render = display_df[cols_to_show].style.apply(highlight_recientes, axis=1)
            else:
                data_to_render = display_df[cols_to_show]

            # Renderizar con st.data_editor: permite editar 'Descripción' y 'Área' directamente en las celdas
            edited_table = st.data_editor(
                data_to_render,
                use_container_width=True,
                hide_index=True,
                key=table_key,
                column_config={
                    "Sel.": st.column_config.CheckboxColumn("✉️", help="Marca la casilla para incluir en el paquete de correo .eml", default=False, width="small"),
                    "Interno": st.column_config.TextColumn("Interno (SOL)", width="small", help="Consecutivo Interno Planta Metales (SOL-XXXXX)", disabled=True),
                    "Folio": st.column_config.TextColumn("Folio (REQ)", width="small", help="Folio Oficial de Requisición", disabled=True),
                    "Fecha": st.column_config.TextColumn("Fecha", width="small", disabled=True),
                    "Estatus Odoo": st.column_config.TextColumn("Estatus", width="medium", disabled=True),
                    "Área": st.column_config.SelectboxColumn("Área de Impacto", width="medium", options=areas_list, required=True, help="Haz clic para seleccionar el área de la requisición"),
                    "Solicitante": st.column_config.TextColumn("Solicitante", width="medium", disabled=True),
                    "Descripción": st.column_config.TextColumn("Descripción", width="large", required=True, help="Haz doble clic o escribe para modificar la descripción directamente"),
                    "Cot.": st.column_config.NumberColumn("Cot.", width="small", disabled=True),
                    "Monto ($)": st.column_config.TextColumn("Monto Estimado", width="small", disabled=True),
                    "Folio PO": st.column_config.TextColumn("Orden (PO)", width="small", disabled=True)
                }
            )

            # Detectar y guardar cambios automáticos realizados directamente en la tabla
            edits_saved = []
            if isinstance(edited_table, pd.DataFrame) and len(edited_table) == len(display_df):
                for i in range(len(display_df)):
                    orig_d = str(display_df.iloc[i]["Descripción"] or "").strip()
                    new_d = str(edited_table.iloc[i]["Descripción"] or "").strip()
                    orig_a = str(display_df.iloc[i]["Área"] or "").strip()
                    new_a = str(edited_table.iloc[i]["Área"] or "").strip()

                    if orig_d != new_d or orig_a != new_a:
                        f_id = display_df.iloc[i]["Folio"]
                        s_id = display_df.iloc[i]["Interno"]
                        update_requisicion_detalles(f_id, nueva_descripcion=new_d, nueva_area=new_a)
                        edits_saved.append(f"{s_id or f_id}")

            if edits_saved:
                st.toast(f"✅ Guardado en base de datos: {', '.join(edits_saved)}", icon="💾")
                st.rerun()

            # Extraer folios con casilla seleccionada para el panel de correo
            sel_folios = []
            if isinstance(edited_table, pd.DataFrame) and "Sel." in edited_table.columns:
                for i in range(len(edited_table)):
                    if bool(edited_table.iloc[i]["Sel."]) is True:
                        sel_folios.append(edited_table.iloc[i]["Folio"])

            return sel_folios, display_df

        selected_folios = []

        # Si el usuario seleccionó "Agrupar por"
        if group_by == "Estatus":
            for idx_grp, est_name in enumerate([ESTATUS_PENDIENTE_AUTORIZACION, ESTATUS_ESPERA_COTIZACION, ESTATUS_PO_GENERADA, ESTATUS_ARCHIVADO]):
                subset = df_filtered[df_filtered["estatus"] == est_name]
                if not subset.empty:
                    with st.expander(f"📁 {est_name} ({len(subset)}) — Subtotal: ${subset['monto_estimado'].sum():,.2f} MXN", expanded=(est_name == ESTATUS_PENDIENTE_AUTORIZACION or est_name == ESTATUS_ESPERA_COTIZACION)):
                        sel_grp_folios, _ = render_odoo_table_section(subset, table_key=f"tabla_odoo_estatus_{idx_grp}")
                        selected_folios.extend(sel_grp_folios)

        elif group_by == "Área de Impacto":
            for idx_grp, area_name in enumerate(sorted(df_filtered["area_impacto"].unique())):
                subset = df_filtered[df_filtered["area_impacto"] == area_name]
                if not subset.empty:
                    with st.expander(f"🎯 {area_name} ({len(subset)}) — Subtotal: ${subset['monto_estimado'].sum():,.2f} MXN", expanded=True):
                        sel_grp_folios, _ = render_odoo_table_section(subset, table_key=f"tabla_odoo_area_{idx_grp}")
                        selected_folios.extend(sel_grp_folios)

        elif group_by == "Solicitante":
            for idx_grp, sol_name in enumerate(sorted(df_filtered["solicitante"].unique())):
                subset = df_filtered[df_filtered["solicitante"] == sol_name]
                if not subset.empty:
                    with st.expander(f"👤 {sol_name} ({len(subset)}) — Subtotal: ${subset['monto_estimado'].sum():,.2f} MXN", expanded=False):
                        sel_grp_folios, _ = render_odoo_table_section(subset, table_key=f"tabla_odoo_sol_{idx_grp}")
                        selected_folios.extend(sel_grp_folios)

        else:
            # Lista plana directa
            sel_master_folios, _ = render_odoo_table_section(df_filtered, table_key="tabla_odoo_master_selection")
            selected_folios.extend(sel_master_folios)

        # Barra de pie de tabla estilo Odoo (Totales)
        st.markdown(f"""
        <div style="background-color:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:10px 16px; margin-top:10px; display:flex; justify-content:space-between; align-items:center; font-size:12.5px;">
            <span><strong>Total de Requisiciones en Lista:</strong> {len(df_filtered)}</span>
            <span><strong>Monto Total Acumulado:</strong> <span style="font-size:14px; font-weight:800; color:#0F172A;">${monto_total_est:,.2f} MXN</span></span>
        </div>
        """, unsafe_allow_html=True)

        # =====================================================================
        # PANEL DE ACCIÓN: GENERACIÓN DE CORREO (.EML) CONSOLIDADO DE AUTORIZACIÓN
        # =====================================================================
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        if selected_folios:
            # Eliminar duplicados preservando orden
            unique_folios = list(dict.fromkeys(selected_folios))
            selected_records = [df_reqs[df_reqs["id_requisicion"] == f].iloc[0].to_dict() for f in unique_folios if not df_reqs[df_reqs["id_requisicion"] == f].empty]

            # Sincronizar automáticamente con el expediente digital inferior
            if unique_folios:
                st.session_state["selected_dossier_id"] = unique_folios[0]

            # -----------------------------------------------------------------
            # PANEL DE ACCIÓN RÁPIDA: MODIFICAR DESCRIPCIÓN Y ÁREA
            # -----------------------------------------------------------------
            with st.expander(f"✏️ Modificar Descripción y Área de la Solicitud ({len(unique_folios)} marcada(s))", expanded=True):
                if len(unique_folios) == 1:
                    target_rec = selected_records[0]
                    t_id = target_rec["id_requisicion"]
                    t_sol = target_rec.get("folio_solicitud", "")
                    t_desc = str(target_rec.get("descripcion_breve", "") or "")
                    cur_area = target_rec.get("area_impacto", "")

                    area_opts = list(areas_list)
                    if cur_area and cur_area not in area_opts:
                        area_opts.append(cur_area)
                    idx_area = area_opts.index(cur_area) if cur_area in area_opts else 0

                    st.markdown(f"**Requisición:** `{t_sol}` / `{t_id}` &bull; **Solicitante:** {target_rec.get('solicitante', '')}")
                    c_ar, c_desc = st.columns([1.1, 2.3])
                    with c_ar:
                        new_area_input = st.selectbox(
                            "Área de Impacto:",
                            options=area_opts,
                            index=idx_area,
                            key=f"quick_edit_area_{t_id}",
                            help="Cambia el área para mejorar la clasificación y el entendimiento de la requisición."
                        )
                    with c_desc:
                        new_desc_input = st.text_area(
                            "Descripción técnica / comercial:",
                            value=t_desc,
                            height=80,
                            key=f"quick_edit_desc_{t_id}"
                        )
                    if st.button("💾 Guardar Cambios (Descripción y Área)", key=f"btn_save_desc_quick_{t_id}", type="primary", use_container_width=True):
                        if update_requisicion_detalles(t_id, nueva_descripcion=new_desc_input, nueva_area=new_area_input):
                            st.toast(f"✅ Requisición {t_sol or t_id} actualizada", icon="✅")
                            st.success(f"✅ Descripción y Área de {t_sol or t_id} guardadas exitosamente.")
                            st.rerun()
                else:
                    target_id = st.selectbox(
                        "Selecciona la requisición cuya descripción y área deseas editar:",
                        options=unique_folios,
                        format_func=lambda x: f"[{next((r.get('folio_solicitud','') for r in selected_records if r['id_requisicion'] == x), '')}] {x} — ({next((r.get('area_impacto','') for r in selected_records if r['id_requisicion'] == x), '')}) {str(next((r.get('descripcion_breve','') for r in selected_records if r['id_requisicion'] == x), ''))[:40]}",
                        key="sel_target_edit_multi"
                    )
                    target_rec = next(r for r in selected_records if r["id_requisicion"] == target_id)
                    t_sol = target_rec.get("folio_solicitud", "")
                    t_desc = str(target_rec.get("descripcion_breve", "") or "")
                    cur_area = target_rec.get("area_impacto", "")

                    area_opts = list(areas_list)
                    if cur_area and cur_area not in area_opts:
                        area_opts.append(cur_area)
                    idx_area = area_opts.index(cur_area) if cur_area in area_opts else 0

                    st.markdown(f"**Requisición:** `{t_sol}` / `{target_id}` &bull; **Solicitante:** {target_rec.get('solicitante', '')}")
                    c_ar, c_desc = st.columns([1.1, 2.3])
                    with c_ar:
                        new_area_input = st.selectbox(
                            "Área de Impacto:",
                            options=area_opts,
                            index=idx_area,
                            key=f"quick_edit_area_{target_id}",
                            help="Cambia el área para mejorar la clasificación y el entendimiento de la requisición."
                        )
                    with c_desc:
                        new_desc_input = st.text_area(
                            "Descripción técnica / comercial:",
                            value=t_desc,
                            height=80,
                            key=f"quick_edit_desc_{target_id}"
                        )
                    if st.button("💾 Guardar Cambios (Descripción y Área)", key=f"btn_save_desc_quick_{target_id}", type="primary", use_container_width=True):
                        if update_requisicion_detalles(target_id, nueva_descripcion=new_desc_input, nueva_area=new_area_input):
                            st.toast(f"✅ Requisición {t_sol or target_id} actualizada", icon="✅")
                            st.success(f"✅ Descripción y Área de {t_sol or target_id} guardadas exitosamente.")
                            st.rerun()
            
            total_est_sel = sum(float(r.get("monto_estimado", 0.0) or 0.0) for r in selected_records)
            folios_str = ", ".join(unique_folios)

            # Contar adjuntos PDF disponibles físicamente en las carpetas
            pdf_adjuntos_count = 0
            for r in selected_records:
                fdir = get_req_directory(r["id_requisicion"])
                if fdir.exists():
                    pdf_adjuntos_count += len(list(fdir.glob("*.pdf")))

            st.markdown(f"""
            <div style="background-color:#FFFFFF; border:1px solid #CBD5E1; border-left:4px solid #EC2024; border-radius:8px; padding:14px 18px; margin:14px 0 10px 0; box-shadow:0 2px 6px rgba(0,0,0,0.03);">
                <div style="font-size:14px; font-weight:800; color:#111111; font-family:'Montserrat', sans-serif;">
                    📩 Solicitud de Autorización por Correo (.eml) — {len(selected_records)} Requisición(es) Seleccionada(s)
                </div>
                <div style="font-size:12px; color:#64748B; margin-top:2px;">
                    Se generará el borrador RFC 822 (.eml) con el saludo respetuoso a Ing. Lorena Hernandez, el cuadro comparativo consolidado y todos los expedientes PDF adjuntos.
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_acc_left, col_acc_right = st.columns([1.1, 1.3])

            with col_acc_left:
                st.markdown(f"📌 **Folios marcados con casilla ({len(selected_records)}):**")
                st.write(f"`{folios_str}`")
                
                # Obtener valores actuales de seguimiento para el resumen lateral
                dias_aut_val = st.session_state.get("eml_dias_aut_batch", 3)
                plazo_po_val = st.session_state.get("eml_plazo_po_batch", "1 semana posterior a autorización")
                st.markdown(f"""
                <div style="background-color:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px; font-size:12px; color:#334155;">
                    <div>&bull; <strong>Presupuesto total del paquete:</strong> <span style="font-size:15px; font-weight:900; color:#EC2024;">${total_est_sel:,.2f} MXN</span></div>
                    <div style="margin-top:4px;">&bull; <strong>Documentos PDF adjuntos:</strong> <span style="font-weight:700; color:#0F172A;">{pdf_adjuntos_count} archivo(s)</span> (requisiciones originales y cotizaciones).</div>
                    <div style="margin-top:4px;">&bull; <strong>Seguimiento Autorización:</strong> <span style="font-weight:700; color:#B45309;">{dias_aut_val} días hábiles</span> &bull; <strong>PO:</strong> <span style="font-weight:700; color:#0F172A;">{plazo_po_val}</span></div>
                    <div style="margin-top:4px;">&bull; <strong>Logotipo SIGRAMA:</strong> Incrustado inline nativo (160px) con borde institucional.</div>
                </div>
                """, unsafe_allow_html=True)

            with col_acc_right:
                usuario_actual_firma = st.session_state.get("usuario") or "Jesús Alberto Morales López"
                correo_remitente_auto = get_user_email(usuario_actual_firma)
                de_default = f"{usuario_actual_firma} <{correo_remitente_auto}>"

                cf0, cf1 = st.columns(2)
                with cf0:
                    eml_from = st.text_input("De (Remitente que descarga):", value=de_default, key="eml_from_batch", help="Cuenta corporativa de la persona que descarga y envía el correo desde Outlook.")
                with cf1:
                    eml_to = st.text_input("Para (Destinatario):", value="Ing. Lorena Hernandez <lhernandez@sigrama.com.mx>", key="eml_to_batch")

                cf2, cf3 = st.columns(2)
                with cf2:
                    eml_cc = st.text_input("Con copia (Cc):", value="Bryan Alejandro Flores Mancinas <bryan.mancinas@sigrama.com.mx>; Cruz Eduardo Carreon Rios <cruz.carreon@sigrama.com.mx>; jose.fernandez@sigrama.com.mx; Luis Alfredo Quintana Palma <luis.quintana@sigrama.com.mx>; Jesus Alberto Morales Lopez <jesus.morales@sigrama.com.mx>", key="eml_cc_batch")
                with cf3:
                    eml_firma = st.text_input("Firma Solicitante:", value=usuario_actual_firma, key="eml_firma_batch")

                cf4, cf5, cf6 = st.columns([1.1, 0.9, 1.2])
                with cf4:
                    eml_planta = st.selectbox(
                        "🏭 Planta:",
                        options=["Planta Metales", "Planta Juan Escutia"],
                        index=0,
                        key="eml_planta_batch"
                    )
                with cf5:
                    eml_dias_aut = st.number_input(
                        "🚩 Días Aut.:",
                        min_value=1,
                        max_value=30,
                        value=3,
                        step=1,
                        help="Días hábiles para recibir visto bueno. Activa recordatorio en Outlook.",
                        key="eml_dias_aut_batch"
                    )
                with cf6:
                    eml_plazo_po = st.text_input(
                        "⏱️ Plazo PO:",
                        value="1 semana posterior a autorización",
                        help="Compromiso formal para emitir la Orden de Compra tras recibir el visto bueno.",
                        key="eml_plazo_po_batch"
                    )

                # Generar archivo .eml consolidado en memoria
                eml_bytes = build_consolidated_requisitions_eml(
                    selected_records,
                    destinatario_to=eml_to,
                    destinatarios_cc=eml_cc,
                    solicitante_remitente=eml_firma,
                    remitente_from=eml_from,
                    planta=eml_planta,
                    dias_autorizacion=int(eml_dias_aut),
                    plazo_po=eml_plazo_po
                )

                if len(selected_records) == 1:
                    r0 = selected_records[0]
                    s0 = str(r0.get("folio_solicitud", "") or "").strip()
                    rid0 = r0.get("id_requisicion", "REQ")
                    tag_nombre = f"{s0}_{rid0}" if s0 else rid0
                else:
                    tag_nombre = f"{len(selected_records)}_Requisiciones"

                st.download_button(
                    label=f"📩 Descargar Borrador de Correo de Autorización (.eml)",
                    data=eml_bytes,
                    file_name=f"Autorizacion_{tag_nombre}.eml",
                    mime="message/rfc822",
                    type="primary",
                    use_container_width=True,
                    key="btn_descarga_eml_batch"
                )

            # Vista previa opcional
            with st.expander("👁️ Ver Vista Previa del Resumen a Enviar en el Correo"):
                preview_list = []
                for r in selected_records:
                    preview_list.append({
                        "Interno": r.get("folio_solicitud", ""),
                        "Folio": r.get("id_requisicion"),
                        "Fecha": r.get("fecha_requisicion"),
                        "Área": r.get("area_impacto"),
                        "Solicitante": r.get("solicitante"),
                        "Descripción": r.get("descripcion_breve"),
                        "Cotizaciones": r.get("num_cotizaciones"),
                        "Monto Estimado": f"${float(r.get('monto_estimado', 0.0)):,.2f} MXN"
                    })
                st.dataframe(pd.DataFrame(preview_list), use_container_width=True, hide_index=True)

        else:
            st.info("💡 **Selección de Requisiciones para Correo:** Marca las casillas de verificación en el extremo izquierdo de una o varias requisiciones en la tabla superior para generar y descargar el archivo de correo borrador (.eml) de solicitud de autorización para Ing. Lorena Hernandez con todos sus PDFs adjuntos.")

        # Selector para abrir Expediente Permanente
        st.markdown("---")
        st.markdown("##### 🔍 Inspeccionar Expediente Digital y Descargar Documentos")
        c_sel, _ = st.columns([2.5, 1.5])
        with c_sel:
            display_labels = {}
            for _, r in df_filtered.iterrows():
                sol_p = f"[{r.get('folio_solicitud', '')}] " if r.get('folio_solicitud') else ""
                display_labels[r["id_requisicion"]] = f"{sol_p}{r['id_requisicion']} — {r.get('descripcion_breve', '')[:45]}"

            all_options = df_filtered["id_requisicion"].tolist()
            if all_options:
                selected_from_list = st.selectbox(
                    "Selecciona una Requisición para ver su expediente completo:",
                    options=all_options,
                    format_func=lambda x: display_labels.get(x, x),
                    index=0,
                    key="sel_dossier_from_list"
                )
                if selected_from_list:
                    st.session_state["selected_dossier_id"] = selected_from_list

    # =========================================================================
    # VISTA 2: TABLERO KANBAN ESTILO ODOO
    # =========================================================================
    else:
        st.markdown("##### 🗂️ Tablero Kanban por Fases Operativas")
        
        cols_kanban = st.columns(4)
        column_states = [
            (ESTATUS_ESPERA_COTIZACION, "⏳ En Espera de Cotización", cols_kanban[0]),
            (ESTATUS_PENDIENTE_AUTORIZACION, "📋 Pendiente de Autorización", cols_kanban[1]),
            (ESTATUS_PO_GENERADA, "✅ PO Generada", cols_kanban[2]),
            (ESTATUS_ARCHIVADO, "📁 Archivado Histórico", cols_kanban[3])
        ]

        for state_key, state_title, col in column_states:
            cfg = STATUS_CONFIG.get(state_key, {})
            header_color = cfg.get("color", "#0F172A")
            bg_color = cfg.get("bg_color", "#F8FAFC")
            
            items_in_state = df_filtered[df_filtered["estatus"] == state_key]
            
            with col:
                st.markdown(f"""
                <div style="background-color:{bg_color}; border:1px solid {cfg.get('border_color', '#CBD5E1')}; border-top:4px solid {header_color}; border-radius:6px; padding:10px; margin-bottom:12px; text-align:center;">
                    <div style="font-weight:800; font-size:13px; color:{header_color}; text-transform:uppercase;">
                        {state_title} ({len(items_in_state)})
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if items_in_state.empty:
                    st.markdown("""
                    <div style="text-align:center; padding:20px; color:#94A3B8; font-size:12px; font-style:italic;">
                        Sin requisiciones
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    for _, row in items_in_state.iterrows():
                        req_id = row["id_requisicion"]
                        sol_id = row.get("folio_solicitud", "")
                        desc = row["descripcion_breve"]
                        sol = row["solicitante"]
                        area = row["area_impacto"]
                        num_cot = row["num_cotizaciones"]
                        monto = row["monto_po"] if state_key in [ESTATUS_PO_GENERADA, ESTATUS_ARCHIVADO] and row["monto_po"] > 0 else row["monto_estimado"]
                        
                        po_badge = f"""<div style="font-size:11px; color:#047857; font-weight:bold; margin-top:4px;">PO: {row['folio_po']}</div>""" if row.get("folio_po") else ""
                        sol_badge = f"""<span style="font-size:10.5px; font-weight:800; color:#0F172A; background-color:#F1F5F9; border:1px solid #CBD5E1; padding:2px 6px; border-radius:4px; margin-right:6px;">{sol_id}</span>""" if sol_id else ""

                        st.markdown(f"""
                        <div style="background-color:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:12px; margin-bottom:10px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>{sol_badge}<span style="font-weight:900; font-size:13px; color:#EC2024;">{req_id}</span></div>
                                <span style="background-color:#EFF6FF; color:#1E40AF; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700;">{area}</span>
                            </div>
                            <div style="font-size:12px; color:#334155; margin-top:6px; font-weight:600; line-height:1.3;">
                                {desc[:60]}{'...' if len(desc) > 60 else ''}
                            </div>
                            <div style="font-size:11px; color:#64748B; margin-top:6px;">
                                👤 {sol.split('(')[0][:24]}
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px dashed #E2E8F0; font-size:11px;">
                                <span style="font-weight:800; color:#0F172A;">${float(monto):,.2f}</span>
                                <span style="color:#64748B;">📑 {num_cot} cot.</span>
                            </div>
                            {po_badge}
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button(f"Expediente {req_id}", key=f"btn_kan_{req_id}", use_container_width=True):
                            st.session_state["selected_dossier_id"] = req_id

    # =========================================================================
    # EXPEDIENTE DIGITAL PERMANENTE Y DESCARGA EN 1 CLIC
    # =========================================================================
    dossier_id = st.session_state.get("selected_dossier_id")
    if dossier_id:
        req_info = get_requisicion_by_id(dossier_id)
        if req_info:
            st.markdown("---")
            st.markdown(f"""
            <div style="background-color:#FFFFFF; border:1px solid #CBD5E1; border-left:5px solid #EC2024; border-radius:6px; padding:18px; margin-top:10px; box-shadow:0 3px 8px rgba(0,0,0,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:18px; font-weight:900; color:#0F172A;">📁 Expediente Digital Permanente: {dossier_id}</span>
                    <span style="background-color:#E2E8F0; color:#334155; padding:4px 10px; border-radius:4px; font-weight:bold; font-size:12px;">{req_info.get('estatus')}</span>
                </div>
                <div style="font-size:13px; color:#475569; margin-top:8px;">
                    <strong>Área de Impacto:</strong> {req_info.get('area_impacto')} &bull; 
                    <strong>Solicitante:</strong> {req_info.get('solicitante')} &bull; 
                    <strong>Fecha:</strong> {req_info.get('fecha_requisicion')}
                </div>
                <div style="font-size:13px; color:#1E293B; margin-top:4px;">
                    <strong>Descripción:</strong> {req_info.get('descripcion_breve')}
                </div>
                <div style="font-size:12px; color:#64748B; margin-top:4px; font-style:italic;">
                    <strong>Notas de Auditoría:</strong> {req_info.get('notas_auditoria') or 'Sin observaciones registradas.'}
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"✏️ Modificar Descripción y Área de este Expediente ({dossier_id})"):
                cur_exp_area = req_info.get("area_impacto", "")
                area_opts = list(areas_list)
                if cur_exp_area and cur_exp_area not in area_opts:
                    area_opts.append(cur_exp_area)
                idx_exp_area = area_opts.index(cur_exp_area) if cur_exp_area in area_opts else 0

                c_de_a, c_de_d = st.columns([1.1, 2.3])
                with c_de_a:
                    new_exp_area = st.selectbox(
                        "Área de Impacto:",
                        options=area_opts,
                        index=idx_exp_area,
                        key=f"exp_edit_area_{dossier_id}",
                        help="Cambia el área para mejorar la clasificación y seguimiento de la requisición."
                    )
                with c_de_d:
                    new_exp_desc = st.text_area(
                        "Descripción de la Solicitud:",
                        value=str(req_info.get("descripcion_breve", "") or ""),
                        height=75,
                        key=f"exp_edit_desc_{dossier_id}"
                    )
                if st.button("💾 Guardar Cambios (Descripción y Área)", key=f"btn_exp_save_desc_{dossier_id}", type="primary", use_container_width=True):
                    if update_requisicion_detalles(dossier_id, nueva_descripcion=new_exp_desc, nueva_area=new_exp_area):
                        st.toast(f"✅ Requisición {dossier_id} actualizada", icon="✅")
                        st.success("✅ Descripción y Área guardadas exitosamente.")
                        st.rerun()

            # Localizar carpeta física de la requisición
            req_dir = get_req_directory(dossier_id)
            attached_files = list(req_dir.iterdir()) if req_dir.exists() else []

            st.markdown("##### 📎 Documentos y Evidencias Adjuntas en Disco Local:")
            
            if not attached_files:
                st.info("ℹ️ No se han almacenado archivos físicos aún en la carpeta de este expediente.")
            else:
                for file_p in attached_files:
                    if file_p.is_file():
                        f_size_kb = file_p.stat().st_size / 1024
                        f_ext = file_p.suffix.lower()
                        icon_type = "📧" if f_ext == ".eml" else "📄"

                        d_col1, d_col2 = st.columns([3, 1])
                        with d_col1:
                            st.write(f"{icon_type} **{file_p.name}** ({f_size_kb:.1f} KB)")
                        with d_col2:
                            with open(file_p, "rb") as bf:
                                file_bytes = bf.read()
                            
                            mime_type = "message/rfc822" if f_ext == ".eml" else "application/pdf"
                            st.download_button(
                                label=f"⬇️ Descargar",
                                data=file_bytes,
                                file_name=file_p.name,
                                mime=mime_type,
                                key=f"dl_odoo_{dossier_id}_{file_p.name}",
                                use_container_width=True
                            )

            # Desglose de cotizaciones si existen
            df_cots_dossier = load_cotizaciones(dossier_id)
            if not df_cots_dossier.empty:
                st.markdown("##### 📊 Desglose de Cotizaciones Registradas:")
                st.dataframe(
                    df_cots_dossier[["proveedor", "monto", "moneda", "tiempo_entrega_dias", "seleccionada", "archivo_cotizacion_pdf"]],
                    use_container_width=True,
                    hide_index=True
                )
