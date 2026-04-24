"""
Opciones del formulario público de pedido (tratamiento / cómo dirigirse al cliente).

Valores guardados en SQLite (columna `forma_trato`) en minúsculas y sin espacios.
"""
from __future__ import annotations

from typing import Optional

# Valores permitidos para el campo «¿Cómo quieres que nos dirijamos a ti?»
FORMAS_TRATO: tuple[str, ...] = (
    "femenino",
    "masculino",
    "neutro",
    "prefiero_no_decirlo",
)

FORMAS_TRATO_ETIQUETAS: dict[str, str] = {
    "femenino": "Femenino",
    "masculino": "Masculino",
    "neutro": "Neutro",
    "prefiero_no_decirlo": "Prefiero no decirlo",
}

# Para plantillas: (valor_bd, etiqueta_visible)
FORMAS_TRATO_OPCIONES: tuple[tuple[str, str], ...] = tuple(
    (c, FORMAS_TRATO_ETIQUETAS[c]) for c in FORMAS_TRATO
)


def etiqueta_forma_trato(valor: Optional[str]) -> str:
    """Texto para mostrar en admin; vacío o desconocido → «—»."""
    if not valor:
        return "—"
    return FORMAS_TRATO_ETIQUETAS.get(valor, valor)


def normalizar_forma_trato(valor: Optional[str]) -> Optional[str]:
    """
    Devuelve el código guardado en BD o None si viene vacío.
    Si el valor no es uno de los permitidos, devuelve None (la ruta debe rechazar).
    """
    v = (valor or "").strip().lower()
    if not v:
        return None
    if v not in FORMAS_TRATO:
        return None
    return v
