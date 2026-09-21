"""
=============================================================================
SISTEMA DE CONTROL Y SEGUIMIENTO DE REQUISICIONES DE COMPRA
INDUSTRIA SIGRAMA S.A. DE C.V. - MÉXICO
=============================================================================
Manual de Identidad Corporativa: PANTONE 485 C (#EC2024) y Black 7 C (#111111)
Tipografías: Montserrat & Questrial
=============================================================================
"""

import os
import base64
from pathlib import Path
from PIL import Image

import streamlit as st

from config import (
    BASE_DIR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_BACKGROUND,
    LOGO_SIGRAMA_PATH,
    FAVICON_PATH
)
from database import init_databases
from modules.requisition_wizard import render_requisition_wizard
from modules.po_control import render_po_control
from modules.dashboard import render_dashboard
from modules.admin_backup import render_admin_backup

# =============================================================================
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# =============================================================================
fav_icon_obj = Image.open(FAVICON_PATH) if FAVICON_PATH.exists() else "📋"

st.set_page_config(
    page_title="Industria SIGRAMA - Control de Requisiciones",
    page_icon=fav_icon_obj,
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# SOPORTE SSO & EMBED DESDE LA CONCENTRADORA (APP HUB)
# =============================================================================
is_embedded = False
sso_user = None
sso_role = "Usuario"

try:
    qp = dict(st.query_params) if hasattr(st, "query_params") else {}
    embed_param = qp.get("embed")
    if isinstance(embed_param, list): embed_param = embed_param[0] if embed_param else None
    if str(embed_param).lower() in ("true", "1"):
        is_embedded = True

    sso_token = qp.get("sso_token")
    if isinstance(sso_token, list): sso_token = sso_token[0] if sso_token else None
    user_param = qp.get("sso_user")
    if isinstance(user_param, list): user_param = user_param[0] if user_param else None
    role_param = qp.get("sso_role", "Usuario")
    if isinstance(role_param, list): role_param = role_param[0] if role_param else "Usuario"

    if sso_token == "SIGRAMA_AUTH_TOKEN" and user_param:
        sso_user = user_param
        sso_role = role_param
        st.session_state["sso_user"] = sso_user
        st.session_state["sso_role"] = sso_role
        st.session_state["usuario_actual"] = sso_user
    elif "sso_user" in st.session_state:
        sso_user = st.session_state["sso_user"]
        sso_role = st.session_state.get("sso_role", "Usuario")
except Exception:
    pass

# Inyección forzada de Favicon Oficial SIGRAMA en navegador
if FAVICON_PATH.exists():
    with open(FAVICON_PATH, "rb") as f:
        fav_b64 = base64.b64encode(f.read()).decode("utf-8")
    st.markdown(f"""
    <head>
        <link rel="icon" type="image/png" href="data:image/png;base64,{fav_b64}">
        <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{fav_b64}">
        <link rel="apple-touch-icon" href="data:image/png;base64,{fav_b64}">
    </head>
    """, unsafe_allow_html=True)

# Inyección de CSS Oficial SIGRAMA (PANTONE 485 C & PANTONE Black 7 C)
embed_css = """
    /* Modo incrustado en Concentradora SIGRAMA */
    header[data-testid="stHeader"], footer, div[data-testid="stDecoration"] {
        display: none !important;
    }
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
    }
""" if is_embedded else ""

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Questrial&display=swap');
    {embed_css}


    /* Tipografías Oficiales */
    html, body, [class*="css"], .stApp {
        font-family: 'Questrial', 'Montserrat', -apple-system, sans-serif !important;
        background-color: #F8FAFC !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        color: #111111 !important;
    }

    /* Barra Lateral Oficial SIGRAMA - Negro Profundo #111111 */
    [data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #1E293B !important;
    }
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
        color: #FFFFFF !important;
        font-family: 'Questrial', sans-serif !important;
    }

    /* Radio de navegación en sidebar estilizado con acento Rojo SIGRAMA */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        background-color: #18181B !important;
        border: 1px solid #27272A !important;
        border-radius: 8px !important;
        padding: 6px !important;
        gap: 4px !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        color: #E2E8F0 !important;
        padding: 10px 14px !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
        margin: 0 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label p,
    [data-testid="stSidebar"] div[role="radiogroup"] label span {
        font-size: 14px !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: rgba(236, 32, 36, 0.2) !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
        background-color: #EC2024 !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(236, 32, 36, 0.4) !important;
    }

    /* Botón Primario Corporativo SIGRAMA (#EC2024) */
    button[kind="primary"], div.stButton > button[kind="primary"] {
        background-color: #EC2024 !important;
        border: 1px solid #EC2024 !important;
        color: #FFFFFF !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        box-shadow: 0 2px 6px rgba(236, 32, 36, 0.3) !important;
        transition: all 0.2s ease !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-size: 13px !important;
    }
    button[kind="primary"]:hover, div.stButton > button[kind="primary"]:hover {
        background-color: #D61B1F !important;
        border-color: #D61B1F !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 10px rgba(236, 32, 36, 0.4) !important;
    }

    /* Botones Secundarios */
    button[kind="secondary"], div.stButton > button[kind="secondary"] {
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-family: 'Montserrat', sans-serif !important;
    }

    /* Tarjetas de Métricas */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #EC2024;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 11px !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        color: #64748B !important;
        font-family: 'Montserrat', sans-serif !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 22px !important;
        font-weight: 900 !important;
        color: #111111 !important;
        font-family: 'Montserrat', sans-serif !important;
    }

    /* File uploader limpio sin duplicaciones */
    section[data-testid="stFileUploaderDropzone"] {
        border: 2px dashed #CBD5E1 !important;
        border-radius: 8px !important;
        background-color: #FFFFFF !important;
        padding: 18px !important;
    }
    section[data-testid="stFileUploaderDropzone"]:hover {
        border-color: #EC2024 !important;
        background-color: #FFFDFD !important;
    }

    /* Badges de estatus */
    .badge-amber { background-color: #FEF3C7; color: #D97706; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; }
    .badge-blue { background-color: #DBEAFE; color: #1D4ED8; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; }
    .badge-green { background-color: #D1FAE5; color: #047857; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; }
    .badge-gray { background-color: #F1F5F9; color: #475569; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; }
</style>
""", unsafe_allow_html=True)


def main():
    """Función de arranque y enrutamiento modular del sistema."""
    init_databases()

    # =========================================================================
    # SIDEBAR: IDENTIDAD CORPORATIVA SIGRAMA
    # =========================================================================
    with st.sidebar:
        # Preferir logotipo negativo oficial para fondo negro
        logo_neg = BASE_DIR / "brand" / "logo_sigrama_negative.png"
        if logo_neg.exists():
            st.image(str(logo_neg), use_container_width=True)
        elif LOGO_SIGRAMA_PATH.exists():
            st.image(str(LOGO_SIGRAMA_PATH), use_container_width=True)
        else:
            st.markdown("""
            <div style="text-align:center; padding:10px 0;">
                <div style="font-size:24px; font-weight:900; color:#FFFFFF; letter-spacing:1.5px;">SIGRAMA</div>
                <div style="font-size:11px; color:#EC2024; font-weight:800; letter-spacing:1px;">INDUSTRIA SIGRAMA</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="text-align:center; margin-bottom:16px;">
            <div style="font-size:11px; color:#94A3B8; text-transform:uppercase; letter-spacing:1px; font-weight:700; font-family:'Montserrat', sans-serif;">
                Control de Requisiciones
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr style='border-color:#27272A;'>", unsafe_allow_html=True)

        if sso_user:
            st.markdown(f"""
            <div style="background-color:#18181B; border:1px solid #3F3F46; border-radius:6px; padding:10px 12px; margin-bottom:12px;">
                <div style="color:#A1A1AA; font-size:10px; text-transform:uppercase; letter-spacing:0.5px; font-weight:700;">👤 Sesión Hub Conectada</div>
                <div style="color:#FFFFFF; font-weight:bold; font-size:13px; margin-top:2px;">{sso_user}</div>
                <div style="color:#EC2024; font-weight:700; font-size:11px; margin-top:1px;">Rol: {sso_role}</div>
            </div>
            """, unsafe_allow_html=True)

        # Menú de Navegación por Fases
        menu_options = [
            "📝 Registro y Cotizaciones (Fase 1)",
            "📑 Control de Orden de Compra (PO)",
            "📊 Panel de Control (Dashboard)",
            "🔒 Mantenimiento y Respaldos"
        ]

        if "selected_nav" not in st.session_state:
            st.session_state["selected_nav"] = menu_options[2]  # Mostrar por defecto el Dashboard con las 53 requisiciones

        selected_menu = st.radio(
            "Flujo de Operación:",
            options=menu_options,
            index=menu_options.index(st.session_state["selected_nav"]) if st.session_state["selected_nav"] in menu_options else 2,
            label_visibility="collapsed"
        )
        st.session_state["selected_nav"] = selected_menu

        st.markdown("<hr style='border-color:#27272A;'>", unsafe_allow_html=True)

        # Indicador de Auditoría y Cumplimiento
        st.markdown("""
        <div style="background-color:#18181B; border:1px solid #27272A; border-radius:6px; padding:12px; font-size:11px; color:#94A3B8;">
            <div style="font-weight:bold; color:#F8FAFC; margin-bottom:4px; font-family:'Montserrat', sans-serif;">🛡️ Cumplimiento SIGRAMA</div>
            <div>&bull; Trazabilidad: 1 REQ &rarr; N Cot &rarr; EML &rarr; PO</div>
            <div>&bull; Persistencia: Excel (.xlsx)</div>
            <div>&bull; Repositorio: data/requisiciones/</div>
            <div>&bull; Cliente: <strong>Industria SIGRAMA</strong></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:20px; text-align:center; font-size:10px; color:#64748B;">
            v2.6.0 &bull; Industria Sigrama S.A. de C.V.<br>
            Planta Metalmecánica &bull; México
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # ENCABEZADO SUPERIOR CORPORATIVO EN EL ÁREA PRINCIPAL
    # =========================================================================
    user_header_badge = ""
    if sso_user:
        user_header_badge = f"""
            <span style="background-color:#F1F5F9; color:#0F172A; border:1px solid #CBD5E1; padding:5px 12px; border-radius:6px; font-size:11px; font-weight:700; font-family:'Montserrat', sans-serif; margin-right:8px;">
                👤 {sso_user}
            </span>
        """

    st.markdown(f"""
    <div style="background-color:#FFFFFF; border-bottom:3px solid #EC2024; border-radius:8px; padding:14px 22px; margin-bottom:18px; box-shadow:0 2px 6px rgba(0,0,0,0.03); display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div style="font-size:19px; font-weight:900; color:#111111; letter-spacing:0.5px; font-family:'Montserrat', sans-serif;">
                INDUSTRIA SIGRAMA S.A. DE C.V.
            </div>
            <div style="font-size:12px; color:#64748B; font-weight:600; text-transform:uppercase; letter-spacing:1px; margin-top:2px;">
                Módulo Central de Control y Seguimiento de Requisiciones de Compra
            </div>
        </div>
        <div style="display:flex; align-items:center;">
            {user_header_badge}
            <span style="background-color:#FEF2F2; color:#DC2626; border:1px solid #FECACA; padding:5px 12px; border-radius:6px; font-size:11px; font-weight:800; letter-spacing:0.5px; font-family:'Montserrat', sans-serif;">
                PLANTA JUAN ESCUTIA
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================================
    # ENRUTAMIENTO MODULAR
    # =========================================================================
    if selected_menu == "📝 Registro y Cotizaciones (Fase 1)":
        render_requisition_wizard()
    elif selected_menu == "📑 Control de Orden de Compra (PO)":
        render_po_control()
    elif selected_menu == "📊 Panel de Control (Dashboard)":
        render_dashboard()
    elif selected_menu == "🔒 Mantenimiento y Respaldos":
        render_admin_backup()


if __name__ == "__main__":
    main()
