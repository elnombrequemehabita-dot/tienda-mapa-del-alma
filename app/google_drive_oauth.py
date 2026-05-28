from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError, ResumableUploadError
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_client_secret_path() -> Path:
    return _project_root() / "secrets" / "google_drive_oauth_client.json"


def _default_token_path() -> Path:
    return _project_root() / "secrets" / "google_drive_token.json"


def _default_service_account_path() -> Path:
    return _project_root() / "secrets" / "google_drive_service_account.json"


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
    return (os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON") or "").strip()


def _oauth_client_json_env() -> str:
    return (os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_JSON") or "").strip()


def _oauth_token_json_env() -> str:
    return (os.getenv("GOOGLE_DRIVE_TOKEN_JSON") or "").strip()


def _service_account_path() -> str:
    configured = (os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH") or "").strip()
    if configured:
        return configured

    default = _default_service_account_path()
    return str(default) if default.exists() else ""


def _hay_oauth_env_configurado() -> bool:
    return bool(_oauth_token_json_env())


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _hay_service_account_configurada() -> bool:
    raw_json = _service_account_json_env()
    raw_path = _service_account_path()

    return bool(raw_json or raw_path)


def obtener_credenciales_service_account():
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
        "No hay credenciales de Google Drive configuradas."
    )


def obtener_credenciales_oauth() -> Credentials:
    raw_token = _oauth_token_json_env()
    if raw_token:
        try:
            token_info = json.loads(raw_token)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_DRIVE_TOKEN_JSON no contiene JSON válido."
            ) from exc

        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            return creds
        raise RuntimeError(
            "GOOGLE_DRIVE_TOKEN_JSON no es válido o no contiene refresh_token."
        )

    client_path = _client_secret_path()
    token_path = _token_path()

    raw_client = _oauth_client_json_env()
    if raw_client and not client_path.exists():
        try:
            client_info = json.loads(raw_client)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_DRIVE_OAUTH_CLIENT_JSON no contiene JSON válido."
            ) from exc
        flow = InstalledAppFlow.from_client_config(client_info, SCOPES)
        creds = flow.run_local_server(port=0)
        return creds

    if not client_path.exists():
        raise FileNotFoundError(
            f"No existe el archivo OAuth client: {client_path}"
        )

    creds: Optional[Credentials] = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(
            str(token_path),
            SCOPES,
        )

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None

    if creds is None or not creds.valid:
        if _bool_env("GOOGLE_DRIVE_DISABLE_INTERACTIVE_OAUTH", False):
            raise RuntimeError(
                "OAuth de Google Drive no es válido y la reautorización interactiva está desactivada."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_path),
            SCOPES,
        )

        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)

    token_path.write_text(
        creds.to_json(),
        encoding="utf-8",
    )

    return creds


def obtener_servicio_drive_oauth():
    client_path = _client_secret_path()

    oauth_error: Exception | None = None
    if _hay_oauth_env_configurado() or client_path.exists():
        try:
            creds = obtener_credenciales_oauth()
            return build(
                "drive",
                "v3",
                credentials=creds,
            )
        except Exception as exc:  # noqa: BLE001
            oauth_error = exc

    if _hay_service_account_configurada():
        creds = obtener_credenciales_service_account()

        return build(
            "drive",
            "v3",
            credentials=creds,
        )

    if oauth_error is not None:
        raise oauth_error

    raise FileNotFoundError(
        "No existe OAuth client y tampoco hay Service Account configurada."
    )


def probar_conexion_drive_oauth() -> str:
    service = obtener_servicio_drive_oauth()

    folder_id = (os.getenv("GOOGLE_DRIVE_FOLDER_ID") or "").strip()

    if not folder_id:
        raise RuntimeError(
            "Falta GOOGLE_DRIVE_FOLDER_ID en variables de entorno."
        )

    folder = service.files().get(
        fileId=folder_id,
        fields="id, name",
        supportsAllDrives=True,
    ).execute()

    return (
        "Google Drive conectado correctamente → "
        f"Carpeta encontrada: {folder['name']}"
    )


def subir_pdf_a_drive_oauth(
    pdf_path: str | Path,
    nombre_archivo: Optional[str] = None,
) -> dict:
    service = obtener_servicio_drive_oauth()

    folder_id = (os.getenv("GOOGLE_DRIVE_FOLDER_ID") or "").strip()

    if not folder_id:
        raise RuntimeError(
            "Falta GOOGLE_DRIVE_FOLDER_ID en variables de entorno."
        )

    pdf_path = Path(pdf_path)

    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(
            f"No existe el PDF: {pdf_path}"
        )

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

    try:
        uploaded = service.files().create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink, webContentLink",
            supportsAllDrives=True,
        ).execute()
    except (HttpError, ResumableUploadError) as exc:
        error_text = str(exc)
        if "Service Accounts do not have storage quota" in error_text:
            raise RuntimeError(
                "Google Drive rechazó la subida con Service Account porque la carpeta está en Mi unidad. "
                "Para vender en producción usa GOOGLE_DRIVE_TOKEN_JSON de OAuth o mueve la carpeta a una unidad compartida."
            ) from exc
        raise

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


def eliminar_archivo_drive_oauth(file_id: str) -> dict:
    if not file_id:
        return {
            "ok": False,
            "error": "file_id vacío.",
        }

    try:
        service = obtener_servicio_drive_oauth()

        service.files().delete(
            fileId=file_id,
            supportsAllDrives=True,
        ).execute()

        return {
            "ok": True,
            "deleted": True,
            "file_id": file_id,
        }

    except Exception as exc:
        error_text = str(exc)

        if "File not found" in error_text or "404" in error_text:
            return {
                "ok": True,
                "deleted": False,
                "already_missing": True,
                "file_id": file_id,
            }

        return {
            "ok": False,
            "error": error_text,
            "file_id": file_id,
        }
