"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo de Sincronización de Alto Rendimiento con Google Cloud Storage (Cloud Run)
- Cliente Singleton reutilizable
- Caché en memoria con TTL (300s) y control de concurrencia thread-safe
- Solo descarga archivos nuevos o modificados
=============================================================================
"""

import os
import time
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

GCS_BUCKET = os.environ.get("GCS_BUCKET", "").strip()

_STORAGE_CLIENT = None
_BUCKET_OBJ = None
_SYNC_LOCK = threading.Lock()
_LAST_SYNC_TS = 0.0
_GCS_READY = False
SYNC_TTL = 300.0  # 5 minutos


def get_storage_client():
    """Retorna una instancia singleton de storage.Client()."""
    global _STORAGE_CLIENT
    if _STORAGE_CLIENT is None:
        from google.cloud import storage
        _STORAGE_CLIENT = storage.Client()
    return _STORAGE_CLIENT


def _gcs_bucket():
    """Retorna una instancia singleton del bucket."""
    global _BUCKET_OBJ
    if not GCS_BUCKET:
        return None
    if _BUCKET_OBJ is None or _BUCKET_OBJ.name != GCS_BUCKET:
        _BUCKET_OBJ = get_storage_client().bucket(GCS_BUCKET)
    return _BUCKET_OBJ


def sync_from_gcs(force: bool = False) -> bool:
    """Descarga todos los archivos de data/ desde el bucket de GCS al arrancar o si expira el TTL."""
    global _GCS_READY, _LAST_SYNC_TS
    if not GCS_BUCKET:
        return False

    now = time.time()
    if not force and (now - _LAST_SYNC_TS) < SYNC_TTL and _GCS_READY:
        return True

    with _SYNC_LOCK:
        now = time.time()
        if not force and (now - _LAST_SYNC_TS) < SYNC_TTL and _GCS_READY:
            return True

        try:
            bucket = _gcs_bucket()
            if not bucket:
                return False

            count = 0
            for blob in bucket.list_blobs(prefix="data/"):
                if blob.name.endswith("/"):
                    continue
                rel_parts = blob.name.split("/")
                local_path = BASE_DIR.joinpath(*rel_parts)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                if not local_path.exists() or local_path.stat().st_size != blob.size:
                    blob.download_to_filename(str(local_path))
                    count += 1
            _GCS_READY = True
            _LAST_SYNC_TS = time.time()
            print(f"[GCS] Sincronizados exitosamente {count} archivos desde gs://{GCS_BUCKET}")
            return True
        except Exception as e:
            print(f"[GCS] Error al sincronizar desde gs://{GCS_BUCKET}: {e}")
            return False


def push_file_to_gcs(local_path: Path):
    """Sube un archivo modificado o nuevo a GCS."""
    if not GCS_BUCKET:
        return False
    try:
        p = Path(local_path)
        if not p.exists():
            return False
        bucket = _gcs_bucket()
        if not bucket:
            return False
        rel_path = p.relative_to(BASE_DIR).as_posix()
        bucket.blob(rel_path).upload_from_filename(str(p))
        print(f"[GCS] Archivo subido: {rel_path}")
        return True
    except Exception as e:
        print(f"[GCS] Error al subir {local_path} a GCS: {e}")
        return False


def delete_req_dir_from_gcs(req_folder_name: str):
    """Elimina una carpeta de requisición en GCS."""
    if not GCS_BUCKET:
        return False
    try:
        bucket = _gcs_bucket()
        if not bucket:
            return False
        prefix = f"data/requisiciones/{req_folder_name}/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        for blob in blobs:
            blob.delete()
        print(f"[GCS] Eliminados {len(blobs)} archivos de {prefix} en GCS")
        return True
    except Exception as e:
        print(f"[GCS] Error eliminando {req_folder_name} de GCS: {e}")
        return False
