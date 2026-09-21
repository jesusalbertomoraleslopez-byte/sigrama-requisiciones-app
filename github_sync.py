"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo de Sincronización con GitHub (Persistencia en Streamlit Cloud)
=============================================================================
Cuando la app corre en Streamlit Cloud, el sistema de archivos es efímero:
cualquier escritura en Excel se pierde al reiniciar. Este módulo sincroniza
los archivos de base de datos (Excel) de vuelta al repositorio de GitHub
después de cada operación de escritura, garantizando la persistencia real.
"""

import base64
import io
import os
from pathlib import Path
from typing import Optional

import streamlit as st

# --- Configuración de credenciales desde st.secrets (Streamlit Cloud)
# o desde variables de entorno (ejecución local)

def _get_secret(key: str) -> Optional[str]:
    """Lee un secreto de Streamlit secrets o de variables de entorno."""
    try:
        return st.secrets.get(key)
    except Exception:
        pass
    return os.environ.get(key)


def _get_github_config() -> dict:
    """Retorna la configuración de GitHub necesaria para el sync."""
    return {
        "token": _get_secret("GITHUB_TOKEN"),
        "repo": _get_secret("GITHUB_REPO"),  # e.g. "user/sigrama-requisiciones-app"
        "branch": _get_secret("GITHUB_BRANCH") or "main",
    }


def push_file_to_github(local_path: Path, repo_path: str) -> bool:
    """
    Sube un archivo local al repositorio de GitHub usando la API REST.
    Crea o actualiza el archivo en el repo (con el SHA correcto para updates).

    Args:
        local_path: Ruta al archivo local a subir.
        repo_path:  Ruta relativa dentro del repo, e.g. 'data/BD_Requisiciones.xlsx'

    Returns:
        True si la operación fue exitosa, False si hubo error.
    """
    try:
        import urllib.request
        import json

        cfg = _get_github_config()
        token = cfg["token"]
        repo = cfg["repo"]
        branch = cfg["branch"]

        if not token or not repo:
            # Sin configuración de GitHub, operación local únicamente
            return True

        # Leer el archivo local como bytes y codificar en base64
        with open(local_path, "rb") as f:
            file_bytes = f.read()
        content_b64 = base64.b64encode(file_bytes).decode("utf-8")

        api_url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"

        # 1. Obtener el SHA actual del archivo (necesario para actualizarlo)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        current_sha = None
        try:
            req_get = urllib.request.Request(
                f"{api_url}?ref={branch}",
                headers=headers,
                method="GET"
            )
            with urllib.request.urlopen(req_get, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                current_sha = data.get("sha")
        except Exception:
            # El archivo no existe aún en el repo, se creará nuevo
            current_sha = None

        # 2. Preparar el payload para crear/actualizar
        payload = {
            "message": f"auto: actualización de {repo_path} desde Streamlit Cloud",
            "content": content_b64,
            "branch": branch,
        }
        if current_sha:
            payload["sha"] = current_sha

        payload_bytes = json.dumps(payload).encode("utf-8")

        req_put = urllib.request.Request(
            api_url,
            data=payload_bytes,
            headers={**headers, "Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req_put, timeout=30) as resp:
            status = resp.getcode()
            return status in (200, 201)

    except Exception as e:
        # No bloquear la operación por fallos de sync
        try:
            st.warning(f"⚠️ Sync GitHub: {e}", icon="⚠️")
        except Exception:
            pass
        return False


def push_excel_dbs_to_github() -> None:
    """
    Sube los tres archivos Excel de la base de datos al repositorio GitHub.
    Se llama después de cada operación de escritura importante para garantizar
    la persistencia cuando la app está en Streamlit Cloud.
    """
    from config import EXCEL_REQUISICIONES_PATH, EXCEL_COTIZACIONES_PATH, EXCEL_CATALOGOS_PATH

    files_to_sync = [
        (EXCEL_REQUISICIONES_PATH, "data/BD_Requisiciones.xlsx"),
        (EXCEL_COTIZACIONES_PATH, "data/BD_Cotizaciones.xlsx"),
        (EXCEL_CATALOGOS_PATH, "data/BD_Catalogos.xlsx"),
    ]

    for local_path, repo_path in files_to_sync:
        if local_path.exists():
            push_file_to_github(local_path, repo_path)


def is_running_on_streamlit_cloud() -> bool:
    """Detecta si la app está corriendo en Streamlit Cloud (o cualquier entorno remoto sin escritura persistente)."""
    # Streamlit Cloud setea STREAMLIT_SHARING_MODE o similar
    # También podemos checar si el token de GitHub está configurado
    cfg = _get_github_config()
    if not cfg["token"] or not cfg["repo"]:
        return False
    # Heurística: si estamos en /mount/src/ es Streamlit Cloud
    base = Path(__file__).resolve().parent
    return "/mount/src" in str(base) or "STREAMLIT_SHARING" in os.environ
