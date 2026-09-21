"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo 1: Asistente de Registro, Extracción, Cotizaciones y Correo (.eml)
=============================================================================
"""

import os
import shutil
import datetime
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st

from config import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_CARD_BG,
    COLOR_BORDER,
    AREAS_IMPACTO_DEFAULT,
    SOLICITANTES_DEFAULT,
    PROVEEDORES_DEFAULT,
    DIRECTORES_DEFAULT,
    ESTATUS_ESPERA_COTIZACION,
    ESTATUS_PENDIENTE_AUTORIZACION,
    normalize_req_id,
    get_req_directory,
    get_folder_name_for_req
)
from pdf_parser import parse_requisicion_pdf
from database import (
    load_catalogos,
    save_requisicion,
    save_cotizaciones,
    get_requisicion_by_id
)
from email_generator import build_requisition_eml


def render_requisition_wizard():
    """Renderiza el flujo completo de registro de requisición."""
    st.markdown("""
    <div style="background-color:#FFFFFF; border-left:5px solid #EC2024; padding:16px 20px; border-radius:6px; margin-bottom:20px; box-shadow:0 2px 6px rgba(0,0,0,0.04); border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0; border-bottom:1px solid #E2E8F0;">
        <div style="font-size:18px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.5px;">
            📝 Registro de Requisición y Generación de Expediente
        </div>
        <div style="font-size:13px; color:#64748B; margin-top:4px;">
            Fase 1: Extracción inteligente desde PDF original, captura de cotizaciones de proveedores y compilación de correo ejecutivo (.eml).
        </div>
    </div>
    """, unsafe_allow_html=True)

    catalogos = load_catalogos()
    areas_list = catalogos.get("areas_impacto", AREAS_IMPACTO_DEFAULT)
    solicitantes_list = catalogos.get("solicitantes", SOLICITANTES_DEFAULT)
    proveedores_list = catalogos.get("proveedores", PROVEEDORES_DEFAULT)

    # Inicializar estado en sesión si no existe
    if "req_wizard_data" not in st.session_state:
        st.session_state.req_wizard_data = {
            "id_requisicion": "",
            "fecha_requisicion": datetime.date.today(),
            "solicitante": solicitantes_list[0] if solicitantes_list else "",
            "area_impacto": areas_list[0] if areas_list else "Materiales",
            "descripcion_breve": "",
            "justificacion": "",
            "prioridad": "Media",
            "monto_estimado": 0.0,
            "moneda": "MXN",
            "pdf_uploaded_bytes": None,
            "pdf_uploaded_name": "",
            "parsed": False
        }

    # =========================================================================
    # PASO 1: CARGA DE REQUISICIÓN ORIGINAL (PDF)
    # =========================================================================
    st.markdown("#### 1. Carga de Requisición Original (PDF del Sistema)")

    col_upload, col_sample = st.columns([2, 1])

    with col_upload:
        uploaded_pdf = st.file_uploader(
            "Cargar archivo PDF de requisición:",
            type=["pdf"],
            key="req_pdf_file_input",
            help="Sube el archivo PDF generado por el ERP o sistema de SIGRAMA."
        )

    with col_sample:
        # Explorador asistido de muestras si existe Z:\17 - Requisiciones o Q:\002 - Requisiciones
        possible_dirs = [Path(r"Z:\17 - Requisiciones"), Path(r"Q:\002 - Requisiciones")]
        sample_dict = {}
        for p_dir in possible_dirs:
            if p_dir.exists():
                for f in p_dir.glob("*.pdf"):
                    if not any(w in f.name.lower() for w in ["cot", "ppto"]):
                        sample_dict[f"{f.name} ({p_dir.drive})"] = f
        
        sample_options = ["(Ninguno)"] + list(sample_dict.keys())[:30]

        selected_sample = st.selectbox(
            "O seleccionar archivo directo de Z:\\17 - Requisiciones:",
            options=sample_options,
            index=0,
            help="Atajo directo a las requisiciones reales en la unidad de red."
        )

    # Procesar archivo cargado o seleccionado
    current_pdf_bytes = None
    current_pdf_name = ""

    if uploaded_pdf is not None:
        current_pdf_bytes = uploaded_pdf.getvalue()
        current_pdf_name = uploaded_pdf.name
    elif selected_sample != "(Ninguno)" and selected_sample in sample_dict:
        sample_path = sample_dict[selected_sample]
        if sample_path.exists():
            with open(sample_path, "rb") as sf:
                current_pdf_bytes = sf.read()
            current_pdf_name = sample_path.name

    # Si se cargó un nuevo PDF y aún no ha sido procesado
    if current_pdf_bytes and (st.session_state.req_wizard_data.get("pdf_uploaded_name") != current_pdf_name):
        extracted = parse_requisicion_pdf(current_pdf_bytes, current_pdf_name)
        
        # Parsear fecha
        try:
            f_date = datetime.datetime.strptime(extracted["fecha_requisicion"], "%Y-%m-%d").date()
        except Exception:
            f_date = datetime.date.today()

        # Validar solicitante en lista
        sol_val = extracted["solicitante"]
        if sol_val not in solicitantes_list:
            # Buscar el más cercano o agregarlo
            matched = False
            for s in solicitantes_list:
                if sol_val.lower() in s.lower() or s.lower() in sol_val.lower():
                    sol_val = s
                    matched = True
                    break
            if not matched and sol_val:
                solicitantes_list.insert(0, sol_val)

        # Validar área en lista
        area_val = extracted["area_impacto"]
        if area_val not in areas_list:
            for a in areas_list:
                if a.lower() in area_val.lower() or area_val.lower() in a.lower():
                    area_val = a
                    break

        st.session_state.req_wizard_data = {
            "id_requisicion": extracted["id_requisicion"],
            "fecha_requisicion": f_date,
            "solicitante": sol_val if sol_val in solicitantes_list else solicitantes_list[0],
            "area_impacto": area_val if area_val in areas_list else areas_list[0],
            "descripcion_breve": extracted["descripcion_breve"],
            "justificacion": extracted["justificacion"],
            "prioridad": "Alta" if "urgente" in extracted["descripcion_breve"].lower() else "Media",
            "monto_estimado": extracted.get("monto_estimado", 0.0),
            "moneda": "MXN",
            "pdf_uploaded_bytes": current_pdf_bytes,
            "pdf_uploaded_name": current_pdf_name,
            "parsed": True
        }
        st.toast(f"✅ Requisición {extracted['id_requisicion']} extraída exitosamente con PyMuPDF", icon="📄")

    # =========================================================================
    # FORMULARIO DE VALIDACIÓN Y CONFIRMACIÓN DE CAMPOS EXTRAÍDOS
    # =========================================================================
    data_state = st.session_state.req_wizard_data

    st.markdown("##### 📌 Datos Clave de la Requisición (Revisión y Ajuste)")

    col_id, col_fecha, col_prioridad = st.columns([1.5, 1.2, 1.3])
    with col_id:
        req_id_input = st.text_input(
            "ID Requisición (Folio):",
            value=data_state["id_requisicion"] or "REQ-26001",
            help="Formato estándar REQ-XXXXX o REQ XXXXX."
        )
    with col_fecha:
        fecha_input = st.date_input(
            "Fecha de Requisición:",
            value=data_state["fecha_requisicion"]
        )
    with col_prioridad:
        prioridad_input = st.selectbox(
            "Prioridad Operativa:",
            options=["Baja", "Media", "Alta", "Urgente"],
            index=["Baja", "Media", "Alta", "Urgente"].index(data_state.get("prioridad", "Media"))
        )

    col_sol, col_area = st.columns([2, 1.5])
    with col_sol:
        # Índice seguro para solicitante
        curr_sol = data_state["solicitante"]
        sol_idx = solicitantes_list.index(curr_sol) if curr_sol in solicitantes_list else 0
        solicitante_input = st.selectbox(
            "Solicitante (Quién elaboró):",
            options=solicitantes_list,
            index=sol_idx
        )
    with col_area:
        curr_area = data_state["area_impacto"]
        area_idx = areas_list.index(curr_area) if curr_area in areas_list else 0
        area_input = st.selectbox(
            "Área de Impacto (Destino de Presupuesto):",
            options=areas_list,
            index=area_idx,
            help="Clasificación obligatoria para control de costos e imputación contable."
        )

    col_desc, col_monto = st.columns([3, 1.2])
    with col_desc:
        descripcion_input = st.text_input(
            "Descripción Breve:",
            value=data_state["descripcion_breve"],
            placeholder="Ej. Suministro de herramental de corte para centro de maquinado"
        )
    with col_monto:
        monto_est_input = st.number_input(
            "Monto Estimado Sugerido ($):",
            min_value=0.0,
            value=float(data_state.get("monto_estimado", 0.0)),
            step=100.0,
            format="%.2f"
        )

    justificacion_input = st.text_area(
        "Justificación Operativa / Observaciones del Sistema:",
        value=data_state["justificacion"],
        placeholder="Motivo de la adquisición, cliente de destino o referencias de cotizaciones previas.",
        height=80
    )

    st.markdown("---")

    # =========================================================================
    # PASO 2: ADJUNTAR COTIZACIONES DE PROVEEDORES (MÚLTIPLE)
    # =========================================================================
    st.markdown("#### 2. Adjuntar Cotizaciones de Proveedores (Múltiples PDFs)")
    st.caption("Carga las cotizaciones comerciales en PDF correspondientes a esta requisición para evaluación comparativa.")

    quotes_files = st.file_uploader(
        "Subir Cotizaciones en PDF (Selecciona uno o varios archivos):",
        type=["pdf"],
        accept_multiple_files=True,
        key="multi_quotes_uploader"
    )

    cotizaciones_captured = []
    
    if quotes_files:
        st.markdown(f"**Se han cargado {len(quotes_files)} cotización(es). Detalla la información comercial:**")
        
        for idx, q_file in enumerate(quotes_files, 1):
            with st.expander(f"📄 Cotización #{idx}: {q_file.name}", expanded=True):
                c_prov, c_monto, c_mon, c_dias, c_sel = st.columns([2.5, 1.5, 1, 1.2, 1.3])
                
                with c_prov:
                    # Sugerir proveedor si el nombre del archivo contiene alguno
                    prov_match_idx = 0
                    for p_i, p_name in enumerate(proveedores_list):
                        if any(term in q_file.name.lower() for term in p_name.lower().split()[:2]):
                            prov_match_idx = p_i
                            break
                    
                    prov_val = st.selectbox(
                        f"Proveedor #{idx}:",
                        options=proveedores_list,
                        index=prov_match_idx,
                        key=f"cot_prov_{idx}"
                    )
                
                with c_monto:
                    monto_val = st.number_input(
                        f"Monto #{idx}:",
                        min_value=0.0,
                        value=float(monto_est_input) if idx == 1 and monto_est_input > 0 else 1000.0,
                        step=100.0,
                        format="%.2f",
                        key=f"cot_monto_{idx}"
                    )
                
                with c_mon:
                    mon_val = st.selectbox(
                        f"Moneda #{idx}:",
                        options=["MXN", "USD", "EUR"],
                        index=0,
                        key=f"cot_mon_{idx}"
                    )
                
                with c_dias:
                    dias_val = st.number_input(
                        f"Entrega (días):",
                        min_value=1,
                        max_value=180,
                        value=7,
                        step=1,
                        key=f"cot_dias_{idx}"
                    )
                
                with c_sel:
                    st.write("")
                    st.write("")
                    es_seleccionada = st.checkbox(
                        "Recomendada",
                        value=(idx == 1),
                        key=f"cot_sel_{idx}",
                        help="Marca la cotización con mejor relación costo-beneficio para solicitar aprobación."
                    )

                cotizaciones_captured.append({
                    "id_cotizacion": f"COT-{normalize_req_id(req_id_input).replace('-', '')}-{idx:02d}",
                    "id_requisicion": normalize_req_id(req_id_input),
                    "proveedor": prov_val,
                    "monto": monto_val,
                    "moneda": mon_val,
                    "tiempo_entrega_dias": dias_val,
                    "archivo_cotizacion_pdf": q_file.name,
                    "seleccionada": "Sí" if es_seleccionada else "No",
                    "file_bytes": q_file.getvalue()
                })
    else:
        st.info("ℹ️ Puedes registrar la requisición ahora en estado 'En Espera de Cotización' o cargar las cotizaciones para solicitar autorización inmediata a Directores.")

    st.markdown("---")

    # =========================================================================
    # PASO 3: GENERACIÓN INSTANTÁNEA DE CORREO (.EML) Y GUARDADO
    # =========================================================================
    st.markdown("#### 3. Generación Instantánea de Correo (.eml) y Registro")

    norm_req_id = normalize_req_id(req_id_input)
    # Estructura estricta del asunto: 'REQ XXXXX - Descripción Breve - Fecha - Área'
    fecha_str = fecha_input.strftime("%Y-%m-%d")
    strict_subject = f"{norm_req_id} - {descripcion_input} - {fecha_str} - {area_input}"

    st.markdown(f"""
    <div style="background-color:#F8FAFC; border:1px solid #CBD5E1; border-radius:6px; padding:14px; margin-bottom:16px;">
        <div style="font-size:12px; font-weight:700; color:#475569; text-transform:uppercase;">Asunto Normativo del Correo:</div>
        <div style="font-size:15px; font-weight:800; color:#0F172A; margin-top:2px;">{strict_subject}</div>
        <div style="font-size:12px; color:#1E293B; margin-top:6px;">
            ✉️ <strong>Para (Autorización):</strong> Lorena Hernandez Cuellar &lt;lhernandez@sigrama.com.mx&gt;
        </div>
        <div style="font-size:11px; color:#64748B; margin-top:3px;">
            📋 <strong>Con copia (Cc):</strong> Bryan Flores &bull; Cruz Carreón &bull; José Fernández &bull; Luis Quintana &bull; Jesús Morales
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Preparar diccionario para guardado y generación
    req_to_save = {
        "id_requisicion": norm_req_id,
        "fecha_requisicion": fecha_str,
        "solicitante": solicitante_input,
        "area_impacto": area_input,
        "descripcion_breve": descripcion_input,
        "justificacion": justificacion_input,
        "prioridad": prioridad_input,
        "estatus": ESTATUS_PENDIENTE_AUTORIZACION if cotizaciones_captured else ESTATUS_ESPERA_COTIZACION,
        "proveedor_seleccionado": "",
        "monto_estimado": monto_est_input,
        "moneda": "MXN",
        "num_cotizaciones": len(cotizaciones_captured),
        "folio_po": "",
        "fecha_po": "",
        "monto_po": 0.0,
        "proveedor_po": "",
        "fecha_autorizacion": "",
        "autorizado_por": "",
        "archivo_requisicion_pdf": f"requisicion_{norm_req_id}.pdf" if data_state.get("pdf_uploaded_bytes") else "",
        "archivo_eml": f"{norm_req_id}_Solicitud_Autorizacion.eml",
        "archivo_po": "",
        "notas_auditoria": f"Registrado el {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}. Flujo inicial completado.",
        "fecha_registro": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ultima_modificacion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Si hay cotización seleccionada, asignar proveedor y monto a la requisición
    for cot in cotizaciones_captured:
        if cot["seleccionada"] == "Sí":
            req_to_save["proveedor_seleccionado"] = cot["proveedor"]
            req_to_save["monto_estimado"] = cot["monto"]
            req_to_save["moneda"] = cot["moneda"]
            break

    # Preparar adjuntos para el correo .eml
    quote_attachments = [
        {"filename": c["archivo_cotizacion_pdf"], "content": c["file_bytes"]}
        for c in cotizaciones_captured if "file_bytes" in c
    ]

    eml_bytes = build_requisition_eml(
        req_data=req_to_save,
        cotizaciones_data=cotizaciones_captured,
        pdf_requisicion_bytes=data_state.get("pdf_uploaded_bytes"),
        pdf_requisicion_name=f"requisicion_{norm_req_id}.pdf",
        cotizaciones_attachments=quote_attachments,
        planta=st.session_state.get("app_planta_activa", "Planta Metales")
    )

    col_btn_eml, col_btn_save = st.columns([1.5, 2])

    with col_btn_eml:
        st.download_button(
            label="📧 Descargar Correo (.eml) Listo",
            data=eml_bytes,
            file_name=f"{norm_req_id}_Solicitud_Autorizacion.eml",
            mime="message/rfc822",
            help="Genera un correo RFC 822 compatible con Outlook o Thunderbird con los PDFs adjuntos incrustados.",
            use_container_width=True
        )

    with col_btn_save:
        if st.button("💾 Guardar Requisición y Almacenar Archivos", type="primary", use_container_width=True):
            if not descripcion_input:
                st.error("⚠️ Por favor ingresa una descripción breve antes de guardar.")
                return

            # 1. Crear carpeta física para la requisición: data/requisiciones/REQ_XXXXX/
            req_folder = get_req_directory(norm_req_id)

            # 2. Guardar PDF de la requisición original si existe
            if data_state.get("pdf_uploaded_bytes"):
                pdf_target_path = req_folder / f"requisicion_{norm_req_id}.pdf"
                with open(pdf_target_path, "wb") as pf:
                    pf.write(data_state["pdf_uploaded_bytes"])

            # 3. Guardar cotizaciones en disco local
            for cot in cotizaciones_captured:
                if "file_bytes" in cot:
                    safe_fn = cot["archivo_cotizacion_pdf"].replace(" ", "_")
                    cot_target_path = req_folder / f"cotizacion_{cot['id_cotizacion']}_{safe_fn}"
                    with open(cot_target_path, "wb") as cf:
                        cf.write(cot["file_bytes"])
                    # Actualizar nombre del archivo guardado
                    cot["archivo_cotizacion_pdf"] = cot_target_path.name

            # 4. Guardar archivo .eml compilado en disco local
            eml_target_path = req_folder / f"{norm_req_id}_Solicitud_Autorizacion.eml"
            with open(eml_target_path, "wb") as ef:
                ef.write(eml_bytes)

            # 5. Persistir en Base de Datos Excel
            save_requisicion(req_to_save)
            if cotizaciones_captured:
                save_cotizaciones(norm_req_id, cotizaciones_captured)

            if "ultimos_folios_cargados" not in st.session_state:
                st.session_state["ultimos_folios_cargados"] = []
            if norm_req_id not in st.session_state["ultimos_folios_cargados"]:
                st.session_state["ultimos_folios_cargados"].append(norm_req_id)

            st.success(f"🎉 Requisición {norm_req_id} guardada con éxito en BD_Requisiciones.xlsx y repositorio físico: {req_folder}")
            st.balloons()
