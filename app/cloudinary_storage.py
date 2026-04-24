"""
Subida de PDFs a Cloudinary para entrega por enlace.
"""
from __future__ import annotations

import os
from typing import Any

import cloudinary
import cloudinary.uploader


def _required_env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise ValueError(f"{name} no configurado en el entorno.")
    return value


def _configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=_required_env("CLOUDINARY_CLOUD_NAME"),
        api_key=_required_env("CLOUDINARY_API_KEY"),
        api_secret=_required_env("CLOUDINARY_API_SECRET"),
        secure=True,
    )


def upload_pdf(order_id: int, pdf_absolute_path: str) -> str:
    """
    Sube un PDF como archivo raw y devuelve secure_url.
    """
    _configure_cloudinary()
    result: dict[str, Any] = cloudinary.uploader.upload(
        pdf_absolute_path,
        resource_type="raw",
        folder="mapa_alma_pedidos",
        public_id=f"pedido_{int(order_id)}",
        overwrite=True,
        invalidate=True,
    )
    secure_url = str(result["secure_url"] or "").strip()
    if not secure_url:
        raise RuntimeError("Cloudinary no devolvió secure_url para el PDF.")
    if not secure_url.startswith("https://res.cloudinary.com/"):
        raise RuntimeError(f"URL de Cloudinary no válida para entrega pública: {secure_url}")
    return secure_url

