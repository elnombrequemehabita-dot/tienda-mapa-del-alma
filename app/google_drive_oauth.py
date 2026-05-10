from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_client_secret_path() -> Path:
    return _project_root() / "secrets" / "google_drive_oauth_client.json"


def _default_token_path() -> Path:
    return _project_root() / "secrets" / "google_drive_token.json"


def _client_secret_path() -> Path:
    configured = (os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_PATH") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_client_secret_path()


def _token_path() -> Path:
    configured = (os.getenv("GOOGLE_DRIVE_TOKEN_PATH") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_token_path()


def _service_account_json_env() -> str:
    """
    JSON completo de la Service Account guardado como variable de entorno.

    Render recomendado:
    GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON={...json completo...}
    """
    return (os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON") or "").strip()


def _service_account_path() -> str:
    """
    Ruta opcional a archivo JSON de Service Account.
    """
    return (os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH") or "").strip()


def _hay_service_account_configurada() -> bool:
    raw_json = _service_account_json_env()
    raw_path = _service_account_path()
    return bool(raw_json or raw_path)


def obtener_credenciales_service_account():
    """
    Credenciales de Google Drive para producción/Render.

    Prioridad:
    1. GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON con el JSON completo.
    2. GOOGLE_DRIVE_CREDENTIALS_PATH con ruta a archivo JSON.

    IMPORTANTE:
    La carpeta de Drive debe estar compartida con el email client_email
    de la Service Account.
    """
    raw_json = _service_account_json_env()

    if raw_json:
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON no contiene JSON válido."
            ) from exc

        return service_account.Credentials.from_service_account_info(
            info,
            scopes=SCOPES,
        )

    credentials_path = _service_account_path()
    if credentials_path:
        path = Path(credentials_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(
                f"No existe archivo de credenciales Service Account: {path}"
            )

        return service_account.Credentials.from_service_account_file(
            str(path),
            scopes=SCOPES,
        )

    raise RuntimeError(
        "No hay credenciales de Google Drive configuradas. "
        "Configura GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON o GOOGLE_DRIVE_CREDENTIALS_PATH."
    )


def obtener_credenciales_oauth() -> Credentials:
    """
    Obtiene credenciales OAuth para usar Google Drive con la cuenta real de Gmail.

    En local puede abrir navegador la primera vez.
    En Render/producción NO conviene depender de OAuth local; si no existe
    el archivo OAuth, se debe usar Service Account.
    """
    client_path = _client_secret_path()
    token_path = _token_path()

    if not client_path.exists():
        raise FileNotFoundError(
            f"No existe el archivo OAuth client: {client_path}. "
            "Debe llamarse google_drive_oauth_client.json y estar en secrets."
        )

    creds: Optional[Credentials] = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def obtener_servicio_drive_oauth():
    """
    Devuelve servicio Google Drive.

    Orden seguro:
    - Si hay OAuth local disponible, usa OAuth.
    - Si OAuth no existe y hay Service Account configurada, usa Service Account.
    - Si no hay nada configurado, falla con mensaje claro.
    """
    client_path = _client_secret_path()

    if client_path.exists():
        creds = obtener_credenciales_oauth()
        return build("drive", "v3", credentials=creds)

    if _hay_service_account_configurada():
        creds = obtener_credenciales_service_account()
        return build("drive", "v3", credentials=creds)

    raise FileNotFoundError(
        f"No existe OAuth client en {client_path} y tampoco hay Service Account "
        "configurada. En Render configura GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON "
        "y GOOGLE_DRIVE_FOLDER_ID."
    )


def probar_conexion_drive_oauth() -> str:
    service = obtener_servicio_drive_oauth()

    folder_id = (os.getenv("GOOGLE_DRIVE_FOLDER_ID") or "").strip()
    if not folder_id:
        raise RuntimeError("Falta GOOGLE_DRIVE_FOLDER_ID en variables de entorno.")

    folder = service.files().get(
        fileId=folder_id,
        fields="id, name",
        supportsAllDrives=True,
    ).execute()

    return f"Google Drive conectado correctamente → Carpeta encontrada: {folder['name']}"


def subir_pdf_a_drive_oauth(pdf_path: str | Path, nombre_archivo: Optional[str] = None) -> dict:
    """
    Sube un PDF a Google Drive.

    Conserva el nombre público de la función para no tocar order_services.py,
    pero ahora funciona también en Render con Service Account.
    """
    service = obtener_servicio_drive_oauth()

    folder_id = (os.getenv("GOOGLE_DRIVE_FOLDER_ID") or "").strip()
    if not folder_id:
        raise RuntimeError("Falta GOOGLE_DRIVE_FOLDER_ID en variables de entorno.")

    pdf_path = Path(pdf_path)
    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(f"No existe el PDF: {pdf_path}")

    if nombre_archivo is None:
        nombre_archivo = pdf_path.name

    metadata = {
        "name": nombre_archivo,
        "parents": [folder_id],
    }

    media = MediaFileUpload(
        str(pdf_path),
        mimetype="application/pdf",
        resumable=True,
    )

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink, webContentLink",
        supportsAllDrives=True,
    ).execute()

    file_id = uploaded["id"]

    permission = {
        "type": "anyone",
        "role": "reader",
    }

    service.permissions().create(
        fileId=file_id,
        body=permission,
        supportsAllDrives=True,
    ).execute()

    final_file = service.files().get(
        fileId=file_id,
        fields="id, name, webViewLink, webContentLink",
        supportsAllDrives=True,
    ).execute()

    return {
        "file_id": final_file["id"],
        "name": final_file.get("name"),
        "view_link": final_file.get("webViewLink"),
        "download_link": final_file.get("webContentLink"),
    }


def eliminar_archivo_drive_oauth(file_id: str) -> str:
    if not file_id:
        raise ValueError("file_id vacío.")

    service = obtener_servicio_drive_oauth()
    service.files().delete(
        fileId=file_id,
        supportsAllDrives=True,
    ).execute()

    return f"Archivo eliminado correctamente de Google Drive → {file_id}"
