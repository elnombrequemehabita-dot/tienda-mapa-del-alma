"""
Lectura de claves Stripe desde el `.env` en la raíz del proyecto.

Centralizado para que `create_app` y las rutas usen la misma lógica.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from dotenv import dotenv_values

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _strip_env_value(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if s.startswith("\ufeff"):
        s = s.lstrip("\ufeff").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def _value_from(file_vals: Mapping[str, Any], *key_names: str) -> str:
    for k in key_names:
        v = _strip_env_value(file_vals.get(k))
        if v:
            return v
    for k in key_names:
        v = _strip_env_value(os.environ.get(k))
        if v:
            return v
    return ""


def _secret_from(file_vals: Mapping[str, Any]) -> str:
    v = _value_from(file_vals, "STRIPE_SECRET_KEY")
    if v:
        return v
    alt = _value_from(file_vals, "STRIPE_API_KEY")
    if alt.startswith(("sk_", "rk_")):
        return alt
    return ""


def load_stripe_from_disk() -> tuple[str, str, str]:
    """
    Devuelve (STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY, STRIPE_WEBHOOK_SECRET)
    leyendo primero el archivo `.env` del proyecto.
    """
    file_vals: dict[str, Any] = {}
    if ENV_FILE.is_file():
        raw = dotenv_values(ENV_FILE)
        file_vals = {str(k): v for k, v in raw.items() if k is not None}
    sk = _secret_from(file_vals)
    pk = _value_from(file_vals, "STRIPE_PUBLIC_KEY", "STRIPE_PUBLISHABLE_KEY")
    wh = _value_from(file_vals, "STRIPE_WEBHOOK_SECRET")
    return sk, pk, wh
