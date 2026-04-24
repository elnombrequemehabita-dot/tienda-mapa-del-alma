"""Token firmado para enlaces de reseña (solo quien tenga el enlace del correo)."""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = "mapa-alma-resenas-v1"
# 10 años: el enlace del correo sigue siendo válido sin caducar pronto
_MAX_AGE_SEC = 10 * 365 * 24 * 3600


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(str(secret_key), salt=_SALT)


def token_para_pedido(pedido_id: int, secret_key: str) -> str:
    return _serializer(secret_key).dumps({"p": int(pedido_id)})


def pedido_id_desde_token(token: str, secret_key: str) -> int | None:
    try:
        data = _serializer(secret_key).loads(token, max_age=_MAX_AGE_SEC)
        return int(data["p"])
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None
