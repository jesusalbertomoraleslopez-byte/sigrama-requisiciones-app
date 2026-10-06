"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Módulo de Sincronización con Google Cloud Storage (Cloud Run Persistencia)
=============================================================================
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

GCS_BUCKET = os.environ.get("GCS_BUCKET", "").strip()
_GCS_READY = False

def _gcs_bucket():
    from google.cloud import storage
    return storage.Client().bucket(GCS_BUCKET)

def sync_from_gcs():
    """Descarga todos los archivos de data/ desde el bucket de GCS al arrancar."""
    global _GCS_READY
    if not GCS_BUCKET:
        return False
    try:
        bucket = _gcs_bucket()
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
        print(f"[GCS] Sincronizados exitosamente {count} archivos desde gs://{GCS_BUCKET}")
        return True
    except Exception as e:
        print(f"[GCS] Error al sincronizar desde gs://{GCS_BUCKET}: {e}")
        return False

def push_file_to_gcs(local_path: Path):
    """Sube un archivo modificado o nuevo a GCS."""
    if not (GCS_BUCKET and _GCS_READY):
        return False
    try:
        p = Path(local_path)
        if not p.exists():
            return False
        bucket = _gcs_bucket()
        rel_path = p.relative_to(BASE_DIR).as_posix()
        bucket.blob(rel_path).upload_from_filename(str(p))
        print(f"[GCS] Archivo subido: {rel_path}")
        return True
    except Exception as e:
        print(f"[GCS] Error al subir {local_path} a GCS: {e}")
        return False

def delete_req_dir_from_gcs(req_folder_name: str):
    """Elimina una carpeta de requisición en GCS."""
    if not (GCS_BUCKET and _GCS_READY):
        return False
    try:
        bucket = _gcs_bucket()
        prefix = f"data/requisiciones/{req_folder_name}/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        for blob in blobs:
            blob.delete()
        print(f"[GCS] Eliminados {len(blobs)} archivos de {prefix} en GCS")
        return True
    except Exception as e:
        print(f"[GCS] Error eliminando {req_folder_name} de GCS: {e}")
        return False
