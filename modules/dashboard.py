"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo 3: Panel de Control (Dashboard), Vista Lista Odoo, Kanban y Expedientes
=============================================================================
"""

import os
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
    load_catalogos
)


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
        st.markdown(f"##### 📋 Listado Oficial de Requisiciones ({len(df_filtered)})")

        if df_filtered.empty:
            st.info("No hay requisiciones que coincidan con los filtros seleccionados.")
            return

        # Función auxiliar para renderizar una tabla de registros estilo Odoo
        def render_odoo_table_section(sub_df: pd.DataFrame, group_title: str = ""):
            if group_title:
                sub_total_monto = sub_df["monto_estimado"].sum()
                st.markdown(f"""
                <div style="background-color:#F1F5F9; border-left:4px solid #0F172A; padding:8px 14px; border-radius:4px; margin:16px 0 8px 0; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:800; font-size:13px; color:#0F172A; text-transform:uppercase;">📂 {group_title} ({len(sub_df)})</span>
                    <span style="font-size:12px; font-weight:700; color:#475569;">Subtotal: ${sub_total_monto:,.2f} MXN</span>
                </div>
                """, unsafe_allow_html=True)

            # Columnas ejecutivas estilo Odoo
            col_specs = [
                ("Folio", "id_requisicion"),
                ("Fecha", "fecha_requisicion"),
                ("Solicitante", "solicitante"),
                ("Área de Impacto", "area_impacto"),
                ("Descripción Breve", "descripcion_breve"),
                ("Cotizaciones", "num_cotizaciones"),
                ("Monto Estimado", "monto_estimado"),
                ("Estatus", "estatus"),
                ("PO", "folio_po")
            ]

            # Formatear datos para presentación impecable
            display_df = sub_df.copy()
            
            # Formatear montos con moneda
            display_df["Monto ($)"] = display_df["monto_estimado"].apply(lambda v: f"${float(v):,.2f}" if float(v) > 0 else "-")
            display_df["Folio"] = display_df["id_requisicion"]
            display_df["Fecha"] = display_df["fecha_requisicion"]
            display_df["Solicitante"] = display_df["solicitante"].apply(lambda s: s.split("(")[0].strip() if "(" in s else s)
            display_df["Área"] = display_df["area_impacto"]
            display_df["Descripción"] = display_df["descripcion_breve"]
            display_df["Cot."] = display_df["num_cotizaciones"].astype(int)
            display_df["Estatus Odoo"] = display_df["estatus"]
            display_df["Folio PO"] = display_df["folio_po"].apply(lambda p: p if p else "-")

            cols_to_show = ["Folio", "Fecha", "Estatus Odoo", "Área", "Solicitante", "Descripción", "Cot.", "Monto ($)", "Folio PO"]
            
            # Renderizar con st.dataframe interactivo y estilizado
            st.dataframe(
                display_df[cols_to_show],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Folio": st.column_config.TextColumn("Folio", width="small"),
                    "Fecha": st.column_config.TextColumn("Fecha", width="small"),
                    "Estatus Odoo": st.column_config.TextColumn("Estatus", width="medium"),
                    "Área": st.column_config.TextColumn("Área de Impacto", width="small"),
                    "Cot.": st.column_config.NumberColumn("Cot.", width="small"),
                    "Monto ($)": st.column_config.TextColumn("Monto Estimado", width="small"),
                    "Folio PO": st.column_config.TextColumn("Orden (PO)", width="small")
                }
            )

        # Si el usuario seleccionó "Agrupar por"
        if group_by == "Estatus":
            for est_name in [ESTATUS_PENDIENTE_AUTORIZACION, ESTATUS_ESPERA_COTIZACION, ESTATUS_PO_GENERADA, ESTATUS_ARCHIVADO]:
                subset = df_filtered[df_filtered["estatus"] == est_name]
                if not subset.empty:
                    with st.expander(f"📁 {est_name} ({len(subset)}) — Subtotal: ${subset['monto_estimado'].sum():,.2f} MXN", expanded=(est_name == ESTATUS_PENDIENTE_AUTORIZACION or est_name == ESTATUS_ESPERA_COTIZACION)):
                        render_odoo_table_section(subset)

        elif group_by == "Área de Impacto":
            for area_name in sorted(df_filtered["area_impacto"].unique()):
                subset = df_filtered[df_filtered["area_impacto"] == area_name]
                if not subset.empty:
                    with st.expander(f"🎯 {area_name} ({len(subset)}) — Subtotal: ${subset['monto_estimado'].sum():,.2f} MXN", expanded=True):
                        render_odoo_table_section(subset)

        elif group_by == "Solicitante":
            for sol_name in sorted(df_filtered["solicitante"].unique()):
                subset = df_filtered[df_filtered["solicitante"] == sol_name]
                if not subset.empty:
                    with st.expander(f"👤 {sol_name} ({len(subset)}) — Subtotal: ${subset['monto_estimado'].sum():,.2f} MXN", expanded=False):
                        render_odoo_table_section(subset)

        else:
            # Lista plana directa
            render_odoo_table_section(df_filtered)

        # Barra de pie de tabla estilo Odoo (Totales)
        st.markdown(f"""
        <div style="background-color:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:10px 16px; margin-top:10px; display:flex; justify-content:space-between; align-items:center; font-size:12.5px;">
            <span><strong>Total de Requisiciones en Lista:</strong> {len(df_filtered)}</span>
            <span><strong>Monto Total Acumulado:</strong> <span style="font-size:14px; font-weight:800; color:#0F172A;">${monto_total_est:,.2f} MXN</span></span>
        </div>
        """, unsafe_allow_html=True)

        # Selector para abrir Expediente Permanente
        st.markdown("---")
        st.markdown("##### 🔍 Inspeccionar Expediente Digital y Descargar Documentos")
        c_sel, _ = st.columns([2.5, 1.5])
        with c_sel:
            all_options = df_filtered["id_requisicion"].tolist()
            if all_options:
                selected_from_list = st.selectbox(
                    "Selecciona una Requisición para ver su expediente completo:",
                    options=all_options,
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
                        desc = row["descripcion_breve"]
                        sol = row["solicitante"]
                        area = row["area_impacto"]
                        num_cot = row["num_cotizaciones"]
                        monto = row["monto_po"] if state_key in [ESTATUS_PO_GENERADA, ESTATUS_ARCHIVADO] and row["monto_po"] > 0 else row["monto_estimado"]
                        
                        po_badge = f"""<div style="font-size:11px; color:#047857; font-weight:bold; margin-top:4px;">PO: {row['folio_po']}</div>""" if row.get("folio_po") else ""

                        st.markdown(f"""
                        <div style="background-color:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:12px; margin-bottom:10px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:900; font-size:13px; color:#0F172A;">{req_id}</span>
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
