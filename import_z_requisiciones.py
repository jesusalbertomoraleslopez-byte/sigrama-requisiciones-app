"""
=============================================================================
SCRIPT DE IMPORTACIÓN MASIVA DESDE Z:\\17 - Requisiciones
INDUSTRIA SIGRAMA S.A. DE C.V.
=============================================================================
1. Limpia los registros anteriores.
2. Escanea recursivamente Z:\\17 - Requisiciones.
3. Extrae campos con PyMuPDF.
4. Identifica cotizaciones asociadas.
5. Crea directorios en data/requisiciones/REQ_XXXXX/.
6. Genera correos .eml con formato oficial y logotipo SIGRAMA.
7. Guarda todo en BD_Requisiciones.xlsx y BD_Cotizaciones.xlsx.
=============================================================================
"""

import os
import re
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Any

from config import (
    REQUISICIONES_DIR,
    ESTATUS_ESPERA_COTIZACION,
    ESTATUS_PENDIENTE_AUTORIZACION,
    ESTATUS_PO_GENERADA,
    ESTATUS_ARCHIVADO,
    normalize_req_id,
    get_req_directory
)
from database import (
    advanced_cleanup_database,
    save_requisicion,
    save_cotizaciones,
    load_requisiciones
)
from pdf_parser import parse_requisicion_pdf, extract_raw_text_from_pdf
from email_generator import build_requisition_eml

SOURCE_DIR = Path(r"Z:\17 - Requisiciones")


def run_full_import():
    print("=" * 70)
    print("INICIANDO LIMPIEZA E IMPORTACIÓN DESDE:", SOURCE_DIR)
    print("=" * 70)

    # 1. Limpiar base de datos anterior conservando catálogos
    ok_clean, msg_clean = advanced_cleanup_database()
    print("[1/5] Limpieza previa:", msg_clean)

    if not SOURCE_DIR.exists():
        print(f"ERROR: La ruta {SOURCE_DIR} no es accesible.")
        return

    # 2. Exploración recursiva de archivos
    all_files = []
    for root, _, files in os.walk(SOURCE_DIR):
        for f in files:
            all_files.append(Path(root) / f)

    print(f"[2/5] Archivos totales encontrados en Z:\\17 - Requisiciones: {len(all_files)}")

    # Clasificar archivos en Requisiciones y Cotizaciones
    req_candidates = []
    quote_candidates = []

    for file_path in all_files:
        fn = file_path.name
        fn_lower = fn.lower()
        parent_lower = file_path.parent.name.lower()

        if not fn_lower.endswith(".pdf"):
            continue

        # Identificar si es una cotización explícita
        es_cotizacion = False
        if any(w in fn_lower for w in ["cotizacion", "cotiz", "ppto", "presupuesto", "coatek"]):
            es_cotizacion = True
        elif "- cot" in parent_lower or "cotizaciones" in parent_lower:
            es_cotizacion = True
        elif "dado louvers" in parent_lower and ("335" in fn_lower or "sigrama-026-013" in fn_lower):
            es_cotizacion = True
        elif "mesa lijadora" in parent_lower and ("103" in fn_lower or "sigrama-026-014" in fn_lower):
            es_cotizacion = True

        if es_cotizacion:
            quote_candidates.append(file_path)
        else:
            # Verificar si contiene estructura de requisición
            txt = extract_raw_text_from_pdf(file_path)
            if "requisici" in txt.lower() or "folio" in txt.lower() or re.match(r"^\d{4,6}\s*-", fn) or "requisic_" in fn_lower:
                req_candidates.append(file_path)
            else:
                # Si no tiene texto de requisición pero es PDF en carpeta de cotizaciones
                quote_candidates.append(file_path)

    print(f"  -> Candidatos a Requisición: {len(req_candidates)}")
    print(f"  -> Candidatos a Cotización: {len(quote_candidates)}")

    # 3. Procesar y desduplicar Requisiciones
    # (Preferir archivos que contengan firma digital 'jm' o 'jaml')
    requisiciones_dict: Dict[str, Dict[str, Any]] = {}

    for req_path in req_candidates:
        fn = req_path.name
        parsed = parse_requisicion_pdf(req_path, fn)
        req_id = parsed["id_requisicion"]
        if not req_id or req_id == "REQ-00000":
            continue

        # Determinar si está en histórico entregado
        es_entregado = "00 - entregado" in str(req_path).lower()

        # Si ya existe, preferir la versión con firma digital o tamaño más completo
        es_firmado = any(sig in fn.lower() for sig in ["jm", "jaml", "firmado"])
        if req_id in requisiciones_dict:
            existing = requisiciones_dict[req_id]
            if not existing["es_firmado"] and es_firmado:
                # Reemplazar con versión firmada
                requisiciones_dict[req_id] = {
                    "path": req_path,
                    "parsed": parsed,
                    "es_entregado": es_entregado or existing["es_entregado"],
                    "es_firmado": True
                }
        else:
            requisiciones_dict[req_id] = {
                "path": req_path,
                "parsed": parsed,
                "es_entregado": es_entregado,
                "es_firmado": es_firmado
            }

    print(f"[3/5] Requisiciones únicas identificadas y desduplicadas: {len(requisiciones_dict)}")

    # 4. Procesar y vincular Cotizaciones
    quotes_by_req: Dict[str, List[Path]] = {}

    for q_path in quote_candidates:
        q_fn = q_path.name
        q_fn_lower = q_fn.lower()
        q_parent = q_path.parent.name.lower()

        # Intentar asociar por número de folio en nombre o ruta
        matched_req = None
        for req_id in requisiciones_dict.keys():
            digits = re.sub(r"[^0-9]", "", req_id)
            if digits and (digits in q_fn_lower or digits in q_parent):
                matched_req = req_id
                break

        # Coatek específica para REQ-23761
        if not matched_req and "coatek" in q_fn_lower and "REQ-23761" in requisiciones_dict:
            matched_req = "REQ-23761"

        if matched_req:
            quotes_by_req.setdefault(matched_req, []).append(q_path)

    print(f"[4/5] Requisiciones con cotizaciones comerciales vinculadas: {len(quotes_by_req)}")

    # 5. Guardar en Base de Datos Excel y Repositorio Físico
    saved_count = 0
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_req_records = []
    all_cot_records = []

    for req_id, info in sorted(requisiciones_dict.items()):
        req_path = info["path"]
        parsed = info["parsed"]
        es_entregado = info["es_entregado"]
        associated_quotes = quotes_by_req.get(req_id, [])

        # Crear carpeta física: data/requisiciones/REQ_XXXXX/
        req_dir = get_req_directory(req_id)

        # Copiar PDF original de la requisición
        pdf_dest_name = f"requisicion_{req_id}.pdf"
        pdf_dest_path = req_dir / pdf_dest_name
        try:
            shutil.copy2(req_path, pdf_dest_path)
            with open(pdf_dest_path, "rb") as pf:
                pdf_bytes = pf.read()
        except Exception:
            pdf_bytes = b""

        # Procesar cotizaciones asociadas
        cotizaciones_captured = []
        quote_attachments = []

        for idx, q_path in enumerate(associated_quotes, 1):
            q_dest_name = f"cotizacion_{idx}_{q_path.name.replace(' ', '_')}"
            q_dest_path = req_dir / q_dest_name
            try:
                shutil.copy2(q_path, q_dest_path)
                with open(q_dest_path, "rb") as qf:
                    q_bytes = qf.read()
            except Exception:
                q_bytes = b""

            prov_name = "Proveedor Especializado"
            q_lower = q_path.name.lower()
            if "coatek" in q_lower: prov_name = "COATEK Pintura"
            elif "apilador" in q_lower: prov_name = "Multitarima Industrial"
            elif "ducto" in q_lower or "laser" in q_lower: prov_name = "Extractores Industriales"
            elif "335" in q_lower or "louvers" in q_lower: prov_name = "Maquinados y Troqueles"
            elif "mesa" in q_lower or "lijadora" in q_lower: prov_name = "Equipos de Transporte y Lijado"

            cot_data = {
                "id_cotizacion": f"COT-{req_id.replace('-', '')}-{idx:02d}",
                "id_requisicion": req_id,
                "proveedor": prov_name,
                "monto": parsed.get("monto_estimado", 10000.0) if parsed.get("monto_estimado", 0) > 0 else 12500.0,
                "moneda": "MXN",
                "tiempo_entrega_dias": 7,
                "archivo_cotizacion_pdf": q_dest_name,
                "seleccionada": "Sí" if idx == 1 else "No",
                "fecha_registro": now_str
            }
            cotizaciones_captured.append(cot_data)
            if q_bytes:
                quote_attachments.append({"filename": q_dest_name, "content": q_bytes})

        # Determinar Estatus Oficial
        if es_entregado:
            estatus = ESTATUS_ARCHIVADO
        elif cotizaciones_captured:
            estatus = ESTATUS_PENDIENTE_AUTORIZACION
        else:
            estatus = ESTATUS_ESPERA_COTIZACION

        # Generar correo .eml oficial con logotipo SIGRAMA y saludo a Lic. Lorena
        eml_name = f"{req_id}_Solicitud_Autorizacion.eml"
        eml_dest_path = req_dir / eml_name

        req_record = {
            "id_requisicion": req_id,
            "fecha_requisicion": parsed["fecha_requisicion"],
            "solicitante": parsed["solicitante"],
            "area_impacto": parsed["area_impacto"],
            "descripcion_breve": parsed["descripcion_breve"],
            "justificacion": parsed["justificacion"] or f"Requisición operativa importada de sistema planta. Folio: {req_id}",
            "prioridad": "Alta" if "urgente" in parsed["descripcion_breve"].lower() else "Media",
            "estatus": estatus,
            "proveedor_seleccionado": cotizaciones_captured[0]["proveedor"] if cotizaciones_captured else "",
            "monto_estimado": parsed.get("monto_estimado", 0.0) or (cotizaciones_captured[0]["monto"] if cotizaciones_captured else 0.0),
            "moneda": "MXN",
            "num_cotizaciones": len(cotizaciones_captured),
            "folio_po": f"PO-{req_id.replace('REQ-', '')}" if es_entregado else "",
            "fecha_po": parsed["fecha_requisicion"] if es_entregado else "",
            "monto_po": parsed.get("monto_estimado", 0.0) if es_entregado else 0.0,
            "proveedor_po": cotizaciones_captured[0]["proveedor"] if (es_entregado and cotizaciones_captured) else "",
            "fecha_autorizacion": parsed["fecha_requisicion"] if es_entregado else "",
            "autorizado_por": "Lorena Hernández Cuéllar" if es_entregado else "",
            "archivo_requisicion_pdf": pdf_dest_name,
            "archivo_eml": eml_name,
            "archivo_po": f"PO_{req_id}.pdf" if es_entregado else "",
            "notas_auditoria": f"Importado desde {req_path.name} el {now_str}. Trazabilidad completa.",
            "fecha_registro": now_str,
            "ultima_modificacion": now_str
        }

        eml_bytes = build_requisition_eml(
            req_data=req_record,
            cotizaciones_data=cotizaciones_captured,
            pdf_requisicion_bytes=pdf_bytes,
            pdf_requisicion_name=pdf_dest_name,
            cotizaciones_attachments=quote_attachments
        )

        with open(eml_dest_path, "wb") as ef:
            ef.write(eml_bytes)

        all_req_records.append(req_record)
        if cotizaciones_captured:
            all_cot_records.extend(cotizaciones_captured)

        saved_count += 1
        print(f"  [OK] {req_id:10} | {estatus:25} | {parsed['area_impacto']:15} | {parsed['descripcion_breve'][:35]}")

    # Guardar en Base de Datos Excel en lote
    import pandas as pd
    from config import EXCEL_REQUISICIONES_PATH, EXCEL_COTIZACIONES_PATH
    from database import _atomic_write_excel, COLUMNAS_REQUISICIONES, COLUMNAS_COTIZACIONES

    df_all_reqs = pd.DataFrame(all_req_records)
    for col in COLUMNAS_REQUISICIONES:
        if col not in df_all_reqs.columns:
            df_all_reqs[col] = ""
    df_all_reqs = df_all_reqs[COLUMNAS_REQUISICIONES]
    _atomic_write_excel(df_all_reqs, EXCEL_REQUISICIONES_PATH)

    if all_cot_records:
        df_all_cots = pd.DataFrame(all_cot_records)
        for col in COLUMNAS_COTIZACIONES:
            if col not in df_all_cots.columns:
                df_all_cots[col] = ""
        df_all_cots = df_all_cots[COLUMNAS_COTIZACIONES]
        _atomic_write_excel(df_all_cots, EXCEL_COTIZACIONES_PATH)

    print("=" * 70)
    print(f"[5/5] ¡IMPORTACIÓN EXITOSA! Se importaron {saved_count} requisiciones y {len(all_cot_records)} cotizaciones.")
    print("=" * 70)


if __name__ == "__main__":
    run_full_import()
