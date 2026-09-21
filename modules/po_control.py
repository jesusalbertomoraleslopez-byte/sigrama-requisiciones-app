"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo 2: Control de Orden de Compra (PO) y Cierre de Ciclo de Auditoría
=============================================================================
"""

import os
import datetime
from pathlib import Path
from typing import Dict, Any

import streamlit as st
import pandas as pd

from config import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    DIRECTORES_DEFAULT,
    ESTATUS_PO_GENERADA,
    ESTATUS_PENDIENTE_AUTORIZACION,
    ESTATUS_ESPERA_COTIZACION,
    normalize_req_id,
    get_req_directory
)
from database import (
    load_requisiciones,
    load_cotizaciones,
    get_requisicion_by_id,
    update_requisicion_po,
    load_catalogos
)


def render_po_control():
    """Renderiza el módulo de control y formalización de Orden de Compra (PO)."""
    st.markdown("""
    <div style="background-color:#FFFFFF; border-left:5px solid #10B981; padding:16px 20px; border-radius:6px; margin-bottom:20px; box-shadow:0 2px 6px rgba(0,0,0,0.04); border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0; border-bottom:1px solid #E2E8F0;">
        <div style="font-size:18px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.5px;">
            📑 Control y Vinculación de Orden de Compra (PO)
        </div>
        <div style="font-size:13px; color:#64748B; margin-top:4px;">
            Cierre del ciclo de control: Asociación formal de PO autorizada, archivo probatorio (PDF o EML) y sellos para auditoría en México.
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_reqs = load_requisiciones()
    if df_reqs.empty:
        st.warning("⚠️ No hay requisiciones registradas en el sistema. Registra una requisición primero.")
        return

    # Catálogos
    catalogos = load_catalogos()
    proveedores_list = catalogos.get("proveedores", [])
    directores_nombres = [d["nombre"] for d in DIRECTORES_DEFAULT]

    # Filtro de búsqueda rápida
    col_search, col_filter = st.columns([2, 1.5])
    with col_search:
        search_query = st.text_input("🔍 Buscar Requisición por Folio, Solicitante o Descripción:", "").strip().lower()
    
    with col_filter:
        ver_todas = st.checkbox("Mostrar también requisiciones con PO ya generada", value=False)

    # Filtrar según estatus y búsqueda
    if not ver_todas:
        df_filtered = df_reqs[df_reqs["estatus"] != ESTATUS_PO_GENERADA]
    else:
        df_filtered = df_reqs.copy()

    if search_query:
        mask = (
            df_filtered["id_requisicion"].str.lower().str.contains(search_query) |
            df_filtered.get("folio_solicitud", pd.Series("", index=df_filtered.index)).str.lower().str.contains(search_query) |
            df_filtered["solicitante"].str.lower().str.contains(search_query) |
            df_filtered["descripcion_breve"].str.lower().str.contains(search_query)
        )
        df_filtered = df_filtered[mask]

    if df_filtered.empty:
        st.info("No se encontraron requisiciones pendientes que coincidan con la búsqueda.")
        return

    # Lista de opciones para selector
    options_list = []
    for _, row in df_filtered.iterrows():
        rid = row["id_requisicion"]
        sol_p = f"[{row.get('folio_solicitud', '')}] " if row.get("folio_solicitud") else ""
        desc = row["descripcion_breve"][:40]
        est = row["estatus"]
        sol = row["solicitante"][:25]
        options_list.append(f"{rid} | {sol_p}{est} | {sol} | {desc}")

    selected_option = st.selectbox(
        "Seleccionar Requisición para procesar:",
        options=options_list,
        index=0
    )

    selected_req_id = selected_option.split(" | ")[0].strip()
    req_data = get_requisicion_by_id(selected_req_id)

    if not req_data:
        st.error("No se pudo cargar la información de la requisición seleccionada.")
        return

    # =========================================================================
    # RESUMEN EJECUTIVO DE LA REQUISICIÓN SELECCIONADA
    # =========================================================================
    st.markdown("##### 📌 Expediente Actual de la Requisición")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Folio Requisición", req_data.get("id_requisicion"), delta=f"Interno: {req_data.get('folio_solicitud', '-')}", delta_color="off")
    c2.metric("Fecha Solicitud", req_data.get("fecha_requisicion"))
    c3.metric("Área de Impacto", req_data.get("area_impacto"))
    c4.metric("Estatus Actual", req_data.get("estatus"))

    st.markdown(f"""
    <div style="background-color:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px 16px; margin-bottom:16px; font-size:13px;">
        <div><strong>Descripción:</strong> {req_data.get('descripcion_breve')}</div>
        <div style="margin-top:4px;"><strong>Solicitante:</strong> {req_data.get('solicitante')}</div>
        <div style="margin-top:4px;"><strong>Proveedor Sugerido / Seleccionado:</strong> {req_data.get('proveedor_seleccionado') or 'No definido'} &bull; <strong>Monto Estimado:</strong> ${float(req_data.get('monto_estimado', 0)):,.2f} {req_data.get('moneda', 'MXN')}</div>
    </div>
    """, unsafe_allow_html=True)

    # Mostrar cotizaciones si existen
    df_cot = load_cotizaciones(selected_req_id)
    if not df_cot.empty:
        with st.expander(f"📊 Cotizaciones asociadas ({len(df_cot)})", expanded=False):
            st.dataframe(
                df_cot[["proveedor", "monto", "moneda", "tiempo_entrega_dias", "seleccionada", "archivo_cotizacion_pdf"]],
                use_container_width=True,
                hide_index=True
            )

    st.markdown("---")

    # =========================================================================
    # FORMULARIO DE FORMALIZACIÓN DE ORDEN DE COMPRA (PO)
    # =========================================================================
    st.markdown("##### 📝 Registro de Orden de Compra Oficial (PO)")

    col_folio, col_fecha_po, col_autoriza = st.columns([1.5, 1.2, 1.5])
    
    with col_folio:
        po_folio_input = st.text_input(
            "Folio de Orden de Compra (PO):",
            value=req_data.get("folio_po") or f"PO-{datetime.datetime.now().strftime('%y%m')}-{selected_req_id.replace('REQ-', '')}",
            placeholder="Ej. PO-2609-10425"
        )

    with col_fecha_po:
        po_fecha_input = st.date_input(
            "Fecha de Emisión de PO:",
            value=datetime.date.today()
        )

    with col_autoriza:
        po_autoriza_input = st.selectbox(
            "Director que Otorgó Visto Bueno:",
            options=directores_nombres,
            index=0
        )

    col_prov_po, col_monto_po = st.columns([2, 1.5])
    
    with col_prov_po:
        # Sugerir el proveedor seleccionado en la requisición
        default_prov = req_data.get("proveedor_seleccionado") or (proveedores_list[0] if proveedores_list else "")
        prov_index = proveedores_list.index(default_prov) if default_prov in proveedores_list else 0
        po_prov_input = st.selectbox(
            "Proveedor Adjudicado:",
            options=proveedores_list,
            index=prov_index
        )

    with col_monto_po:
        default_monto = float(req_data.get("monto_po") or req_data.get("monto_estimado") or 0.0)
        po_monto_input = st.number_input(
            "Monto Final de la PO ($):",
            min_value=0.0,
            value=default_monto,
            step=100.0,
            format="%.2f"
        )

    st.markdown("##### 📎 Archivo Probatorio de PO / Autorización")
    st.caption("Carga el documento emitido de la PO en PDF o el archivo de correo (.eml) donde el director confirmó la autorización:")

    po_file = st.file_uploader(
        "Subir Archivo de PO o Correo de Aprobación:",
        type=["pdf", "eml"],
        key="po_file_uploader_key"
    )

    po_notas_input = st.text_area(
        "Notas de Auditoría / Justificación Fiscal (SAT / Corporativo):",
        value="",
        placeholder="Ej. Autorizado con visto bueno de Dirección General. Entrega pactada en Planta Metales.",
        height=70
    )

    if st.button("✅ Formalizar Orden de Compra y Cerrar Ciclo", type="primary", use_container_width=True):
        if not po_folio_input:
            st.error("⚠️ El número o folio de la Orden de Compra (PO) es obligatorio.")
            return

        # 1. Guardar archivo probatorio en la carpeta física de la requisición
        saved_filename = req_data.get("archivo_po", "")
        req_folder = get_req_directory(selected_req_id)

        if po_file is not None:
            safe_po_name = f"PO_{po_folio_input.replace('/', '_').replace('-', '_')}_{po_file.name}"
            target_po_path = req_folder / safe_po_name
            with open(target_po_path, "wb") as pf:
                pf.write(po_file.getvalue())
            saved_filename = safe_po_name

        # 2. Actualizar estado y registrar auditoría en BD_Requisiciones.xlsx
        success = update_requisicion_po(
            req_id=selected_req_id,
            folio_po=po_folio_input,
            fecha_po=po_fecha_input.strftime("%Y-%m-%d"),
            monto_po=po_monto_input,
            proveedor_po=po_prov_input,
            autorizado_por=po_autoriza_input,
            archivo_po_name=saved_filename,
            notas=po_notas_input
        )

        if success:
            st.success(f"🎉 Orden de Compra {po_folio_input} asociada exitosamente a la Requisición {selected_req_id}. Ciclo de control cerrado.")
            st.balloons()
        else:
            st.error("Ocurrió un error al intentar actualizar la requisición.")
