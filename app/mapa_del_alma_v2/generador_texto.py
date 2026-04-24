"""
Generador de texto del libro Mapa del Alma (V15).

Orquesta perfil + narrativa usando únicamente `narrative_banks_v15` como banco
(vía `narrative.build_narrative`). El filtrado final pasa por `narrative_sanitize`.
"""
from __future__ import annotations

from datetime import date

import narrative_banks_v15  # noqa: F401 — fuente única de textos (ancla explícita)

from logic import SoulProfile, build_profile
from narrative import BookNarrative, build_narrative


def generar_narrativa(
    nombre: str,
    fecha: date,
    *,
    apellidos: str | None = None,
) -> BookNarrative:
    """
    Construye la narrativa completa del libro, lista para PDF.
    Todos los textos provienen de narrative_banks_v15 (composición en narrative.py).
    """
    perfil = build_profile(nombre, fecha, apellidos=apellidos)
    return build_narrative(perfil)


def generar_narrativa_desde_perfil(perfil: SoulProfile) -> BookNarrative:
    """Misma salida que `generar_narrativa`, partiendo de un SoulProfile ya calculado."""
    return build_narrative(perfil)
