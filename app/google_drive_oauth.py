from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
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


def obtener_credenciales_oauth() -> Credentials:
    """
    Obtiene credenciales OAuth para usar Google Drive con la cuenta real de Gmail.

    Primera vez:
    - Abre navegador.
    - La usuaria inicia sesión.
    - Se guarda secrets/google_drive_token.json.

    Siguientes veces:
    - Reutiliza el token guardado.
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
    creds = obtener_credenciales_oauth()
    return build("drive", "v3", credentials=creds)


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

    return f"OAuth Google Drive conectado correctamente → Carpeta encontrada: {folder['name']}"


def subir_pdf_a_drive_oauth(pdf_path: str | Path, nombre_archivo: Optional[str] = None) -> dict:
    """
    Sube un PDF a Google Drive usando OAuth con la cuenta Gmail real.

    Devuelve:
    - file_id
    - view_link
    - download_link
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
