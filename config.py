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
ESTATUS_AUTORIZADA = "Autorizada"
ESTATUS_PO_GENERADA = "PO Generada"
ESTATUS_TERMINADA = "Terminada"
ESTATUS_ARCHIVADA = "Archivada"
ESTATUS_CONGELADA = "Congelada"

# Compatibilidad con nombres anteriores
ESTATUS_ARCHIVADO = ESTATUS_ARCHIVADA

TODOS_ESTATUS = [
    ESTATUS_ESPERA_COTIZACION,
    ESTATUS_PENDIENTE_AUTORIZACION,
    ESTATUS_AUTORIZADA,
    ESTATUS_PO_GENERADA,
    ESTATUS_TERMINADA,
    ESTATUS_ARCHIVADA,
    ESTATUS_CONGELADA
]

# Configuración de Colores, Badges y Semáforos por Estatus
STATUS_CONFIG = {
    ESTATUS_ESPERA_COTIZACION: {
        "color": "#D97706",         # Ámbar oscuro
        "bg_color": "#FEF3C7",      # Ámbar muy suave
        "border_color": "#FDE68A",
        "icon": "⏳",
        "badge_class": "badge-amber"
    },
    ESTATUS_PENDIENTE_AUTORIZACION: {
        "color": "#EA580C",         # Naranja / Alerta
        "bg_color": "#FFEDD5",      # Naranja suave
        "border_color": "#FED7AA",
        "icon": "📋",
        "badge_class": "badge-orange"
    },
    ESTATUS_AUTORIZADA: {
        "color": "#0284C7",         # Azul cielo / Aprobado
        "bg_color": "#E0F2FE",      # Azul muy suave
        "border_color": "#BAE6FD",
        "icon": "👍",
        "badge_class": "badge-blue"
    },
    ESTATUS_PO_GENERADA: {
        "color": "#16A34A",         # Verde institucional
        "bg_color": "#DCFCE7",      # Verde suave
        "border_color": "#BBF7D0",
        "icon": "📝",
        "badge_class": "badge-green"
    },
    ESTATUS_TERMINADA: {
        "color": "#059669",         # Esmeralda éxito
        "bg_color": "#D1FAE5",      # Esmeralda suave
        "border_color": "#A7F3D0",
        "icon": "✅",
        "badge_class": "badge-emerald"
    },
    ESTATUS_ARCHIVADA: {
        "color": "#64748B",         # Pizarra neutro
        "bg_color": "#F1F5F9",      # Gris suave
        "border_color": "#E2E8F0",
        "icon": "📁",
        "badge_class": "badge-gray"
    },
    ESTATUS_CONGELADA: {
        "color": "#2563EB",         # Azul hielo / frío
        "bg_color": "#EFF6FF",      # Azul frío suave
        "border_color": "#BFDBFE",
        "icon": "🧊",
        "badge_class": "badge-ice"
    }
}
# Alias para compatibilidad
STATUS_CONFIG["Archivado Histórico"] = STATUS_CONFIG[ESTATUS_ARCHIVADA]

# Catálogos Estándar de la Industria e Industria SIGRAMA S.A. de C.V.
AREAS_IMPACTO_DEFAULT = [
    "Materiales",
    "Producción",
    "Laser",
    "Lijado",
    "Doblez",
    "Pintura",
    "Embarque",
    "Calidad",
    "Inspección",
    "Herramientas",
    "Maquinaria",
    "Mano de Obra",
    "Supervisión",
    "Gastos Generales",
    "Refacciones"
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
    "nombre": "Ing. Lorena Hernandez",
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
    {"nombre": "Ing. Lorena Hernandez", "puesto": "Dirección / Autorización", "correo": "lhernandez@sigrama.com.mx"},
    {"nombre": "Bryan Alejandro Flores Mancinas", "puesto": "Compras / Proyectos", "correo": "bryan.mancinas@sigrama.com.mx"},
    {"nombre": "Cruz Eduardo Carreon Rios", "puesto": "Operaciones", "correo": "cruz.carreon@sigrama.com.mx"},
    {"nombre": "Jose Fernandez", "puesto": "Dirección", "correo": "jose.fernandez@sigrama.com.mx"},
    {"nombre": "Luis Alfredo Quintana Palma", "puesto": "Maquinado / Operaciones", "correo": "luis.quintana@sigrama.com.mx"},
    {"nombre": "Jesus Alberto Morales Lopez", "puesto": "Sistemas / Dirección", "correo": "jesus.morales@sigrama.com.mx"}
]

MONEDAS_DEFAULT = ["MXN", "USD", "EUR"]
PRIORIDADES_DEFAULT = ["Baja", "Media", "Alta", "Urgente"]

# Paleta de Colores Post-it Oficial para Tarjetas Kanban
PALETA_COLORES_ODOO = [
    {"id": "blanco", "nombre": "⚪ Blanco", "color": "#64748B", "bg": "#FFFFFF", "border": "#E2E8F0", "top": "#CBD5E1"},
    {"id": "amarillo", "nombre": "🟡 Amarillo Post-it", "color": "#CA8A04", "bg": "#FEF08A", "border": "#FDE047", "top": "#EAB308"},
    {"id": "verde", "nombre": "🟢 Verde Post-it", "color": "#16A34A", "bg": "#BBF7D0", "border": "#86EFAC", "top": "#22C55E"},
    {"id": "azul", "nombre": "🔵 Azul Post-it", "color": "#0284C7", "bg": "#BAE6FD", "border": "#7DD3FC", "top": "#0284C7"},
    {"id": "rosa", "nombre": "🌸 Rosa Post-it", "color": "#DB2777", "bg": "#FBCFE8", "border": "#F9A8D4", "top": "#DB2777"},
    {"id": "naranja", "nombre": "🟠 Naranja Post-it", "color": "#EA580C", "bg": "#FED7AA", "border": "#FDBA74", "top": "#EA580C"},
    {"id": "morado", "nombre": "🟣 Morado Post-it", "color": "#7C3AED", "bg": "#DDD6FE", "border": "#C4B5FD", "top": "#7C3AED"},
    {"id": "turquesa", "nombre": "🩵 Turquesa Post-it", "color": "#0891B2", "bg": "#A5F3FC", "border": "#67E8F9", "top": "#0891B2"},
    {"id": "rojo", "nombre": "🔴 Rojo Post-it", "color": "#DC2626", "bg": "#FECACA", "border": "#FCA5A5", "top": "#DC2626"},
]

# Clave de acceso para sección de mantenimiento (por defecto para entorno local)
ADMIN_PIN_DEFAULT = "SigramaAdmin2026"
ADMIN_PASSWORDS = ["SigramaAdmin2026", "SigramaMetales2026", "Admin2026", "sigrama2026", "admin", "sigrama"]

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
