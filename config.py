"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo de Configuración Central y Catálogos Institucionales
=============================================================================
"""

import os
from pathlib import Path

# Directorios del Sistema
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REQUISICIONES_DIR = DATA_DIR / "requisiciones"
BRAND_DIR = BASE_DIR / "brand"

# Asegurar existencia de directorios base
DATA_DIR.mkdir(parents=True, exist_ok=True)
REQUISICIONES_DIR.mkdir(parents=True, exist_ok=True)
BRAND_DIR.mkdir(parents=True, exist_ok=True)

# Rutas a Archivos de Base de Datos Excel
EXCEL_REQUISICIONES_PATH = DATA_DIR / "BD_Requisiciones.xlsx"
EXCEL_COTIZACIONES_PATH = DATA_DIR / "BD_Cotizaciones.xlsx"
EXCEL_CATALOGOS_PATH = DATA_DIR / "BD_Catalogos.xlsx"

# Archivos de Imagen Institucional
LOGO_SIGRAMA_PATH = BRAND_DIR / "logo_sigrama.png"
FAVICON_PATH = BRAND_DIR / "favicon.png"

# Identidad Visual y Paleta Corporativa SIGRAMA
COLOR_PRIMARY = "#EC2024"      # Rojo Corporativo SIGRAMA
COLOR_SECONDARY = "#0F172A"    # Azul Pizarra Oscuro Ejecutivo
COLOR_BACKGROUND = "#F8FAFC"    # Slate Claro Industrial
COLOR_CARD_BG = "#FFFFFF"       # Blanco Puro
COLOR_BORDER = "#E2E8F0"        # Borde sutil
COLOR_TEXT_MAIN = "#1E293B"     # Texto principal grafito
COLOR_TEXT_MUTED = "#64748B"    # Texto secundario pizarra

# Estatus Oficiales del Flujo de Requisiciones
ESTATUS_ESPERA_COTIZACION = "En Espera de Cotización"
ESTATUS_PENDIENTE_AUTORIZACION = "Pendiente de Autorización"
ESTATUS_PO_GENERADA = "PO Generada"
ESTATUS_ARCHIVADO = "Archivado Histórico"

TODOS_ESTATUS = [
    ESTATUS_ESPERA_COTIZACION,
    ESTATUS_PENDIENTE_AUTORIZACION,
    ESTATUS_PO_GENERADA,
    ESTATUS_ARCHIVADO
]

# Configuración de Colores y Badges por Estatus
STATUS_CONFIG = {
    ESTATUS_ESPERA_COTIZACION: {
        "color": "#D97706",         # Ámbar oscuro
        "bg_color": "#FEF3C7",      # Ámbar muy suave
        "border_color": "#FDE68A",
        "icon": "⏳",
        "badge_class": "badge-amber"
    },
    ESTATUS_PENDIENTE_AUTORIZACION: {
        "color": "#1D4ED8",         # Azul ejecutivo
        "bg_color": "#DBEAFE",      # Azul suave
        "border_color": "#BFDBFE",
        "icon": "📋",
        "badge_class": "badge-blue"
    },
    ESTATUS_PO_GENERADA: {
        "color": "#047857",         # Verde esmeralda
        "bg_color": "#D1FAE5",      # Verde suave
        "border_color": "#A7F3D0",
        "icon": "✅",
        "badge_class": "badge-green"
    },
    ESTATUS_ARCHIVADO: {
        "color": "#475569",         # Pizarra neutro
        "bg_color": "#F1F5F9",      # Gris suave
        "border_color": "#E2E8F0",
        "icon": "📁",
        "badge_class": "badge-gray"
    }
}

# Catálogos Estándar de la Industria e Industria SIGRAMA S.A. de C.V.
AREAS_IMPACTO_DEFAULT = [
    "Materiales",
    "Mano de Obra",
    "Supervisión",
    "Gastos Generales",
    "Herramientas",
    "Maquinaria"
]

SOLICITANTES_DEFAULT = [
    "Ing. Jesús Alberto Morales (Dirección / Sistemas SIGRAMA)",
    "Luis Alfredo Quintana Palma (Operaciones / Maquinado SIGRAMA)",
    "Ing. Carlos Mendoza (Jefe de Proyectos)",
    "Ing. Roberto Garza (Automatización y Control)",
    "Ing. Alejandro Morales (Mantenimiento e Instalaciones)",
    "Lic. Sofía Villalobos (Adquisiciones y Logística)",
    "Ing. David Peña (Manufactura y Taller)",
    "Ing. Fernando Soto (Diseño Eléctrico)"
]

PROVEEDORES_DEFAULT = [
    "Siemens Industry México",
    "Rockwell Automation / Allen-Bradley",
    "Festo Neumática S.A. de C.V.",
    "Schneider Electric México",
    "ABB México S.A. de C.V.",
    "Grainger México",
    "Aceros y Perfiles Monterrey",
    "Suministros Industriales del Norte",
    "Phoenix Contact México",
    "SMC Corporation México"
]

# Destinatarios Oficiales de Solicitud de Autorización
DESTINATARIO_PRINCIPAL_DEFAULT = {
    "nombre": "Lorena Hernandez Cuellar",
    "correo": "lhernandez@sigrama.com.mx",
    "puesto": "Dirección / Autorización de Compras"
}

DESTINATARIOS_CC_DEFAULT = [
    {"nombre": "Bryan Alejandro Flores Mancinas", "correo": "bryan.mancinas@sigrama.com.mx", "puesto": "Compras / Proyectos"},
    {"nombre": "Cruz Eduardo Carreon Rios", "correo": "cruz.carreon@sigrama.com.mx", "puesto": "Operaciones"},
    {"nombre": "Jose Fernandez", "correo": "jose.fernandez@sigrama.com.mx", "puesto": "Dirección"},
    {"nombre": "Luis Alfredo Quintana Palma", "correo": "luis.quintana@sigrama.com.mx", "puesto": "Maquinado / Operaciones"},
    {"nombre": "Jesus Alberto Morales Lopez", "correo": "jesus.morales@sigrama.com.mx", "puesto": "Sistemas / Dirección"}
]

DIRECTORES_DEFAULT = [
    {"nombre": "Lorena Hernandez Cuellar", "puesto": "Dirección / Autorización", "correo": "lhernandez@sigrama.com.mx"},
    {"nombre": "Bryan Alejandro Flores Mancinas", "puesto": "Compras / Proyectos", "correo": "bryan.mancinas@sigrama.com.mx"},
    {"nombre": "Cruz Eduardo Carreon Rios", "puesto": "Operaciones", "correo": "cruz.carreon@sigrama.com.mx"},
    {"nombre": "Jose Fernandez", "puesto": "Dirección", "correo": "jose.fernandez@sigrama.com.mx"},
    {"nombre": "Luis Alfredo Quintana Palma", "puesto": "Maquinado / Operaciones", "correo": "luis.quintana@sigrama.com.mx"},
    {"nombre": "Jesus Alberto Morales Lopez", "puesto": "Sistemas / Dirección", "correo": "jesus.morales@sigrama.com.mx"}
]

MONEDAS_DEFAULT = ["MXN", "USD", "EUR"]
PRIORIDADES_DEFAULT = ["Baja", "Media", "Alta", "Urgente"]

# Clave de acceso para sección de mantenimiento (por defecto para entorno local)
ADMIN_PIN_DEFAULT = "sigrama2026"

def normalize_req_id(req_id: str) -> str:
    """Normaliza un ID de requisición a un formato estándar 'REQ-XXXXX'."""
    if not req_id:
        return "REQ-00000"
    s = str(req_id).strip().upper()
    # Si viene como REQ XXXXX o REQ-XXXXX o XXXXX
    s = s.replace("_", "-").replace(" ", "-")
    if not s.startswith("REQ"):
        s = f"REQ-{s}"
    # Normalizar guiones duplicados
    while "--" in s:
        s = s.replace("--", "-")
    return s

def get_folder_name_for_req(req_id: str) -> str:
    """Genera un nombre de carpeta seguro y estándar, p. ej. 'REQ_10420'."""
    norm = normalize_req_id(req_id)
    return norm.replace("-", "_")

def get_req_directory(req_id: str) -> Path:
    """Retorna y asegura la carpeta física para almacenar archivos de la requisición."""
    folder_name = get_folder_name_for_req(req_id)
    target_dir = REQUISICIONES_DIR / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir
