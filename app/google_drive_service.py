import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def obtener_servicio_drive():
    credentials_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH")

    if not credentials_path:
        raise RuntimeError(
            "No existe GOOGLE_DRIVE_CREDENTIALS_PATH en variables de entorno"
        )

    if not os.path.exists(credentials_path):
        raise RuntimeError(
            f"No existe archivo de credenciales: {credentials_path}"
        )

    creds = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES,
    )

    service = build("drive", "v3", credentials=creds)
    return service


def probar_conexion_drive():
    service = obtener_servicio_drive()

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not folder_id:
        raise RuntimeError(
            "No existe GOOGLE_DRIVE_FOLDER_ID en variables de entorno"
        )

    folder = service.files().get(
        fileId=folder_id,
        fields="id, name"
    ).execute()

    return (
        f"Google Drive conectado correctamente → "
        f"Carpeta encontrada: {folder['name']}"
    )


def subir_pdf_a_drive(pdf_path, nombre_archivo=None):
    service = obtener_servicio_drive()

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not folder_id:
        raise RuntimeError(
            "No existe GOOGLE_DRIVE_FOLDER_ID"
        )

    if not os.path.exists(pdf_path):
        raise RuntimeError(
            f"No existe el PDF: {pdf_path}"
        )

    if not nombre_archivo:
        nombre_archivo = os.path.basename(pdf_path)

    metadata = {
        "name": nombre_archivo,
        "parents": [folder_id],
    }

    media = MediaFileUpload(
        pdf_path,
        mimetype="application/pdf",
        resumable=True,
    )

    archivo = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink, webContentLink",
        supportsAllDrives=True
    ).execute()

    file_id = archivo["id"]

    permission = {
        "type": "anyone",
        "role": "reader",
    }

    service.permissions().create(
        fileId=file_id,
        body=permission,
        supportsAllDrives=True
    ).execute()

    archivo_actualizado = service.files().get(
        fileId=file_id,
        fields="id, webViewLink, webContentLink",
        supportsAllDrives=True
    ).execute()

    return {
        "file_id": archivo_actualizado["id"],
        "view_link": archivo_actualizado.get("webViewLink"),
        "download_link": archivo_actualizado.get("webContentLink"),
    }


def eliminar_archivo_drive(file_id):
    service = obtener_servicio_drive()

    service.files().delete(fileId=file_id).execute()

    return f"Archivo eliminado correctamente → {file_id}"
