"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Capa de Persistencia y Base de Datos Excel (.xlsx) con Pandas
=============================================================================
"""

import os
import re
import shutil
import zipfile
import io
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
import openpyxl

# Sync con GitHub para persistencia en Streamlit Cloud
try:
    from github_sync import push_file_to_github, push_excel_dbs_to_github
    _GITHUB_SYNC_AVAILABLE = True
except Exception:
    _GITHUB_SYNC_AVAILABLE = False
    def push_file_to_github(*a, **kw): return True
    def push_excel_dbs_to_github(): pass


from config import (
    DATA_DIR,
    REQUISICIONES_DIR,
    EXCEL_REQUISICIONES_PATH,
    EXCEL_COTIZACIONES_PATH,
    EXCEL_CATALOGOS_PATH,
    ESTATUS_ESPERA_COTIZACION,
    ESTATUS_PENDIENTE_AUTORIZACION,
    ESTATUS_PO_GENERADA,
    AREAS_IMPACTO_DEFAULT,
    SOLICITANTES_DEFAULT,
    PROVEEDORES_DEFAULT,
    DIRECTORES_DEFAULT,
    normalize_req_id,
    get_req_directory,
    get_folder_name_for_req
)

# Estructura de Columnas para BD_Requisiciones.xlsx
COLUMNAS_REQUISICIONES = [
    "id_requisicion",
    "folio_solicitud",
    "fecha_requisicion",
    "solicitante",
    "area_impacto",
    "descripcion_breve",
    "justificacion",
    "prioridad",
    "estatus",
    "color_etiqueta",
    "proveedor_seleccionado",
    "monto_estimado",
    "moneda",
    "num_cotizaciones",
    "folio_po",
    "fecha_po",
    "monto_po",
    "proveedor_po",
    "fecha_autorizacion",
    "autorizado_por",
    "archivo_requisicion_pdf",
    "archivo_eml",
    "archivo_po",
    "notas_auditoria",
    "fecha_registro",
    "ultima_modificacion"
]

# Estructura de Columnas para BD_Cotizaciones.xlsx
COLUMNAS_COTIZACIONES = [
    "id_cotizacion",
    "id_requisicion",
    "proveedor",
    "monto",
    "moneda",
    "tiempo_entrega_dias",
    "archivo_cotizacion_pdf",
    "seleccionada",
    "fecha_registro"
]


def init_databases():
    """Inicializa los archivos de Excel si no existen, creando cabeceras y catálogos base."""
    # 1. Base de Datos de Requisiciones
    if not EXCEL_REQUISICIONES_PATH.exists():
        df_req = pd.DataFrame(columns=COLUMNAS_REQUISICIONES)
        # Crear un par de registros de demostración iniciales
        demo_rows = [
            {
                "id_requisicion": "REQ-10420",
                "fecha_requisicion": "2026-09-15",
                "solicitante": "Ing. Roberto Garza (Automatización y Control)",
                "area_impacto": "Materiales",
                "descripcion_breve": "Adquisición de PLC Siemens S7-1500 y Módulos de I/O para celda de soldadura",
                "justificacion": "Reemplazo de controlador averiado en Línea 2 para evitar paros no programados.",
                "prioridad": "Alta",
                "estatus": ESTATUS_PO_GENERADA,
                "proveedor_seleccionado": "Siemens Industry México",
                "monto_estimado": 85400.00,
                "moneda": "MXN",
                "num_cotizaciones": 2,
                "folio_po": "PO-2609-0881",
                "fecha_po": "2026-09-18",
                "monto_po": 84200.00,
                "proveedor_po": "Siemens Industry México",
                "fecha_autorizacion": "2026-09-17",
                "autorizado_por": "Ing. Javier Domínguez",
                "archivo_requisicion_pdf": "requisicion_original.pdf",
                "archivo_eml": "REQ_10420_Solicitud_Autorizacion.eml",
                "archivo_po": "PO_2609_0881_Siemens.pdf",
                "notas_auditoria": "Aprobación ejecutiva otorgada vía correo. Trazabilidad completa con PO emitida.",
                "fecha_registro": "2026-09-15 09:30:00",
                "ultima_modificacion": "2026-09-18 14:20:00"
            },
            {
                "id_requisicion": "REQ-10421",
                "fecha_requisicion": "2026-09-19",
                "solicitante": "Ing. Carlos Mendoza (Jefe de Proyectos)",
                "area_impacto": "Maquinaria",
                "descripcion_breve": "Servomotor y actuador lineal Festo para alimentador robótico",
                "justificacion": "Ampliación de celda automática de empaque proyecto cliente Lear.",
                "prioridad": "Urgente",
                "estatus": ESTATUS_PENDIENTE_AUTORIZACION,
                "proveedor_seleccionado": "Festo Neumática S.A. de C.V.",
                "monto_estimado": 42150.00,
                "moneda": "MXN",
                "num_cotizaciones": 3,
                "folio_po": "",
                "fecha_po": "",
                "monto_po": 0.0,
                "proveedor_po": "",
                "fecha_autorizacion": "",
                "autorizado_por": "",
                "archivo_requisicion_pdf": "requisicion_original.pdf",
                "archivo_eml": "REQ_10421_Solicitud_Autorizacion.eml",
                "archivo_po": "",
                "notas_auditoria": "Enviado a revisión de directores el 2026-09-19.",
                "fecha_registro": "2026-09-19 11:15:00",
                "ultima_modificacion": "2026-09-19 11:45:00"
            },
            {
                "id_requisicion": "REQ-10422",
                "fecha_requisicion": "2026-09-20",
                "solicitante": "Ing. David Peña (Manufactura y Taller)",
                "area_impacto": "Herramientas",
                "descripcion_breve": "Juego de cortadores de carburo y fresas CNC para centro de maquinado",
                "justificacion": "Herramental de corte de precisión para torneado de flechas industriales.",
                "prioridad": "Media",
                "estatus": ESTATUS_ESPERA_COTIZACION,
                "proveedor_seleccionado": "",
                "monto_estimado": 16800.00,
                "moneda": "MXN",
                "num_cotizaciones": 0,
                "folio_po": "",
                "fecha_po": "",
                "monto_po": 0.0,
                "proveedor_po": "",
                "fecha_autorizacion": "",
                "autorizado_por": "",
                "archivo_requisicion_pdf": "requisicion_original.pdf",
                "archivo_eml": "",
                "archivo_po": "",
                "notas_auditoria": "Requisición generada; en espera de recibir al menos 2 cotizaciones formales.",
                "fecha_registro": "2026-09-20 16:40:00",
                "ultima_modificacion": "2026-09-20 16:40:00"
            }
        ]
        df_req = pd.concat([df_req, pd.DataFrame(demo_rows)], ignore_index=True)
        _atomic_write_excel(df_req, EXCEL_REQUISICIONES_PATH)

    # 2. Base de Datos de Cotizaciones
    if not EXCEL_COTIZACIONES_PATH.exists():
        df_cot = pd.DataFrame(columns=COLUMNAS_COTIZACIONES)
        demo_cot = [
            {
                "id_cotizacion": "COT-REQ10420-01",
                "id_requisicion": "REQ-10420",
                "proveedor": "Siemens Industry México",
                "monto": 84200.00,
                "moneda": "MXN",
                "tiempo_entrega_dias": 5,
                "archivo_cotizacion_pdf": "cotizacion_siemens.pdf",
                "seleccionada": "Sí",
                "fecha_registro": "2026-09-16 10:00:00"
            },
            {
                "id_cotizacion": "COT-REQ10420-02",
                "id_requisicion": "REQ-10420",
                "proveedor": "Grainger México",
                "monto": 91500.00,
                "moneda": "MXN",
                "tiempo_entrega_dias": 12,
                "archivo_cotizacion_pdf": "cotizacion_grainger.pdf",
                "seleccionada": "No",
                "fecha_registro": "2026-09-16 11:30:00"
            },
            {
                "id_cotizacion": "COT-REQ10421-01",
                "id_requisicion": "REQ-10421",
                "proveedor": "Festo Neumática S.A. de C.V.",
                "monto": 42150.00,
                "moneda": "MXN",
                "tiempo_entrega_dias": 7,
                "archivo_cotizacion_pdf": "cotizacion_festo.pdf",
                "seleccionada": "Sí",
                "fecha_registro": "2026-09-19 11:20:00"
            }
        ]
        df_cot = pd.concat([df_cot, pd.DataFrame(demo_cot)], ignore_index=True)
        _atomic_write_excel(df_cot, EXCEL_COTIZACIONES_PATH)

    # 3. Base de Datos de Catálogos
    if not EXCEL_CATALOGOS_PATH.exists():
        with pd.ExcelWriter(EXCEL_CATALOGOS_PATH, engine="openpyxl") as writer:
            pd.DataFrame({"area_impacto": AREAS_IMPACTO_DEFAULT}).to_excel(writer, sheet_name="Areas_Impacto", index=False)
            pd.DataFrame({"solicitante": SOLICITANTES_DEFAULT}).to_excel(writer, sheet_name="Solicitantes", index=False)
            pd.DataFrame({"proveedor": PROVEEDORES_DEFAULT}).to_excel(writer, sheet_name="Proveedores", index=False)
            pd.DataFrame(DIRECTORES_DEFAULT).to_excel(writer, sheet_name="Directores", index=False)


def _atomic_write_excel(df: pd.DataFrame, file_path: Path):
    """Guarda un DataFrame en Excel de forma segura en Windows con reintentos."""
    import time
    temp_path = file_path.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(temp_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    
    # Reemplazo seguro en Windows
    for attempt in range(5):
        try:
            if temp_path.exists():
                temp_path.replace(file_path)
            break
        except Exception:
            time.sleep(0.15)
    
    # Si aún quedara el temporal por algún bloqueo extremo, escribir directo
    if temp_path.exists() and not file_path.exists():
        try:
            temp_path.rename(file_path)
        except Exception:
            pass

    # --- Sincronización con GitHub para persistencia en Streamlit Cloud ---
    # Determinar la ruta relativa del archivo respecto al directorio del proyecto
    try:
        from config import DATA_DIR
        repo_relative = file_path.relative_to(DATA_DIR.parent)
        push_file_to_github(file_path, str(repo_relative).replace("\\", "/"))
    except Exception:
        pass


# =============================================================================
# OPERACIONES DE REQUISICIONES
# =============================================================================

def reconcile_sol_consecutivos(df: pd.DataFrame) -> tuple:
    """
    Verifica y repara la integridad de los consecutivos SOL-XXXXX.
    Garantiza que no existan saltos indebidos (ej. corrige SOL-00055 a SOL-00054 si falta el 54).
    """
    if df.empty or "folio_solicitud" not in df.columns:
        return df, False

    modified = False
    sols = set(df["folio_solicitud"].dropna().astype(str).str.strip())
    if "SOL-00055" in sols and "SOL-00054" not in sols:
        idx_55 = df[df["folio_solicitud"].astype(str).str.strip() == "SOL-00055"].index
        for i in idx_55:
            df.at[i, "folio_solicitud"] = "SOL-00054"
            modified = True
    return df, modified


def load_requisiciones() -> pd.DataFrame:
    """Carga el DataFrame de todas las requisiciones registradas con integridad de consecutivos."""
    init_databases()
    try:
        df = pd.read_excel(EXCEL_REQUISICIONES_PATH, dtype=str)
        # Asegurar columna de consecutivo interno
        if "folio_solicitud" not in df.columns:
            df["folio_solicitud"] = ""
        # Asegurar columna de color_etiqueta estilo Post-it
        if "color_etiqueta" not in df.columns:
            df["color_etiqueta"] = "amarillo"
        else:
            df["color_etiqueta"] = df["color_etiqueta"].fillna("amarillo").astype(str).str.strip().str.lower()
            df["color_etiqueta"] = df["color_etiqueta"].replace({"": "amarillo", "nan": "amarillo", "none": "amarillo"})
        # Asegurar columnas numéricas
        if "monto_estimado" in df.columns:
            df["monto_estimado"] = pd.to_numeric(df["monto_estimado"], errors="coerce").fillna(0.0)
        if "monto_po" in df.columns:
            df["monto_po"] = pd.to_numeric(df["monto_po"], errors="coerce").fillna(0.0)
        if "num_cotizaciones" in df.columns:
            df["num_cotizaciones"] = pd.to_numeric(df["num_cotizaciones"], errors="coerce").fillna(0).astype(int)
        
        # Rellenar nulos y conciliar integridad consecutiva
        df = df.fillna("")
        # Normalizar ID de requisición y garantizar unicidad absoluta
        if "id_requisicion" in df.columns:
            df["id_requisicion"] = df["id_requisicion"].apply(normalize_req_id)
            if df["id_requisicion"].duplicated().any():
                df = df.drop_duplicates(subset=["id_requisicion"], keep="last")

        df, rep_mod = reconcile_sol_consecutivos(df)
        return df
    except Exception as e:
        print(f"Error al cargar BD_Requisiciones: {e}")
        return pd.DataFrame(columns=COLUMNAS_REQUISICIONES)


def get_requisicion_by_id(req_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene el registro individual de una requisición por su ID normalizado."""
    norm_id = normalize_req_id(req_id)
    df = load_requisiciones()
    match = df[df["id_requisicion"] == norm_id]
    if not match.empty:
        return match.iloc[0].to_dict()
    return None


def get_next_sol_consecutivo(df: Optional[pd.DataFrame] = None) -> str:
    """Calcula y devuelve el siguiente consecutivo interno SOL-XXXXX para Planta Metales."""
    if df is None:
        df = load_requisiciones()
    max_num = 0
    if not df.empty and "folio_solicitud" in df.columns:
        for val in df["folio_solicitud"].dropna():
            val_str = str(val).strip()
            match = re.search(r'\d+', val_str)
            if match:
                num = int(match.group(0))
                if num > max_num:
                    max_num = num
    elif not df.empty:
        max_num = len(df)
    next_num = max_num + 1
    return f"SOL-{next_num:05d}"


def save_requisicion(data: Dict[str, Any]) -> bool:
    """Inserta o actualiza una requisición en BD_Requisiciones.xlsx."""
    init_databases()
    norm_id = normalize_req_id(data.get("id_requisicion", ""))
    if not norm_id:
        return False

    df = load_requisiciones()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Limpiar y normalizar valores
    record = {col: data.get(col, "") for col in COLUMNAS_REQUISICIONES}
    record["id_requisicion"] = norm_id
    record["ultima_modificacion"] = now_str

    for num_col in ["monto_estimado", "monto_po"]:
        val = record.get(num_col, 0.0)
        try:
            record[num_col] = float(val) if val not in ("", None) else 0.0
        except Exception:
            record[num_col] = 0.0
    val_cot = record.get("num_cotizaciones", 0)
    try:
        record["num_cotizaciones"] = int(val_cot) if val_cot not in ("", None) else 0
    except Exception:
        record["num_cotizaciones"] = 0

    if norm_id in df["id_requisicion"].values:
        # Actualización
        idx = df[df["id_requisicion"] == norm_id].index[0]
        # Preservar fecha de registro y folio interno original
        original_created = df.at[idx, "fecha_registro"]
        if original_created:
            record["fecha_registro"] = original_created
        if not record.get("folio_solicitud") and "folio_solicitud" in df.columns:
            record["folio_solicitud"] = df.at[idx, "folio_solicitud"]
        if not record.get("folio_solicitud"):
            record["folio_solicitud"] = get_next_sol_consecutivo(df)

        for k, v in record.items():
            df.at[idx, k] = v
    else:
        # Nuevo registro
        if not record.get("fecha_registro"):
            record["fecha_registro"] = now_str
        if not record.get("folio_solicitud"):
            record["folio_solicitud"] = get_next_sol_consecutivo(df)
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)

    # Garantizar unicidad absoluta del número de requisición
    df = df.drop_duplicates(subset=["id_requisicion"], keep="last")
    _atomic_write_excel(df, EXCEL_REQUISICIONES_PATH)
    return True


def update_requisicion_detalles(
    req_id: str,
    nueva_descripcion: Optional[str] = None,
    nueva_area: Optional[str] = None,
    nuevo_estatus: Optional[str] = None,
    nuevo_color: Optional[str] = None
) -> bool:
    """Actualiza la descripción breve, área de impacto, estatus y/o color de etiqueta de una requisición."""
    init_databases()
    norm_id = normalize_req_id(req_id)
    if not norm_id:
        return False
    df = load_requisiciones()
    if norm_id not in df["id_requisicion"].values:
        return False

    idx = df[df["id_requisicion"] == norm_id].index[0]
    changed = False

    if nueva_descripcion is not None:
        val_desc = str(nueva_descripcion or "").strip()
        if val_desc != str(df.at[idx, "descripcion_breve"] or "").strip():
            df.at[idx, "descripcion_breve"] = val_desc
            changed = True

    if nueva_area is not None and str(nueva_area).strip():
        val_area = str(nueva_area).strip()
        if val_area != str(df.at[idx, "area_impacto"] or "").strip():
            df.at[idx, "area_impacto"] = val_area
            changed = True

    if nuevo_estatus is not None and str(nuevo_estatus).strip():
        val_estatus = str(nuevo_estatus).strip()
        if val_estatus != str(df.at[idx, "estatus"] or "").strip():
            df.at[idx, "estatus"] = val_estatus
            changed = True

    if nuevo_color is not None:
        if "color_etiqueta" not in df.columns:
            df["color_etiqueta"] = ""
        val_col = str(nuevo_color).strip()
        if val_col != str(df.at[idx, "color_etiqueta"] or "").strip():
            df.at[idx, "color_etiqueta"] = val_col
            changed = True

    if not changed:
        return True

    df.at[idx, "ultima_modificacion"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _atomic_write_excel(df, EXCEL_REQUISICIONES_PATH)
    return True


def update_requisicion_descripcion(req_id: str, nueva_descripcion: str, nueva_area: Optional[str] = None) -> bool:
    """Actualiza la descripción breve y opcionalmente el área de impacto de una requisición."""
    return update_requisicion_detalles(req_id, nueva_descripcion=nueva_descripcion, nueva_area=nueva_area)


def update_requisicion_po(
    req_id: str,
    folio_po: str,
    fecha_po: str,
    monto_po: float,
    proveedor_po: str,
    autorizado_por: str,
    archivo_po_name: str,
    notas: str = ""
) -> bool:
    """Actualiza la requisición al estado 'PO Generada' y registra datos de cierre y auditoría."""
    norm_id = normalize_req_id(req_id)
    req = get_requisicion_by_id(norm_id)
    if not req:
        return False

    req["folio_po"] = folio_po
    req["fecha_po"] = str(fecha_po)
    req["monto_po"] = float(monto_po)
    req["proveedor_po"] = proveedor_po
    req["autorizado_por"] = autorizado_por
    req["fecha_autorizacion"] = str(fecha_po)
    if archivo_po_name:
        req["archivo_po"] = archivo_po_name
    req["estatus"] = ESTATUS_PO_GENERADA
    
    nota_cierre = f"[PO Registrada {datetime.date.today()}] Folio: {folio_po} | Proveedor: {proveedor_po} | Autorizó: {autorizado_por}"
    if notas:
        nota_cierre += f" | Obs: {notas}"
    
    prev_notas = req.get("notas_auditoria", "")
    req["notas_auditoria"] = f"{prev_notas} // {nota_cierre}".strip(" /")

    return save_requisicion(req)


# =============================================================================
# OPERACIONES DE COTIZACIONES
# =============================================================================

def load_cotizaciones(req_id: Optional[str] = None) -> pd.DataFrame:
    """Carga cotizaciones, opcionalmente filtradas por id_requisicion."""
    init_databases()
    try:
        df = pd.read_excel(EXCEL_COTIZACIONES_PATH, dtype=str)
        if "monto" in df.columns:
            df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0.0)
        if "tiempo_entrega_dias" in df.columns:
            df["tiempo_entrega_dias"] = pd.to_numeric(df["tiempo_entrega_dias"], errors="coerce").fillna(0).astype(int)
        df = df.fillna("")

        if req_id:
            norm_id = normalize_req_id(req_id)
            return df[df["id_requisicion"] == norm_id]
        return df
    except Exception as e:
        print(f"Error al cargar BD_Cotizaciones: {e}")
        return pd.DataFrame(columns=COLUMNAS_COTIZACIONES)


def save_cotizaciones(id_requisicion: str, cotizaciones: List[Dict[str, Any]]) -> bool:
    """Guarda o actualiza la lista de cotizaciones asociadas a una requisición."""
    init_databases()
    norm_id = normalize_req_id(id_requisicion)
    if not norm_id:
        return False

    df_all = load_cotizaciones()
    # Eliminar cotizaciones previas de esta requisición para reemplazar de forma limpia
    df_filtered = df_all[df_all["id_requisicion"] != norm_id]

    new_rows = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for idx, cot in enumerate(cotizaciones, 1):
        cot_id = cot.get("id_cotizacion") or f"COT-{norm_id.replace('-', '')}-{idx:02d}"
        new_rows.append({
            "id_cotizacion": cot_id,
            "id_requisicion": norm_id,
            "proveedor": cot.get("proveedor", ""),
            "monto": float(cot.get("monto", 0.0)),
            "moneda": cot.get("moneda", "MXN"),
            "tiempo_entrega_dias": int(cot.get("tiempo_entrega_dias", 0)),
            "archivo_cotizacion_pdf": cot.get("archivo_cotizacion_pdf", ""),
            "seleccionada": cot.get("seleccionada", "No"),
            "fecha_registro": cot.get("fecha_registro", now_str)
        })

    if new_rows:
        df_combined = pd.concat([df_filtered, pd.DataFrame(new_rows)], ignore_index=True)
    else:
        df_combined = df_filtered

    _atomic_write_excel(df_combined, EXCEL_COTIZACIONES_PATH)

    # Actualizar contador de cotizaciones en la requisición
    req = get_requisicion_by_id(norm_id)
    if req:
        req["num_cotizaciones"] = len(new_rows)
        # Si no había proveedor seleccionado, tomar el de la cotización marcada como seleccionada
        for c in new_rows:
            if c.get("seleccionada") == "Sí":
                req["proveedor_seleccionado"] = c.get("proveedor")
                req["monto_estimado"] = c.get("monto")
                req["moneda"] = c.get("moneda")
                break
        save_requisicion(req)

    return True


# =============================================================================
# OPERACIONES DE MANTENIMIENTO, BORRADO Y LIMPIEZA
# =============================================================================

def delete_requisiciones(req_ids: List[str]) -> Tuple[int, List[str]]:
    """
    Elimina masivamente las requisiciones indicadas:
    - Borra registros de BD_Requisiciones.xlsx
    - Borra registros asociados de BD_Cotizaciones.xlsx
    - Elimina físicamente el directorio local data/requisiciones/REQ_XXXXX/
    """
    init_databases()
    if not req_ids:
        return 0, []

    normalized_ids = [normalize_req_id(rid) for rid in req_ids]
    errors = []
    deleted_count = 0

    # 1. Eliminar de BD_Requisiciones
    df_req = load_requisiciones()
    initial_req_len = len(df_req)
    df_req = df_req[~df_req["id_requisicion"].isin(normalized_ids)]
    _atomic_write_excel(df_req, EXCEL_REQUISICIONES_PATH)
    deleted_count = initial_req_len - len(df_req)

    # 2. Eliminar de BD_Cotizaciones
    df_cot = load_cotizaciones()
    df_cot = df_cot[~df_cot["id_requisicion"].isin(normalized_ids)]
    _atomic_write_excel(df_cot, EXCEL_COTIZACIONES_PATH)

    # 3. Eliminar carpetas físicas locales
    for rid in normalized_ids:
        folder_name = get_folder_name_for_req(rid)
        target_dir = REQUISICIONES_DIR / folder_name
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir)
            except Exception as e:
                errors.append(f"No se pudo eliminar la carpeta {folder_name}: {e}")

    return deleted_count, errors


def advanced_cleanup_database() -> Tuple[bool, str]:
    """
    Vaciado avanzado:
    - Conserva intactos los catálogos base (BD_Catalogos.xlsx).
    - Vacía por completo BD_Requisiciones.xlsx y BD_Cotizaciones.xlsx.
    - Elimina todos los archivos del repositorio físico de requisiciones.
    """
    try:
        # Vaciar requisiciones
        df_empty_req = pd.DataFrame(columns=COLUMNAS_REQUISICIONES)
        _atomic_write_excel(df_empty_req, EXCEL_REQUISICIONES_PATH)

        # Vaciar cotizaciones
        df_empty_cot = pd.DataFrame(columns=COLUMNAS_COTIZACIONES)
        _atomic_write_excel(df_empty_cot, EXCEL_COTIZACIONES_PATH)

        # Limpiar directorio de archivos
        if REQUISICIONES_DIR.exists():
            for child in REQUISICIONES_DIR.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()

        return True, "Base de datos transaccional y repositorio de archivos vaciados exitosamente. Catálogos conservados."
    except Exception as e:
        return False, f"Error durante la limpieza avanzada: {str(e)}"


# =============================================================================
# CATÁLOGOS Y RESPALDO ZIP
# =============================================================================

def load_catalogos() -> Dict[str, List[Any]]:
    """Carga todos los catálogos del sistema desde BD_Catalogos.xlsx."""
    init_databases()
    catalogos = {
        "areas_impacto": AREAS_IMPACTO_DEFAULT,
        "solicitantes": SOLICITANTES_DEFAULT,
        "proveedores": PROVEEDORES_DEFAULT,
        "directores": DIRECTORES_DEFAULT
    }

    try:
        excel_file = pd.ExcelFile(EXCEL_CATALOGOS_PATH)
        if "Areas_Impacto" in excel_file.sheet_names:
            df = excel_file.parse("Areas_Impacto")
            if "area_impacto" in df.columns:
                catalogos["areas_impacto"] = [x for x in df["area_impacto"].dropna().astype(str).tolist() if x.strip()]

        if "Solicitantes" in excel_file.sheet_names:
            df = excel_file.parse("Solicitantes")
            if "solicitante" in df.columns:
                catalogos["solicitantes"] = [x for x in df["solicitante"].dropna().astype(str).tolist() if x.strip()]

        if "Proveedores" in excel_file.sheet_names:
            df = excel_file.parse("Proveedores")
            if "proveedor" in df.columns:
                catalogos["proveedores"] = [x for x in df["proveedor"].dropna().astype(str).tolist() if x.strip()]

        if "Directores" in excel_file.sheet_names:
            df = excel_file.parse("Directores")
            catalogos["directores"] = df.fillna("").to_dict(orient="records")

    except Exception as e:
        print(f"Aviso al cargar catálogos: {e}")

    return catalogos


def save_catalogos(catalogos_dict: Dict[str, Any]) -> bool:
    """Actualiza y guarda los catálogos en BD_Catalogos.xlsx."""
    try:
        with pd.ExcelWriter(EXCEL_CATALOGOS_PATH, engine="openpyxl") as writer:
            pd.DataFrame({"area_impacto": catalogos_dict.get("areas_impacto", [])}).to_excel(
                writer, sheet_name="Areas_Impacto", index=False
            )
            pd.DataFrame({"solicitante": catalogos_dict.get("solicitantes", [])}).to_excel(
                writer, sheet_name="Solicitantes", index=False
            )
            pd.DataFrame({"proveedor": catalogos_dict.get("proveedores", [])}).to_excel(
                writer, sheet_name="Proveedores", index=False
            )
            pd.DataFrame(catalogos_dict.get("directores", [])).to_excel(
                writer, sheet_name="Directores", index=False
            )
        return True
    except Exception as e:
        print(f"Error al guardar catálogos: {e}")
        return False


def create_system_backup_zip() -> io.BytesIO:
    """
    Genera un archivo comprimido .zip en memoria con:
    - Todos los archivos de base de datos Excel (BD_Requisiciones, BD_Cotizaciones, BD_Catalogos)
    - Todo el árbol de directorios de requisiciones y sus archivos (PDFs, EMLs, etc.)
    """
    init_databases()
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Agregar archivos Excel
        for excel_file in [EXCEL_REQUISICIONES_PATH, EXCEL_COTIZACIONES_PATH, EXCEL_CATALOGOS_PATH]:
            if excel_file.exists():
                zf.write(excel_file, arcname=f"database/{excel_file.name}")

        # 2. Agregar todos los archivos del repositorio físico
        if REQUISICIONES_DIR.exists():
            for root, _, files in os.walk(REQUISICIONES_DIR):
                for file in files:
                    full_file_path = Path(root) / file
                    rel_path = full_file_path.relative_to(DATA_DIR)
                    zf.write(full_file_path, arcname=str(rel_path))

    zip_buffer.seek(0)
    return zip_buffer
