"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo de Extracción Inteligente de Documentos PDF (PyMuPDF / Regex)
=============================================================================
Calibrado y validado contra el formato real del sistema de requisiciones
de Industria SIGRAMA S.A. de C.V. (ej. reportes generados en planta).

Campos extraídos automáticamente:
- Folio de la requisición (normalizado a REQ-XXXXX)
- Fecha de la requisición (formato ISO YYYY-MM-DD)
- Solicitante / Usuario que elaboró
- Departamento y Área de Impacto
- Descripción Breve (del catálogo de conceptos, partidas o nombre de archivo)
- Justificación / Observaciones y datos de cotizaciones previas
- Monto estimado (si está presente en subtotales del sistema)
=============================================================================
"""

import os
import re
import datetime
from pathlib import Path
from typing import Dict, Any, Union, Optional, List

# Soporte para PyMuPDF moderno o legado fitz
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from config import (
    AREAS_IMPACTO_DEFAULT,
    SOLICITANTES_DEFAULT,
    normalize_req_id
)

MESES_ESPANOL = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "setiembre": "09", "octubre": "10",
    "noviembre": "11", "diciembre": "12"
}


def extract_raw_text_from_pdf(pdf_source: Union[str, Path, bytes]) -> str:
    """Extrae el contenido de texto plano de todas las páginas del PDF con PyMuPDF."""
    if fitz is None:
        return ""

    text = ""
    try:
        if isinstance(pdf_source, (str, Path)):
            doc = fitz.open(str(pdf_source))
        else:
            doc = fitz.open(stream=pdf_source, filetype="pdf")

        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
    except Exception as e:
        print(f"Error al extraer texto con PyMuPDF: {e}")
    return text


def parse_requisicion_pdf(
    pdf_source: Union[str, Path, bytes],
    original_filename: str = ""
) -> Dict[str, Any]:
    """
    Analiza a fondo una requisición en PDF del sistema de Industria SIGRAMA y
    retorna un diccionario estructurado listo para auto-llenar los formularios.
    """
    raw_text = extract_raw_text_from_pdf(pdf_source)
    filename = original_filename or ""
    if isinstance(pdf_source, (str, Path)) and not filename:
        filename = os.path.basename(str(pdf_source))

    extracted = {
        "id_requisicion": "",
        "fecha_requisicion": datetime.date.today().strftime("%Y-%m-%d"),
        "solicitante": "",
        "area_impacto": "Materiales",
        "descripcion_breve": "",
        "justificacion": "",
        "monto_estimado": 0.0,
        "moneda": "MXN",
        "observaciones_extraidas": "",
        "confianza": "alta",
        "texto_extraido": raw_text[:800] if raw_text else ""
    }

    # =========================================================================
    # 1. EXTRACCIÓN DEL FOLIO / ID DE REQUISICIÓN
    # =========================================================================
    # Heurística A: Nombre de archivo como "21092 - MAQUINADOS...", "23297 - ...", "REQ-10425..."
    m_fn = re.match(r"^(\d{4,6})\s*[-_]", filename)
    if m_fn:
        extracted["id_requisicion"] = normalize_req_id(m_fn.group(1))

    # Heurística B: Formato estándar SIGRAMA en el cuerpo del PDF:
    # "Folio de la requisición:\nFecha de la requisición:\n23761\nSeptiembre 21, 2026"
    if not extracted["id_requisicion"]:
        m_body = re.search(
            r"Folio de la requisici[oó]n:\s*(?:Fecha de la requisici[oó]n:\s*)?(\d{4,6})",
            raw_text,
            re.IGNORECASE
        )
        if m_body:
            extracted["id_requisicion"] = normalize_req_id(m_body.group(1))

    # Heurística C: Bloque "Folio ... \n {DIGITOS}"
    if not extracted["id_requisicion"]:
        m_block = re.search(r"(?:Folio[^\n]*\n+)(\d{4,6})", raw_text, re.IGNORECASE)
        if m_block:
            extracted["id_requisicion"] = normalize_req_id(m_block.group(1))

    # Heurística D: Patrones genéricos de respaldo
    if not extracted["id_requisicion"]:
        for pat in [
            r"(?i)\b(REQ[\s\-_]?[0-9]{3,7})\b",
            r"(?i)No\.?\s*Requisici[oó]n[\s:]*([0-9]{3,7})"
        ]:
            m = re.search(pat, raw_text)
            if m:
                extracted["id_requisicion"] = normalize_req_id(m.group(1))
                break

    # =========================================================================
    # 2. EXTRACCIÓN DE LA FECHA DE LA REQUISICIÓN
    # =========================================================================
    # Heurística A: "Septiembre 21, 2026" o "Agosto 17, 2026"
    m_spanish_date = re.search(r"([A-Za-zñáéíóú]+)\s+(\d{1,2}),\s+(\d{4})", raw_text)
    if m_spanish_date:
        mes_word = m_spanish_date.group(1).lower()
        if mes_word in MESES_ESPANOL:
            mes_num = MESES_ESPANOL[mes_word]
            dia_num = int(m_spanish_date.group(2))
            anio_num = m_spanish_date.group(3)
            extracted["fecha_requisicion"] = f"{anio_num}-{mes_num}-{dia_num:02d}"

    # Heurística B: "Fecha de Entrega: 21/09/2026"
    if not extracted["fecha_requisicion"] or extracted["fecha_requisicion"] == datetime.date.today().strftime("%Y-%m-%d"):
        m_ent = re.search(r"Fecha de Entrega:\s*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", raw_text, re.IGNORECASE)
        if m_ent:
            d, m, y = m_ent.group(1), m_ent.group(2), m_ent.group(3)
            extracted["fecha_requisicion"] = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

    # =========================================================================
    # 3. EXTRACCIÓN DE SOLICITANTE / USUARIO QUE ELABORÓ
    # =========================================================================
    # Formato SIGRAMA:
    # "Usuario\nJESUS ALBERTO MORALES\nDIRECCION"
    m_user = re.search(r"Usuario\s*\n+([A-ZÁÉÍÓÚÑ\s\.\-]{3,45})\n", raw_text)
    if m_user:
        raw_user = m_user.group(1).replace("\r", " ").replace("\n", " ").strip()
        # Limpiar si tomó una línea vacía o palabra clave
        if raw_user not in ("DIRECCION", "SISTEMAS", "MAQUINADO", "Status", "Página"):
            extracted["solicitante"] = " ".join(raw_user.split()).title()

    # Si no se encontró por 'Usuario', buscar firma digital:
    # "Firmado digitalmente por Ing. Jesús Morales"
    if not extracted["solicitante"]:
        m_sign = re.search(r"Firmado\s+digitalmente\s+por\s+([^\n\r]+)", raw_text, re.IGNORECASE)
        if m_sign:
            extracted["solicitante"] = " ".join(m_sign.group(1).replace("\r", " ").replace("\n", " ").split()).strip()

    # Homologar con catálogo de solicitantes si coincide
    if extracted["solicitante"]:
        for sol_cat in SOLICITANTES_DEFAULT:
            first_name = extracted["solicitante"].split()[0].lower()
            if first_name in sol_cat.lower():
                extracted["solicitante"] = sol_cat
                break

    # =========================================================================
    # 4. EXTRACCIÓN DE ÁREA DE IMPACTO
    # =========================================================================
    # Mapeo inteligente de Atributos del sistema SIGRAMA a las 6 áreas oficiales:
    # (Materiales, Mano de Obra, Supervisión, Gastos Generales, Herramientas, Maquinaria)
    raw_lower = raw_text.lower()

    if "herramental" in raw_lower or "brocas" in raw_lower or "carburo" in raw_lower or "fresas" in raw_lower or "cortador" in raw_lower:
        extracted["area_impacto"] = "Herramientas"
    elif "maquinaria" in raw_lower or "maq y equipo" in raw_lower or "batch" in raw_lower or "horno" in raw_lower or "dobladora" in raw_lower or "laser" in raw_lower:
        extracted["area_impacto"] = "Maquinaria"
    elif "mantenimiento del local" in raw_lower or "epp" in raw_lower or "equipo de proteccion" in raw_lower or "escritorio" in raw_lower or "sillas" in raw_lower or "embalaje" in raw_lower:
        extracted["area_impacto"] = "Gastos Generales"
    elif "supervision" in raw_lower or "auditoria" in raw_lower or "inspeccion" in raw_lower:
        extracted["area_impacto"] = "Supervisión"
    elif "mano de obra" in raw_lower or "servicios varios" in raw_lower or "instalacion" in raw_lower:
        extracted["area_impacto"] = "Mano de Obra"
    else:
        extracted["area_impacto"] = "Materiales"

    # =========================================================================
    # 5. EXTRACCIÓN DE DESCRIPCIÓN BREVE Y OBSERVACIONES
    # =========================================================================
    # A) Si el nombre del archivo contiene descripción clara (ej. "21138 - Impresora de Etiquetas.PDF")
    if " - " in filename:
        desc_from_fn = filename.split(" - ", 1)[1]
        # Limpiar extensión y autor
        desc_clean = re.sub(r"(?i)\.pdf$", "", desc_from_fn)
        desc_clean = re.sub(r"(?i)(?:jm|jaml)$", "", desc_clean).strip()
        if len(desc_clean) > 3:
            extracted["descripcion_breve"] = desc_clean

    # B) Si no hay nombre descriptivo, extraer el concepto o primera partida
    if not extracted["descripcion_breve"]:
        # Buscar líneas de conceptos después de 'Fecha de Entrega:'
        m_item = re.search(
            r"Fecha de Entrega:\s*\d{1,2}/\d{1,2}/\d{4}\s*\n+(?:PIEZA|-)?\s*\n*(?:[A-Z0-9\-_]+)?\s*\n*(?:[A-Z0-9\-_]+)?\s*\n*([^\n\r]{6,90})",
            raw_text
        )
        if m_item:
            extracted["descripcion_breve"] = m_item.group(1).strip()
        else:
            extracted["descripcion_breve"] = "Adquisición de insumos y equipos para operación SIGRAMA"

    # C) Extraer campo 'Observaciones' (que muchas veces trae cotizaciones previas en el sistema)
    m_obs = re.search(r"Observaciones\s*\n+([\s\S]+?)(?:Solicitado por|Autorizacion Jefe|\Z)", raw_text)
    if m_obs:
        obs_text = m_obs.group(1).strip()
        if obs_text and obs_text.lower() != "solicitado por:":
            extracted["justificacion"] = obs_text
            extracted["observaciones_extraidas"] = obs_text

    # =========================================================================
    # 6. EXTRACCIÓN DE SUBTOTAL / TOTAL ESTIMADO (Si aplica)
    # =========================================================================
    m_tot = re.search(r"TOTAL\s*\n+([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2}))", raw_text)
    if m_tot:
        try:
            extracted["monto_estimado"] = float(m_tot.group(1).replace(",", ""))
        except Exception:
            pass

    # Garantizar ID si el archivo era una imagen o no tenía texto
    if not extracted["id_requisicion"]:
        sec_hash = datetime.datetime.now().strftime("%d%H%M")
        extracted["id_requisicion"] = f"REQ-26{sec_hash}"
        extracted["confianza"] = "asistida"

    if not extracted["solicitante"]:
        extracted["solicitante"] = SOLICITANTES_DEFAULT[0]

    return extracted
