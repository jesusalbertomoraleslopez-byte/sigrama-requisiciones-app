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
<style>
    /* Modo incrustado en Concentradora SIGRAMA */
    header[data-testid="stHeader"], footer, div[data-testid="stDecoration"], div[class*="manageApp"], div[class*="ManageApp"], button[title*="Manage app"], [data-testid="stStatusWidget"] {
        display: none !important;
    }
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 6.5rem !important;
    }
</style>
"""

if is_embedded:
    st.markdown(embed_css, unsafe_allow_html=True)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Questrial&display=swap');

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
        color: #F8FAFC !important;
        font-family: 'Questrial', sans-serif !important;
    }

    /* Radio de navegación en sidebar: diseño tipo pastillas Odoo moderno y legible */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        gap: 6px !important;
        display: flex !important;
        flex-direction: column !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: #18181B !important;
        border: 1px solid #27272A !important;
        color: #F1F5F9 !important;
        padding: 10px 14px !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        margin: 0 !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label p,
    [data-testid="stSidebar"] div[role="radiogroup"] label span {
        font-size: 13.5px !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        color: #F1F5F9 !important;
        line-height: 1.4 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: #27272A !important;
        border-color: #EC2024 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
        background-color: #EC2024 !important;
        border-color: #EC2024 !important;
        box-shadow: 0 3px 10px rgba(236, 32, 36, 0.45) !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p,
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] span {
        color: #FFFFFF !important;
        font-weight: 800 !important;
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

    /* Marcador invisible para vincular estilos al botón nativo siguiente */
    div:has(.kanban-marker),
    div[data-testid="stElementContainer"]:has(.kanban-marker) {
        height: 0px !important;
        min-height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
        line-height: 0px !important;
        overflow: hidden !important;
    }

    /* Tarjetas Post-it Grandes y Unificadas (Botón Nativo Streamlit sin recarga) */
    div:has(.kanban-marker) + div button,
    div[data-testid="stElementContainer"]:has(.kanban-marker) + div[data-testid="stElementContainer"] button {
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        justify-content: flex-start !important;
        text-align: left !important;
        width: 100% !important;
        height: auto !important;
        min-height: 185px !important;
        padding: 16px 18px !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04) !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease !important;
        cursor: pointer !important;
        margin-bottom: 12px !important;
    }

    div:has(.kanban-marker) + div button:hover,
    div[data-testid="stElementContainer"]:has(.kanban-marker) + div[data-testid="stElementContainer"] button:hover {
        transform: translateY(-4px) scale(1.015) !important;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.16) !important;
    }

    div:has(.kanban-marker) + div button:active,
    div[data-testid="stElementContainer"]:has(.kanban-marker) + div[data-testid="stElementContainer"] button:active {
        transform: scale(0.99) !important;
    }

    div:has(.kanban-marker) + div button div[data-testid="stMarkdownContainer"],
    div[data-testid="stElementContainer"]:has(.kanban-marker) + div[data-testid="stElementContainer"] button div[data-testid="stMarkdownContainer"] {
        width: 100% !important;
        text-align: left !important;
    }

    div:has(.kanban-marker) + div button p,
    div[data-testid="stElementContainer"]:has(.kanban-marker) + div[data-testid="stElementContainer"] button p {
        text-align: left !important;
        white-space: pre-line !important;
        word-break: break-word !important;
        color: #0F172A !important;
        font-size: 13.5px !important;
        line-height: 1.55 !important;
        font-family: 'Questrial', 'Montserrat', -apple-system, sans-serif !important;
        margin: 0 !important;
    }

    div:has(.kanban-marker) + div button code,
    div[data-testid="stElementContainer"]:has(.kanban-marker) + div[data-testid="stElementContainer"] button code {
        background-color: rgba(0, 0, 0, 0.08) !important;
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 11px !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }

    /* Colores Post-it oficiales aplicados directamente a la tarjeta Kanban */
    div:has(.marker-amarillo) + div button, div[data-testid="stElementContainer"]:has(.marker-amarillo) + div button { background-color: #FEF08A !important; border: 1.5px solid #FDE047 !important; border-top: 8px solid #CA8A04 !important; }
    div:has(.marker-amarillo) + div button:hover { background-color: #FEF9C3 !important; }

    div:has(.marker-verde) + div button, div[data-testid="stElementContainer"]:has(.marker-verde) + div button { background-color: #BBF7D0 !important; border: 1.5px solid #86EFAC !important; border-top: 8px solid #16A34A !important; }
    div:has(.marker-verde) + div button:hover { background-color: #DCFCE7 !important; }

    div:has(.marker-azul) + div button, div[data-testid="stElementContainer"]:has(.marker-azul) + div button { background-color: #BAE6FD !important; border: 1.5px solid #7DD3FC !important; border-top: 8px solid #0284C7 !important; }
    div:has(.marker-azul) + div button:hover { background-color: #E0F2FE !important; }

    div:has(.marker-rosa) + div button, div[data-testid="stElementContainer"]:has(.marker-rosa) + div button { background-color: #FBCFE8 !important; border: 1.5px solid #F9A8D4 !important; border-top: 8px solid #DB2777 !important; }
    div:has(.marker-rosa) + div button:hover { background-color: #FCE7F3 !important; }

    div:has(.marker-naranja) + div button, div[data-testid="stElementContainer"]:has(.marker-naranja) + div button { background-color: #FED7AA !important; border: 1.5px solid #FDBA74 !important; border-top: 8px solid #EA580C !important; }
    div:has(.marker-naranja) + div button:hover { background-color: #FFEDD5 !important; }

    div:has(.marker-morado) + div button, div[data-testid="stElementContainer"]:has(.marker-morado) + div button { background-color: #DDD6FE !important; border: 1.5px solid #C4B5FD !important; border-top: 8px solid #7C3AED !important; }
    div:has(.marker-morado) + div button:hover { background-color: #EDE9FE !important; }

    div:has(.marker-turquesa) + div button, div[data-testid="stElementContainer"]:has(.marker-turquesa) + div button { background-color: #A5F3FC !important; border: 1.5px solid #67E8F9 !important; border-top: 8px solid #0891B2 !important; }
    div:has(.marker-turquesa) + div button:hover { background-color: #CFFAFE !important; }

    div:has(.marker-rojo) + div button, div[data-testid="stElementContainer"]:has(.marker-rojo) + div button { background-color: #FECACA !important; border: 1.5px solid #FCA5A5 !important; border-top: 8px solid #DC2626 !important; }
    div:has(.marker-rojo) + div button:hover { background-color: #FEE2E2 !important; }

    div:has(.marker-blanco) + div button, div[data-testid="stElementContainer"]:has(.marker-blanco) + div button { background-color: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; border-top: 8px solid #94A3B8 !important; }
    div:has(.marker-blanco) + div button:hover { background-color: #F8FAFC !important; }

    /* Tags Odoo (Pills redondeadas) */
    .odoo-pill {
        display: inline-block;
        font-size: 10px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 12px;
        margin-right: 4px;
        margin-bottom: 4px;
        line-height: 1.2;
    }

    /* Avatar circular estilo Odoo */
    .odoo-avatar {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        color: #FFFFFF;
        font-size: 9.5px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.15);
        flex-shrink: 0;
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


def check_authentication():
    """Valida credenciales de acceso institucional (jmorales / SigramaAdmin2026) y SSO."""
    if st.session_state.get("authenticated", False):
        return True

    # Soporte SSO robusto desde Concentradora SIGRAMA
    try:
        qp = dict(st.query_params) if hasattr(st, "query_params") else {}
        sso_token = qp.get("sso_token")
        if isinstance(sso_token, list): sso_token = sso_token[0] if sso_token else None
        sso_user_q = qp.get("sso_user")
        if isinstance(sso_user_q, list): sso_user_q = sso_user_q[0] if sso_user_q else None
        sso_role_q = qp.get("sso_role", "Admin")
        if isinstance(sso_role_q, list): sso_role_q = sso_role_q[0] if sso_role_q else "Admin"

        if sso_token == "SIGRAMA_AUTH_TOKEN" and sso_user_q:
            u_clean = str(sso_user_q).strip().lower()
            es_admin = sso_role_q == "Admin" or "jmorales" in u_clean or "admin" in u_clean or "morales" in u_clean
            st.session_state["authenticated"] = True
            st.session_state["usuario"] = sso_user_q
            st.session_state["usuario_actual"] = sso_user_q
            st.session_state["rol"] = "Admin" if es_admin else sso_role_q
            st.session_state["sso_user"] = sso_user_q
            st.session_state["sso_role"] = "Admin" if es_admin else sso_role_q
            if es_admin:
                st.session_state["admin_authenticated"] = True
            return True
    except Exception:
        pass

    # Si ya tiene sesión guardada
    if st.session_state.get("authenticated", False):
        return True

    # Ocultar barra lateral si no ha iniciado sesión
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    col_l1, col_l2, col_l3 = st.columns([1, 1.3, 1])
    with col_l2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        if LOGO_SIGRAMA_PATH.exists():
            with open(LOGO_SIGRAMA_PATH, "rb") as f:
                b64_login_logo = base64.b64encode(f.read()).decode()
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="background: #FFFFFF; display: inline-block; padding: 12px 24px; border-radius: 10px; box-shadow: 0 4px 14px rgba(0,0,0,0.06); margin-bottom: 12px;">
                    <img src="data:image/png;base64,{b64_login_logo}" style="width: 170px; height: auto; display: block;" alt="Industria Sigrama">
                </div>
                <h3 style="font-family: 'Montserrat', sans-serif; font-size: 20px; font-weight: 900; color: #111111; margin: 4px 0 2px 0;">
                    REQUISICIONES DE COMPRA
                </h3>
                <p style="color: #64748B; font-size: 13px; margin: 0; font-family: 'Questrial', sans-serif;">
                    Industria SIGRAMA S.A. de C.V. &bull; Acceso Autorizado
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="font-family: 'Montserrat', sans-serif; color: #EC2024; font-weight: 900; margin: 0;">INDUSTRIA SIGRAMA</h2>
                <h4 style="font-family: 'Montserrat', sans-serif; color: #111111; margin: 4px 0 0 0;">REQUISICIONES DE COMPRA</h4>
            </div>
            """, unsafe_allow_html=True)

        with st.form("form_login_requisiciones", clear_on_submit=False):
            st.markdown("""
            <div style="background: rgba(236,32,36,0.08); border-left: 3px solid #EC2024; padding: 8px 12px; border-radius: 4px; margin-bottom: 14px;">
                <span style="font-family: 'Montserrat', sans-serif; font-size: 12px; font-weight: 700; color: #EC2024;">
                    🔒 ACCESO DE ADMINISTRADOR
                </span>
                <div style="font-size: 11.5px; color: #475569; margin-top: 2px;">
                    Ingrese con su usuario y contraseña de Administrador.
                </div>
            </div>
            """, unsafe_allow_html=True)

            user_val = st.text_input("👤 Usuario:", placeholder="jmorales o admin", key="auth_user_field")
            pass_val = st.text_input("🔑 Contraseña:", type="password", placeholder="••••••••", key="auth_pass_field")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            btn_entrar = st.form_submit_button("Ingresar al Sistema", type="primary", use_container_width=True)

            if btn_entrar:
                u_clean = str(user_val).strip().lower()
                p_clean = str(pass_val).strip()

                valid_users = ["admin", "administrador", "jmorales", "sig-adm-01", "jesús morales", "jesus morales", "jesús alberto morales lópez", "jesus alberto morales lopez"]
                valid_passwords = ["SigramaAdmin2026", "SigramaMetales2026", "Sigrama123!", "Admin2026", "admin", "sigrama2026", "MAQUINADOS"]
                try:
                    if hasattr(st, "secrets") and "admin_password" in st.secrets:
                        valid_passwords.append(str(st.secrets["admin_password"]).strip())
                except Exception:
                    pass

                if (u_clean in valid_users or "morales" in u_clean or "admin" in u_clean) and p_clean in valid_passwords:
                    st.session_state["authenticated"] = True
                    st.session_state["admin_authenticated"] = True
                    st.session_state["usuario"] = "Jesús Alberto Morales López" if "morales" in u_clean or u_clean == "jmorales" else "admin"
                    st.session_state["usuario_actual"] = st.session_state["usuario"]
                    st.session_state["rol"] = "Admin"
                    st.session_state["sso_user"] = st.session_state["usuario"]
                    st.session_state["sso_role"] = "Admin"
                    st.success("✅ Acceso concedido como Administrador. Cargando...")
                    st.rerun()
                else:
                    st.error("❌ Credenciales inválidas. Verifique su usuario y contraseña.")
        return False


def main():
    """Función de arranque y enrutamiento modular del sistema."""
    init_databases()
    if not check_authentication():
        return

    # =========================================================================
    # SIDEBAR: IDENTIDAD CORPORATIVA SIGRAMA
    # =========================================================================
    with st.sidebar:
        # Logotipo SIGRAMA estilizado (tamaño óptimo y elegante ~160px centrado)
        logo_neg = BASE_DIR / "brand" / "logo_sigrama_negative.png"
        target_logo = logo_neg if logo_neg.exists() else LOGO_SIGRAMA_PATH
        if target_logo.exists():
            col_l1, col_l2, col_l3 = st.columns([0.15, 0.7, 0.15])
            with col_l2:
                st.image(str(target_logo), use_container_width=True)
        else:
            st.markdown("""
            <div style="text-align:center; padding:10px 0;">
                <div style="font-size:22px; font-weight:900; color:#FFFFFF; letter-spacing:1.5px;">SIGRAMA</div>
                <div style="font-size:10px; color:#EC2024; font-weight:800; letter-spacing:1px;">INDUSTRIA SIGRAMA</div>
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

        cur_user = st.session_state.get("usuario") or sso_user
        cur_role = st.session_state.get("rol") or sso_role
        if cur_user:
            st.markdown(f"""
            <div style="background-color:#18181B; border:1px solid #3F3F46; border-radius:6px; padding:10px 12px; margin-bottom:12px;">
                <div style="color:#A1A1AA; font-size:10px; text-transform:uppercase; letter-spacing:0.5px; font-weight:700;">👤 Sesión Conectada</div>
                <div style="color:#FFFFFF; font-weight:bold; font-size:13px; margin-top:2px;">{cur_user}</div>
                <div style="color:#EC2024; font-weight:700; font-size:11px; margin-top:1px;">Rol: {cur_role}</div>
            </div>
            """, unsafe_allow_html=True)
            if not is_embedded and st.button("🚪 Cerrar Sesión", key="btn_logout_sidebar", use_container_width=True):
                st.session_state["authenticated"] = False
                st.session_state["admin_authenticated"] = False
                st.session_state["usuario"] = None
                st.session_state["rol"] = None
                st.rerun()

        # Menú de Navegación por Fases
        menu_options = [
            "📊 Panel de Control (Dashboard)",
            "🗂️ Pipeline Kanban (CRM Odoo)",
            "📝 Registro y Cotizaciones (Fase 1)",
            "📑 Control de Orden de Compra (PO)",
            "🔒 Mantenimiento y Respaldos"
        ]

        if "selected_nav" not in st.session_state:
            st.session_state["selected_nav"] = menu_options[0]  # Dashboard por defecto

        selected_menu = st.radio(
            "Flujo de Operación:",
            options=menu_options,
            index=menu_options.index(st.session_state["selected_nav"]) if st.session_state["selected_nav"] in menu_options else 0,
            label_visibility="collapsed"
        )
        st.session_state["selected_nav"] = selected_menu

        st.markdown("<hr style='border-color:#27272A;'>", unsafe_allow_html=True)

        planta_activa = st.selectbox(
            "🏭 Planta:",
            options=["Planta Metales", "Planta Juan Escutia"],
            index=0,
            key="app_planta_activa"
        )

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
            v2.7.0 &bull; Industria Sigrama S.A. de C.V.<br>
            Planta Metalmecánica &bull; México
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # ENCABEZADO SUPERIOR CORPORATIVO EN EL ÁREA PRINCIPAL
    # =========================================================================
    user_header_badge = ""
    u_display = st.session_state.get("usuario") or sso_user
    r_display = st.session_state.get("rol") or sso_role
    if u_display:
        user_header_badge = f'<span style="background-color:#F1F5F9; color:#0F172A; border:1px solid #CBD5E1; padding:5px 12px; border-radius:6px; font-size:11px; font-weight:700; font-family:\'Montserrat\', sans-serif; margin-right:8px;">👤 {u_display} ({r_display})</span>'

    header_html = (
        '<div style="background-color:#FFFFFF; border-bottom:3px solid #EC2024; border-radius:8px; padding:14px 22px; margin-bottom:18px; box-shadow:0 2px 6px rgba(0,0,0,0.03); display:flex; justify-content:space-between; align-items:center;">'
        '<div>'
        '<div style="font-size:19px; font-weight:900; color:#111111; letter-spacing:0.5px; font-family:\'Montserrat\', sans-serif;">INDUSTRIA SIGRAMA S.A. DE C.V.</div>'
        '<div style="font-size:12px; color:#64748B; font-weight:600; text-transform:uppercase; letter-spacing:1px; margin-top:2px;">Módulo Central de Control y Seguimiento de Requisiciones de Compra</div>'
        '</div>'
        f'<div style="display:flex; align-items:center;">{user_header_badge}<span style="background-color:#FEF2F2; color:#DC2626; border:1px solid #FECACA; padding:5px 12px; border-radius:6px; font-size:11px; font-weight:800; letter-spacing:0.5px; font-family:\'Montserrat\', sans-serif;">{planta_activa.upper()}</span></div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # =========================================================================
    # ENRUTAMIENTO MODULAR
    # =========================================================================
    if selected_menu == "📊 Panel de Control (Dashboard)":
        st.session_state["odoo_view_mode"] = "📋 Lista Odoo"
        render_dashboard()
    elif selected_menu == "🗂️ Pipeline Kanban (CRM Odoo)":
        st.session_state["odoo_view_mode"] = "🗂️ Kanban Odoo"
        render_dashboard()
    elif selected_menu == "📝 Registro y Cotizaciones (Fase 1)":
        render_requisition_wizard()
    elif selected_menu == "📑 Control de Orden de Compra (PO)":
        render_po_control()
    elif selected_menu == "🔒 Mantenimiento y Respaldos":
        render_admin_backup()


if __name__ == "__main__":
    main()
