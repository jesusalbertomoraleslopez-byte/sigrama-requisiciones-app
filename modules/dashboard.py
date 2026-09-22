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
from typing import List, Dict, Any, Optional

import base64
import streamlit as st
import pandas as pd
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from config import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_BORDER,
    AREAS_IMPACTO_DEFAULT,
    SOLICITANTES_DEFAULT,
    PRIORIDADES_DEFAULT,
    MONEDAS_DEFAULT,
    ESTATUS_ESPERA_COTIZACION,
    ESTATUS_PENDIENTE_AUTORIZACION,
    ESTATUS_AUTORIZADA,
    ESTATUS_PO_GENERADA,
    ESTATUS_TERMINADA,
    ESTATUS_ARCHIVADA,
    ESTATUS_ARCHIVADO,
    ESTATUS_CONGELADA,
    STATUS_CONFIG,
    TODOS_ESTATUS,
    PALETA_COLORES_ODOO,
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
    save_requisicion,
    update_requisicion_descripcion,
    update_requisicion_detalles
)
from email_generator import (
    build_consolidated_requisitions_eml,
)


@st.dialog("📋 Expediente y Ajuste de Requisición", width="large")
def modal_ver_expediente(dossier_id: str):
    """Ventana modal interactiva de alta fidelidad: vista preliminar del PDF original y ajuste de datos."""
    req_info = get_requisicion_by_id(dossier_id)
    if not req_info:
        st.error(f"No se encontró información para la requisición {dossier_id}.")
        return

    # Catálogos dinámicos
    catalogos = load_catalogos()
    areas_list = list(catalogos.get("areas_impacto", AREAS_IMPACTO_DEFAULT))
    solicitantes_list = list(catalogos.get("solicitantes", SOLICITANTES_DEFAULT))
    prioridades_list = list(PRIORIDADES_DEFAULT)
    monedas_list = list(MONEDAS_DEFAULT)

    sol_id = str(req_info.get("folio_solicitud", "") or "").strip()
    estatus_actual = str(req_info.get("estatus", "") or "").strip()

    # Normalizar estatus
    matched_status = TODOS_ESTATUS[0]
    for s in TODOS_ESTATUS:
        if s.lower() == estatus_actual.lower():
            matched_status = s
            break
        if "espera" in estatus_actual.lower() and "espera" in s.lower():
            matched_status = ESTATUS_ESPERA_COTIZACION
            break
        if "pendiente" in estatus_actual.lower() and "pendiente" in s.lower():
            matched_status = ESTATUS_PENDIENTE_AUTORIZACION
            break
        if "congelad" in estatus_actual.lower() and "congelad" in s.lower():
            matched_status = ESTATUS_CONGELADA
            break
        if "archiv" in estatus_actual.lower() and "archiv" in s.lower():
            matched_status = ESTATUS_ARCHIVADA
            break
        if "po" in estatus_actual.lower() and "po" in s.lower():
            matched_status = ESTATUS_PO_GENERADA
            break
        if "terminad" in estatus_actual.lower() and "terminad" in s.lower():
            matched_status = ESTATUS_TERMINADA
            break
        if "autorizad" in estatus_actual.lower() and s == ESTATUS_AUTORIZADA:
            matched_status = ESTATUS_AUTORIZADA
            break

    cfg = STATUS_CONFIG.get(matched_status, {})
    status_color = cfg.get("color", "#0F172A")
    status_bg = cfg.get("bg_color", "#F1F5F9")
    status_icon = cfg.get("icon", "📋")

    # Localizar archivo PDF de la requisición en la carpeta local
    req_dir = get_req_directory(dossier_id)
    pdf_file = None
    pdf_name = req_info.get("archivo_requisicion_pdf", "")
    if pdf_name and (req_dir / pdf_name).exists():
        pdf_file = req_dir / pdf_name
    elif req_dir.exists():
        for f in req_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".pdf" and ("requisic" in f.name.lower() or "req" in f.name.lower()):
                pdf_file = f
                break
        if not pdf_file:
            for f in req_dir.iterdir():
                if f.is_file() and f.suffix.lower() == ".pdf" and "cotiz" not in f.name.lower():
                    pdf_file = f
                    break

    # Encabezado visual compacto con identificador y semáforo
    st.markdown(f"""
    <div style="background-color:#FFFFFF; border:1px solid #CBD5E1; border-left:6px solid #EC2024; border-radius:8px; padding:10px 16px; margin-bottom:12px; box-shadow:0 2px 6px rgba(0,0,0,0.04);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
                <span style="font-size:12px; font-weight:800; color:#475569; background:#F1F5F9; border:1px solid #CBD5E1; padding:3px 8px; border-radius:4px; margin-right:8px;">{sol_id or 'SOL-S/N'}</span>
                <span style="font-size:24px; font-weight:900; color:#EC2024; font-family:'Montserrat', sans-serif;">{dossier_id}</span>
            </div>
            <span style="background-color:{status_bg}; color:{status_color}; border:1px solid {status_color}44; padding:4px 12px; border-radius:6px; font-weight:800; font-size:13px;">
                {status_icon} {matched_status}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # DISPOSICIÓN A 2 COLUMNAS: Izquierda = Documento Preliminar (PDF), Derecha = Ajuste de Campos y Guardar
    col_pdf, col_form = st.columns([1.1, 1.25])

    # -------------------------------------------------------------------------
    # COLUMNA 1: VISTA PRELIMINAR DEL DOCUMENTO (PDF)
    # -------------------------------------------------------------------------
    with col_pdf:
        st.markdown("##### 📄 Documento Preliminar (PDF Original)")
        if pdf_file and pdf_file.exists():
            with open(pdf_file, "rb") as f_pdf:
                pdf_bytes = f_pdf.read()

            st.download_button(
                label="⬇️ Descargar PDF Original",
                data=pdf_bytes,
                file_name=pdf_file.name,
                mime="application/pdf",
                key=f"dl_pdf_preview_{dossier_id}",
                use_container_width=True
            )

            with st.container(height=680):
                if fitz:
                    try:
                        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                        for page_num in range(len(doc)):
                            if len(doc) > 1:
                                st.caption(f"📄 Página {page_num + 1} de {len(doc)}")
                            page = doc[page_num]
                            pix = page.get_pixmap(dpi=140)
                            img_bytes = pix.tobytes("png")
                            st.image(img_bytes, use_container_width=True)
                    except Exception:
                        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
                        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="640" style="border:1px solid #CBD5E1; border-radius:6px;"></iframe>', unsafe_allow_html=True)
                else:
                    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
                    st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="640" style="border:1px solid #CBD5E1; border-radius:6px;"></iframe>', unsafe_allow_html=True)
        else:
            st.info("ℹ️ No se ha encontrado el archivo PDF original de esta requisición.")
            uploaded_pdf = st.file_uploader("Adjuntar PDF de Requisición:", type=["pdf"], key=f"upload_pdf_{dossier_id}")
            if uploaded_pdf:
                target_pdf_path = req_dir / f"requisicion_{dossier_id}.pdf"
                with open(target_pdf_path, "wb") as f_out:
                    f_out.write(uploaded_pdf.getbuffer())
                update_requisicion_detalles(dossier_id, nueva_descripcion=None)
                st.toast("✅ PDF adjuntado correctamente", icon="📄")
                st.rerun()

    # -------------------------------------------------------------------------
    # COLUMNA 2: FORMULARIO Y AJUSTE DE INFORMACIÓN
    # -------------------------------------------------------------------------
    with col_form:
        st.markdown("##### ✏️ Ajuste de Información")
        with st.form(key=f"form_expediente_{dossier_id}"):
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                inp_sol_id = st.text_input("No. Interno (SOL):", value=sol_id, help="Consecutivo interno SOL-XXXXX")
            with c_f2:
                inp_req_id = st.text_input("No. Requisición SAI:", value=dossier_id, help="Folio oficial del SAI")

            c_f3, c_f4 = st.columns([1.6, 1])
            with c_f3:
                st_idx = TODOS_ESTATUS.index(matched_status) if matched_status in TODOS_ESTATUS else 0
                inp_estatus = st.selectbox(
                    "Estatus / Etapa Actual:",
                    options=TODOS_ESTATUS,
                    index=st_idx,
                    format_func=lambda s: f"{STATUS_CONFIG.get(s, {}).get('icon', '')} {s}"
                )
            with c_f4:
                cur_prio = req_info.get("prioridad", "Media")
                if cur_prio not in prioridades_list:
                    prioridades_list.append(cur_prio)
                prio_idx = prioridades_list.index(cur_prio) if cur_prio in prioridades_list else 1
                inp_prioridad = st.selectbox("Prioridad:", options=prioridades_list, index=prio_idx)

            cur_solicitante = str(req_info.get("solicitante", "") or "").strip()
            if cur_solicitante and cur_solicitante not in solicitantes_list:
                solicitantes_list.insert(0, cur_solicitante)
            sol_idx = solicitantes_list.index(cur_solicitante) if cur_solicitante in solicitantes_list else 0
            inp_solicitante = st.selectbox("Solicitante:", options=solicitantes_list, index=sol_idx)

            c_f6, c_f7 = st.columns([1.4, 1.1])
            with c_f6:
                cur_area = str(req_info.get("area_impacto", "") or "").strip()
                if cur_area and cur_area not in areas_list:
                    areas_list.insert(0, cur_area)
                area_idx = areas_list.index(cur_area) if cur_area in areas_list else 0
                inp_area = st.selectbox("Área de Impacto:", options=areas_list, index=area_idx)
            with c_f7:
                inp_fecha = st.text_input("Fecha Solicitud:", value=str(req_info.get("fecha_requisicion", "") or ""))

            c_f8, c_f9, c_f10 = st.columns([1.2, 1, 1.2])
            with c_f8:
                m_est_val = float(req_info.get("monto_estimado", 0.0) or 0.0)
                inp_monto_est = st.number_input("Monto Estimado ($):", value=m_est_val, min_value=0.0, step=100.0, format="%.2f")
            with c_f9:
                cur_mon = str(req_info.get("moneda", "MXN") or "MXN").strip()
                if cur_mon not in monedas_list:
                    monedas_list.append(cur_mon)
                mon_idx = monedas_list.index(cur_mon) if cur_mon in monedas_list else 0
                inp_moneda = st.selectbox("Moneda:", options=monedas_list, index=mon_idx)
            with c_f10:
                m_po_val = float(req_info.get("monto_po", 0.0) or 0.0)
                inp_monto_po = st.number_input("Monto PO ($):", value=m_po_val, min_value=0.0, step=100.0, format="%.2f")

            inp_desc = st.text_area(
                "Descripción Breve / Concepto:",
                value=str(req_info.get("descripcion_breve", "") or ""),
                height=80,
                help="Concepto o descripción detallada de lo que se requiere comprar o fabricar."
            )
            inp_just = st.text_area(
                "Justificación / Motivo:",
                value=str(req_info.get("justificacion", "") or ""),
                height=55
            )

            c_po1, c_po2 = st.columns([1.1, 1.5])
            with c_po1:
                inp_folio_po = st.text_input("Folio de PO:", value=str(req_info.get("folio_po", "") or ""))
            with c_po2:
                cur_prov = str(req_info.get("proveedor_seleccionado", "") or req_info.get("proveedor_po", "") or "")
                inp_proveedor = st.text_input("Proveedor Ganador / Asignado:", value=cur_prov)

            c_po3, c_po4 = st.columns(2)
            with c_po3:
                inp_fecha_po = st.text_input("Fecha de PO:", value=str(req_info.get("fecha_po", "") or ""))
            with c_po4:
                inp_notas = st.text_input("Notas de Auditoría:", value=str(req_info.get("notas_auditoria", "") or ""))

            paleta_ids = [c["id"] for c in PALETA_COLORES_ODOO]
            cur_color_id = str(req_info.get("color_etiqueta", "amarillo") or "amarillo").strip().lower()
            if cur_color_id in ["", "nan", "none"]:
                cur_color_id = "amarillo"
            col_idx = paleta_ids.index(cur_color_id) if cur_color_id in paleta_ids else 0
            inp_color_etiqueta = st.selectbox(
                "🎨 Color de Fondo del Post-it (Tablero Kanban):",
                options=paleta_ids,
                index=col_idx,
                format_func=lambda cid: next((c["nombre"] for c in PALETA_COLORES_ODOO if c["id"] == cid), cid),
                help="Elige el color de fondo con el que se mostrará esta tarjeta Post-it en el tablero Kanban."
            )

            st.write("")
            btn_submit = st.form_submit_button(
                "💾 GUARDAR INFORMACIÓN DE LA REQUISICIÓN",
                type="primary",
                use_container_width=True
            )

            if btn_submit:
                clean_req = normalize_req_id(inp_req_id)
                clean_sol = inp_sol_id.strip().upper()
                
                updated_data = {
                    "id_requisicion": clean_req,
                    "folio_solicitud": clean_sol,
                    "fecha_requisicion": inp_fecha.strip(),
                    "solicitante": inp_solicitante.strip(),
                    "area_impacto": inp_area.strip(),
                    "descripcion_breve": inp_desc.strip(),
                    "justificacion": inp_just.strip(),
                    "prioridad": inp_prioridad,
                    "estatus": inp_estatus,
                    "color_etiqueta": inp_color_etiqueta,
                    "proveedor_seleccionado": inp_proveedor.strip(),
                    "proveedor_po": inp_proveedor.strip(),
                    "monto_estimado": float(inp_monto_est),
                    "moneda": inp_moneda,
                    "num_cotizaciones": req_info.get("num_cotizaciones", 0),
                    "folio_po": inp_folio_po.strip(),
                    "fecha_po": inp_fecha_po.strip(),
                    "monto_po": float(inp_monto_po),
                    "fecha_autorizacion": req_info.get("fecha_autorizacion", ""),
                    "autorizado_por": req_info.get("autorizado_por", ""),
                    "archivo_requisicion_pdf": req_info.get("archivo_requisicion_pdf", ""),
                    "archivo_eml": req_info.get("archivo_eml", ""),
                    "archivo_po": req_info.get("archivo_po", ""),
                    "notas_auditoria": inp_notas.strip(),
                    "fecha_registro": req_info.get("fecha_registro", "")
                }

                if save_requisicion(updated_data):
                    st.toast(f"✅ Requisición {clean_req} guardada exitosamente", icon="💾")
                    st.success(f"✅ ¡Información de {clean_req} actualizada y sincronizada!")
                    st.rerun()
                else:
                    st.error("❌ Ocurrió un error al guardar los cambios en la base de datos.")

    # =========================================================================
    # COTIZACIONES ASOCIADAS
    # =========================================================================
    df_cots = load_cotizaciones(dossier_id)
    if not df_cots.empty:
        st.markdown("---")
        st.markdown(f"##### 📑 Cotizaciones Asociadas ({len(df_cots)})")
        cols_cot_show = ["proveedor", "monto", "moneda", "tiempo_entrega_dias", "seleccionada", "archivo_cotizacion_pdf"]
        cols_present = [c for c in cols_cot_show if c in df_cots.columns]
        st.dataframe(df_cots[cols_present], use_container_width=True, hide_index=True)

    # =========================================================================
    # ARCHIVOS FÍSICOS Y EVIDENCIAS
    # =========================================================================
    req_dir = get_req_directory(dossier_id)
    attached_files = list(req_dir.iterdir()) if req_dir.exists() else []

    st.markdown("---")
    st.markdown("##### 📎 Documentos y Evidencias Adjuntas")
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
                    try:
                        with open(file_p, "rb") as bf:
                            file_bytes = bf.read()
                        mime_type = "message/rfc822" if f_ext == ".eml" else "application/pdf"
                        st.download_button(
                            label="⬇️ Descargar",
                            data=file_bytes,
                            file_name=file_p.name,
                            mime=mime_type,
                            key=f"dl_modal_{dossier_id}_{file_p.name}",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error: {e}")

    # Descarga directa de correo individual EML
    try:
        single_eml = build_consolidated_requisitions_eml(
            [req_info],
            destinatario_to=None,
            destinatarios_cc=None,
            solicitante_remitente=req_info.get("solicitante", ""),
            remitente_from=None,
            planta="Planta Metales"
        )
        s_sol = str(req_info.get("folio_solicitud", "") or "").strip()
        s_tag = f"{s_sol}_{dossier_id}" if s_sol else dossier_id
        st.download_button(
            label=f"📩 Descargar Correo de Autorización (.eml)",
            data=single_eml,
            file_name=f"Autorizacion_{s_tag}.eml",
            mime="message/rfc822",
            key=f"dl_eml_modal_{dossier_id}",
            use_container_width=True
        )
    except Exception:
        pass

    st.markdown("---")
    if st.button("✖️ Cerrar Ventana", key=f"btn_close_modal_{dossier_id}", use_container_width=True):
        st.rerun()


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


def render_dashboard(force_view: Optional[str] = None):
    """Renderiza el panel de control ejecutivo con Vista Lista tipo Odoo y Tablero Kanban."""
    if force_view:
        st.session_state["odoo_view_mode"] = force_view
    elif "odoo_view_mode" not in st.session_state:
        st.session_state["odoo_view_mode"] = "📋 Lista Odoo"

    title_text = "🗂️ Pipeline Kanban por Fases (Estilo Odoo CRM)" if st.session_state.get("odoo_view_mode") == "🗂️ Kanban Odoo" else "📊 Control Operativo de Requisiciones (Estilo Odoo ERP)"
    desc_text = "Vista de pipeline por columnas donde puedes arrastrar/cambiar de estatus cada requisición en 1 clic." if st.session_state.get("odoo_view_mode") == "🗂️ Kanban Odoo" else "Gestión centralizada por fases, agrupación multidimensional y expediente digital permanente."

    st.markdown(f"""
    <div style="background-color:#FFFFFF; border-left:5px solid #EC2024; padding:16px 20px; border-radius:6px; margin-bottom:18px; box-shadow:0 2px 6px rgba(0,0,0,0.04); border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0; border-bottom:1px solid #E2E8F0;">
        <div style="font-size:18px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.5px;">
            {title_text}
        </div>
        <div style="font-size:13px; color:#64748B; margin-top:4px;">
            Industria SIGRAMA S.A. de C.V. &bull; {desc_text}
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
            cur_view = st.session_state.get("odoo_view_mode", "📋 Lista Odoo")
            opts = ["📋 Lista Odoo", "🗂️ Kanban Odoo"]
            view_mode = st.radio(
                "Modo de Vista:",
                options=opts,
                index=opts.index(cur_view) if cur_view in opts else 0,
                horizontal=True,
                key="odoo_view_mode"
            )

    # Filtros Rápidos por Estado (Odoo Filter Chips con los 7 estatus)
    f_cols = st.columns(8)
    counts = {
        "all": len(df_reqs),
        "esp": len(df_reqs[df_reqs["estatus"] == ESTATUS_ESPERA_COTIZACION]),
        "pen": len(df_reqs[df_reqs["estatus"] == ESTATUS_PENDIENTE_AUTORIZACION]),
        "aut": len(df_reqs[df_reqs["estatus"] == ESTATUS_AUTORIZADA]),
        "po": len(df_reqs[df_reqs["estatus"] == ESTATUS_PO_GENERADA]),
        "ter": len(df_reqs[df_reqs["estatus"] == ESTATUS_TERMINADA]),
        "arc": len(df_reqs[df_reqs["estatus"].isin([ESTATUS_ARCHIVADA, "Archivado Histórico"])]),
        "con": len(df_reqs[df_reqs["estatus"] == ESTATUS_CONGELADA]),
    }

    if "odoo_status_filter" not in st.session_state:
        st.session_state["odoo_status_filter"] = "Todos"

    with f_cols[0]:
        if st.button(f"🌐 Todos ({counts['all']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = "Todos"
    with f_cols[1]:
        if st.button(f"⏳ Cotización ({counts['esp']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_ESPERA_COTIZACION
    with f_cols[2]:
        if st.button(f"📋 Pendiente ({counts['pen']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_PENDIENTE_AUTORIZACION
    with f_cols[3]:
        if st.button(f"👍 Autorizada ({counts['aut']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_AUTORIZADA
    with f_cols[4]:
        if st.button(f"📝 Con PO ({counts['po']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_PO_GENERADA
    with f_cols[5]:
        if st.button(f"✅ Terminada ({counts['ter']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_TERMINADA
    with f_cols[6]:
        if st.button(f"📁 Archivada ({counts['arc']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_ARCHIVADA
    with f_cols[7]:
        if st.button(f"🧊 Congelada ({counts['con']})", use_container_width=True):
            st.session_state["odoo_status_filter"] = ESTATUS_CONGELADA

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
    monto_total_po = df_filtered[df_filtered["estatus"].isin([ESTATUS_PO_GENERADA, ESTATUS_TERMINADA, ESTATUS_ARCHIVADA, "Archivado Histórico"])]["monto_po"].sum()

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
            <span>✏️ <strong>Edición Directa en la Tabla:</strong> Puedes cambiar el <strong>🚦 Estatus</strong> haciendo clic en su celda, editar la <strong>Descripción</strong> con doble clic, o reasignar el <strong>Área de Impacto</strong>. Para mover tarjetas entre etapas estilo CRM, activa la vista <strong>🗂️ Kanban Odoo</strong> arriba a la derecha.</span>
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
            display_df["Interno"] = display_df.get("folio_solicitud", "").apply(
                lambda v: str(v).upper() if v else ""
            )
            display_df["Monto ($)"] = display_df["monto_estimado"].apply(lambda v: f"${float(v):,.2f}" if float(v) > 0 else "-")
            display_df["Folio"] = display_df["id_requisicion"]
            display_df["Fecha"] = display_df["fecha_requisicion"]
            display_df["Solicitante"] = display_df["solicitante"].apply(lambda s: s.split("(")[0].strip() if "(" in s else s)
            display_df["Área"] = display_df["area_impacto"]
            display_df["Descripción"] = display_df["descripcion_breve"]
            display_df["Cot."] = display_df["num_cotizaciones"].astype(int)
            display_df["Folio PO"] = display_df["folio_po"].apply(lambda p: p if p else "-")

            # Columna Estatus con emoji de badge de color según STATUS_CONFIG
            def fmt_estatus(e):
                cfg = STATUS_CONFIG.get(str(e).strip(), {})
                icon = cfg.get("icon", "❓")
                return f"{icon} {e}"
            display_df["Estatus Odoo"] = display_df["estatus"].apply(fmt_estatus)

            display_df.insert(0, "Sel.", False)

            cols_to_show = ["Sel.", "Interno", "Folio", "Fecha", "Estatus Odoo", "Área", "Solicitante", "Descripción", "Cot.", "Monto ($)", "Folio PO"]

            # Aplicar estilo de color a las últimas cargadas (exactamente como en Remisiones #FFF59D)
            # Y aplicar color de fila según estatus
            def style_table(row):
                estatus_raw = str(row.get("Estatus Odoo", "")).strip()
                # Buscar la clave original en STATUS_CONFIG
                cfg = {}
                for k, v in STATUS_CONFIG.items():
                    if k in estatus_raw:
                        cfg = v
                        break
                bg = ""
                if row["Folio"] in ultimas_cargadas_set and "Amarillo" in highlight_mode:
                    bg = "background-color: #FFF59D; color: #0F172A;"
                elif cfg:
                    bg = f"background-color: {cfg['bg_color']}22; color: #0F172A;"
                return [bg for _ in row]

            if "Amarillo" in highlight_mode:
                data_to_render = display_df[cols_to_show].style.apply(
                    lambda row: ['background-color: #FFF59D; color: #0F172A;' if row["Folio"] in ultimas_cargadas_set else '' for _ in row],
                    axis=1
                )
            else:
                data_to_render = display_df[cols_to_show]

            # Opciones oficiales de estatus con semáforo/emoji (1 a 7 ordenados)
            estatus_opciones = [
                f"{STATUS_CONFIG[ESTATUS_ESPERA_COTIZACION]['icon']} {ESTATUS_ESPERA_COTIZACION}",
                f"{STATUS_CONFIG[ESTATUS_PENDIENTE_AUTORIZACION]['icon']} {ESTATUS_PENDIENTE_AUTORIZACION}",
                f"{STATUS_CONFIG[ESTATUS_AUTORIZADA]['icon']} {ESTATUS_AUTORIZADA}",
                f"{STATUS_CONFIG[ESTATUS_PO_GENERADA]['icon']} {ESTATUS_PO_GENERADA}",
                f"{STATUS_CONFIG[ESTATUS_TERMINADA]['icon']} {ESTATUS_TERMINADA}",
                f"{STATUS_CONFIG[ESTATUS_ARCHIVADA]['icon']} {ESTATUS_ARCHIVADA}",
                f"{STATUS_CONFIG[ESTATUS_CONGELADA]['icon']} {ESTATUS_CONGELADA}",
            ]

            # Renderizar con st.data_editor: permite editar 'Estatus', 'Descripción' y 'Área' directamente
            edited_table = st.data_editor(
                data_to_render,
                use_container_width=True,
                hide_index=True,
                key=table_key,
                column_config={
                    "Sel.": st.column_config.CheckboxColumn("✉️", help="Marca la casilla para incluir en el paquete de correo .eml", default=False, width="small"),
                    "Interno": st.column_config.TextColumn(
                        "📌 Interno (SOL)",
                        width="medium",
                        help="Consecutivo Interno Planta Metales (SOL-XXXXX)",
                        disabled=True
                    ),
                    "Folio": st.column_config.TextColumn("Folio (REQ)", width="small", help="Folio Oficial de Requisición", disabled=True),
                    "Fecha": st.column_config.TextColumn("Fecha", width="small", disabled=True),
                    "Estatus Odoo": st.column_config.SelectboxColumn(
                        "🚦 Estatus",
                        width="medium",
                        options=estatus_opciones,
                        required=True,
                        help="Haz clic para cambiar el estatus de la requisición (1 al 7)"
                    ),
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
                    orig_e = str(display_df.iloc[i]["Estatus Odoo"] or "").strip()
                    new_e = str(edited_table.iloc[i]["Estatus Odoo"] or "").strip()

                    # Limpiar emoji para guardar estatus oficial
                    clean_new_e = None
                    if orig_e != new_e:
                        for est_oficial in TODOS_ESTATUS:
                            if est_oficial in new_e:
                                clean_new_e = est_oficial
                                break

                    if orig_d != new_d or orig_a != new_a or clean_new_e is not None:
                        f_id = display_df.iloc[i]["Folio"]
                        s_id = display_df.iloc[i]["Interno"]
                        update_requisicion_detalles(
                            f_id,
                            nueva_descripcion=new_d if orig_d != new_d else None,
                            nueva_area=new_a if orig_a != new_a else None,
                            nuevo_estatus=clean_new_e
                        )
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
            for idx_grp, est_name in enumerate(TODOS_ESTATUS):
                subset = df_filtered[df_filtered["estatus"] == est_name]
                if not subset.empty:
                    cfg_s = STATUS_CONFIG.get(est_name, {})
                    icon_s = cfg_s.get("icon", "📁")
                    with st.expander(f"{icon_s} {est_name} ({len(subset)}) — Subtotal: ${subset['monto_estimado'].sum():,.2f} MXN", expanded=(est_name in [ESTATUS_ESPERA_COTIZACION, ESTATUS_PENDIENTE_AUTORIZACION, ESTATUS_AUTORIZADA])):
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

                # ── Información de envío (solo lectura / pre-configurado) ──────────
                st.markdown("""
                <div style="background-color:#F0FDF4; border:1px solid #86EFAC; border-radius:6px; padding:10px 14px; font-size:12px; color:#166534; margin-bottom:8px;">
                    <strong>📧 Configuración del Correo de Autorización:</strong><br>
                    <span>✉️ <strong>Para:</strong> Ing. Lorena Hernandez &lt;lhernandez@sigrama.com.mx&gt;</span><br>
                    <span>🔕 <strong>De:</strong> <em>Cuenta predeterminada del equipo que abre el .eml</em> (asignada automáticamente por Outlook)</span>
                </div>
                """, unsafe_allow_html=True)

                cf3, cf4, cf5, cf6 = st.columns([1.2, 1.0, 0.8, 1.2])
                with cf3:
                    eml_firma = st.text_input(
                        "✍️ Firma Solicitante:",
                        value=usuario_actual_firma,
                        key="eml_firma_batch",
                        help="Nombre que aparece al calce del cuerpo del correo."
                    )
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
                # To: siempre Lorena (del config). Cc: defaults del config. From: omitido (Outlook usa cuenta del equipo).
                eml_bytes = build_consolidated_requisitions_eml(
                    selected_records,
                    destinatario_to=None,   # usa DESTINATARIO_PRINCIPAL_DEFAULT (Ing. Lorena Hernandez)
                    destinatarios_cc=None,  # usa DESTINATARIOS_CC_DEFAULT del config
                    solicitante_remitente=eml_firma,
                    remitente_from=None,    # Outlook asigna la cuenta predeterminada del equipo
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
        c_sel, c_btn = st.columns([2.5, 1.2])
        selected_from_list = None
        with c_sel:
            display_labels = {}
            for _, r in df_filtered.iterrows():
                sol_p = f"[{r.get('folio_solicitud', '')}] " if r.get('folio_solicitud') else ""
                display_labels[r["id_requisicion"]] = f"{sol_p}{r['id_requisicion']} — {r.get('descripcion_breve', '')[:45]}"

            all_options = df_filtered["id_requisicion"].tolist()
            if all_options:
                selected_from_list = st.selectbox(
                    "Selecciona una Requisición para ver su expediente:",
                    options=all_options,
                    format_func=lambda x: display_labels.get(x, x),
                    index=0,
                    key="sel_dossier_from_list"
                )
                if selected_from_list:
                    st.session_state["selected_dossier_id"] = selected_from_list

        with c_btn:
            st.write("")
            st.write("")
            if st.button("📁 Abrir Ventana", key="btn_open_modal_from_list", type="primary", use_container_width=True):
                if selected_from_list:
                    modal_ver_expediente(selected_from_list)

    # =========================================================================
    # VISTA 2: TABLERO KANBAN ESTILO ODOO
    # =========================================================================
    else:
        st.markdown("##### 🗂️ Tablero Kanban por Fases Operativas (Pipeline Odoo CRM)")
        st.markdown("""
        <div style="background-color:#F8FAFC; border-left:4px solid #EC2024; padding:8px 14px; border-radius:4px; margin-bottom:12px; font-size:12.5px; color:#334155;">
            💡 <b>Pipeline Interactivo:</b> Cambia de estatus en 1 clic con <b>[◀ Regresar]</b> o <b>[▶ Avanzar]</b>, abre el expediente con <b>[👁️]</b>, o reasigna directamente con <b>[⚙️ Mover]</b>.
        </div>
        """, unsafe_allow_html=True)
        
        cols_kanban = st.columns(7)
        column_states = [
            (ESTATUS_ESPERA_COTIZACION, "1. ⏳ Cotización", cols_kanban[0]),
            (ESTATUS_PENDIENTE_AUTORIZACION, "2. 📋 Pendiente", cols_kanban[1]),
            (ESTATUS_AUTORIZADA, "3. 👍 Autorizada", cols_kanban[2]),
            (ESTATUS_PO_GENERADA, "4. 📝 Con PO", cols_kanban[3]),
            (ESTATUS_TERMINADA, "5. ✅ Terminada", cols_kanban[4]),
            (ESTATUS_ARCHIVADA, "6. 📁 Archivada", cols_kanban[5]),
            (ESTATUS_CONGELADA, "7. 🧊 Congelada", cols_kanban[6]),
        ]

        # En modo Kanban CRM se muestran todas las columnas de fases (respetando búsqueda y filtro de área)
        df_kanban = df_reqs.copy()
        if area_filter != "Todas las Áreas":
            df_kanban = df_kanban[df_kanban["area_impacto"] == area_filter]
        if search_text:
            mask_k = (
                df_kanban["id_requisicion"].str.lower().str.contains(search_text) |
                df_kanban.get("folio_solicitud", pd.Series("", index=df_kanban.index)).str.lower().str.contains(search_text) |
                df_kanban["solicitante"].str.lower().str.contains(search_text) |
                df_kanban["descripcion_breve"].str.lower().str.contains(search_text) |
                df_kanban["folio_po"].str.lower().str.contains(search_text) |
                df_kanban["proveedor_seleccionado"].str.lower().str.contains(search_text)
            )
            df_kanban = df_kanban[mask_k]

        total_pipeline_monto = max(df_kanban["monto_estimado"].sum(), 1.0)

        for state_key, state_title, col in column_states:
            cfg = STATUS_CONFIG.get(state_key, {})
            header_color = cfg.get("color", "#0F172A")
            bg_color = cfg.get("bg_color", "#F8FAFC")
            
            # Asegurar coincidencia incluso si viene con nombre antiguo 'Archivado Histórico'
            if state_key == ESTATUS_ARCHIVADA:
                items_in_state = df_kanban[df_kanban["estatus"].isin([ESTATUS_ARCHIVADA, "Archivado Histórico"])]
            else:
                items_in_state = df_kanban[df_kanban["estatus"] == state_key]

            # Calcular monto total de la columna
            col_total_monto = 0.0
            if not items_in_state.empty:
                for _, r in items_in_state.iterrows():
                    m_po = float(r.get("monto_po", 0.0) or 0.0)
                    m_est = float(r.get("monto_estimado", 0.0) or 0.0)
                    if state_key in [ESTATUS_PO_GENERADA, ESTATUS_TERMINADA, ESTATUS_ARCHIVADA] and m_po > 0:
                        col_total_monto += m_po
                    else:
                        col_total_monto += m_est

            bar_pct = min(max(int((col_total_monto / total_pipeline_monto) * 100), 10) if col_total_monto > 0 else 0, 100)
            
            with col:
                # Encabezado estilo Odoo CRM con Título, Contador, Barra de Progreso y Monto Total
                header_html = (
                    f'<div style="background-color:#FFFFFF; border:1px solid #E2E8F0; border-top:4px solid {header_color}; border-radius:6px; padding:8px 10px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<span style="font-weight:800; font-size:11.5px; color:#0F172A; text-transform:uppercase; letter-spacing:0.3px;">{state_title}</span>'
                    f'<span style="background-color:#F1F5F9; color:#475569; font-size:11px; font-weight:800; padding:1px 6px; border-radius:10px; border:1px solid #E2E8F0;">{len(items_in_state)}</span>'
                    f'</div>'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">'
                    f'<div style="flex:1; height:4px; background-color:#E2E8F0; border-radius:2px; margin-right:8px; overflow:hidden;">'
                    f'<div style="width:{bar_pct}%; height:100%; background-color:{header_color}; border-radius:2px;"></div>'
                    f'</div>'
                    f'<span style="font-size:11.5px; font-weight:800; color:#0F172A; white-space:nowrap;">${col_total_monto:,.0f}</span>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(header_html, unsafe_allow_html=True)

                if items_in_state.empty:
                    st.markdown('<div style="text-align:center; padding:18px 4px; color:#94A3B8; font-size:11px; font-style:italic;">Sin requisiciones</div>', unsafe_allow_html=True)
                else:
                    for _, row in items_in_state.iterrows():
                        req_id = row["id_requisicion"]
                        sol_id = str(row.get("folio_solicitud", "") or "").strip()
                        desc = str(row.get("descripcion_breve", "") or "").strip()
                        sol = str(row.get("solicitante", "") or "").strip()
                        area = str(row.get("area_impacto", "") or "").strip()
                        num_cot = int(row.get("num_cotizaciones", 0) or 0)
                        monto = float(row["monto_po"]) if state_key in [ESTATUS_PO_GENERADA, ESTATUS_TERMINADA, ESTATUS_ARCHIVADA] and float(row.get("monto_po", 0) or 0) > 0 else float(row.get("monto_estimado", 0) or 0)
                        moneda = str(row.get("moneda", "MXN") or "MXN")
                        prioridad = str(row.get("prioridad", "Media") or "Media").strip().capitalize()

                        if prioridad in ["Urgente", "Alta"]:
                            stars = "⭐⭐⭐"
                        elif prioridad == "Media":
                            stars = "⭐⭐☆"
                        else:
                            stars = "⭐☆☆"

                        # Iniciales y color para el avatar circular Odoo
                        sol_clean = re.sub(r'\(.*?\)', '', sol).strip()
                        name_parts = [p for p in sol_clean.split() if p and p.lower() not in ['ing.', 'lic.', 'arq.', 'dr.', 'de', 'del', 'la', 'las', 'los']]
                        if len(name_parts) >= 2:
                            initials = (name_parts[0][0] + name_parts[1][0]).upper()
                        elif len(name_parts) == 1:
                            initials = name_parts[0][:2].upper()
                        else:
                            initials = "SG"

                        avatar_colors = ["#6366F1", "#8B5CF6", "#0D9488", "#D97706", "#DB2777", "#2563EB", "#059669"]
                        avatar_bg = avatar_colors[abs(hash(sol_clean)) % len(avatar_colors)]

                        # Color asignado al Post-it / tarjeta Odoo
                        color_val = str(row.get("color_etiqueta", "amarillo") or "amarillo").strip().lower()
                        if color_val in ["", "nan", "none"]:
                            color_val = "amarillo"

                        palette_match = next((c for c in PALETA_COLORES_ODOO if c["id"] == color_val or c["color"].lower() == color_val), PALETA_COLORES_ODOO[0])
                        card_bg = palette_match["bg"]
                        card_border = palette_match["border"]
                        card_top = palette_match.get("top", palette_match["color"])
                        color_class = f"kanban-color-{palette_match['id']}"

                        sol_clean = re.sub(r'\(.*?\)', '', sol).strip()
                        desc_clean = desc.replace("\n", " ").strip()
                        desc_preview = desc_clean[:115] + ("..." if len(desc_clean) > 115 else "")

                        sol_short = sol_clean[:22]
                        area_text = f"📍 {area}" if area else ""
                        po_badge = f'<span style="background-color:#E2E8F0; color:#334155; font-size:10.5px; font-weight:700; padding:2px 6px; border-radius:4px; margin-left:6px;">PO: {row["folio_po"]}</span>' if row.get("folio_po") else ""
                        sol_badge = f'<span style="background-color:rgba(0,0,0,0.07); color:#0F172A; font-size:11px; font-weight:800; padding:2px 6px; border-radius:4px;">{sol_id}</span>' if sol_id else ""

                        card_html = f"""
                        <div class="odoo-postit-card" style="background-color:{card_bg} !important; border:1.5px solid {card_border} !important; border-top:8px solid {card_top} !important;">
                            <div>
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                                    <span style="font-size:14px; font-weight:900; color:#0F172A;">📌 {req_id}</span>
                                    {sol_badge}
                                </div>
                                <div style="font-size:12.5px; font-weight:700; color:#1E293B; line-height:1.35; margin-bottom:8px;">
                                    {desc_preview}
                                </div>
                            </div>
                            <div>
                                <div style="font-size:14px; font-weight:900; color:#059669; margin-bottom:6px; display:flex; align-items:center;">
                                    <span>💰 ${float(monto):,.2f} {moneda}</span>
                                    {po_badge}
                                </div>
                                <div style="font-size:11.5px; color:#475569; margin-bottom:6px;">
                                    👤 <strong>{sol_short}</strong> {f"&bull; {area_text}" if area_text else ""}
                                </div>
                                <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:#64748B; border-top:1px dashed rgba(0,0,0,0.12); padding-top:6px;">
                                    <span>{stars} {prioridad}</span>
                                    <span style="font-weight:700;">📑 {num_cot} cotizaciones</span>
                                </div>
                            </div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        if st.button(f"👁️ Abrir Expediente {req_id}", key=f"btn_open_{req_id}", use_container_width=True, help=f"Abrir expediente completo de {req_id}"):
                            modal_ver_expediente(req_id)

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
