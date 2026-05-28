"""Tokens firmados para descargas locales de PDF.

La entrega normal usa Google Drive. Este token protege el enlace local de
respaldo para que /descarga/<id> no sea adivinable por número de pedido.
"""
from __future__ import annotations

import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = "mapa-alma-descargas-v1"


def _max_age_sec() -> int:
    try:
        horas = int(os.getenv("PDF_DOWNLOAD_TOKEN_MAX_AGE_HOURS", "48"))
    except (TypeError, ValueError):
        horas = 48
    return max(1, horas) * 3600


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    safe_key = str(secret_key or "").strip()
    if not safe_key:
        raise RuntimeError("SECRET_KEY no configurada para tokens de descarga.")
    return URLSafeTimedSerializer(safe_key, salt=_SALT)


def token_para_descarga(pedido_id: int, secret_key: str) -> str:
    return _serializer(secret_key).dumps({"p": int(pedido_id)})


def pedido_id_desde_token_descarga(token: str, secret_key: str) -> int | None:
    try:
        data = _serializer(secret_key).loads(token, max_age=_max_age_sec())
        return int(data["p"])
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None
