"""
Mapa del Alma — capa editorial «premium» del PDF (layout, proporciones, ritmo de página).

La lógica de datos (signo, imágenes, narrativa) sigue en `logic` / `narrative` / `pdf_engine.build_pdf`;
aquí solo hay decisiones de maquetación reutilizable.

Evitar import circular: no importar `pdf_engine` a nivel de módulo.
"""
from __future__ import annotations

from enum import IntEnum


class SectionLayout(IntEnum):
    """Layouts reutilizables para secciones con sello + texto."""

    LAYOUT_A = 0  # Sello arriba a la izquierda; cuerpo ancho completo debajo
    LAYOUT_B = 1  # Título + cuerpo primero; sello grande centrado debajo
    LAYOUT_C = 2  # Tipo cita: tipografía centrada más grande; sello discreto abajo


# --- Portada: sin caja blanca dominante (nombre sobre fondo; velo muy suave si se usa panel) ---
PREMIUM_COVER_USE_TEXT_ONLY_BLOCK = True
PREMIUM_COVER_NAME_DATE_PANEL_ALPHA = 0.10
PREMIUM_COVER_NAME_FONT_SIZE = 40.0
PREMIUM_COVER_NAME_LEADING = 46.0
PREMIUM_COVER_BIRTH_FONT_SIZE = 12.8
PREMIUM_COVER_BIRTH_LEADING = 16.0
PREMIUM_COVER_NAME_SPACER_AFTER = 10.0

# --- Sellos: ~32–45 % del menor lado útil (paisaje = altura suele mandar) ---
HERO_FRAC_MIN = 0.22
HERO_FRAC_MAX = 0.32
STAMP_MAX_WIDTH_FRAC = 0.34
STAMP_BUDGET_PT = 520.0

# Cierre: sello algo más compacto para favorecer una sola página editorial
FIRMA_UNIVERSO_STAMP_LAST_PREMIUM_PT = 136.0

# Un título (sección) por página: no fusionar signo/elemento en la misma hoja.
MERGE_HERO_PAGE_BREAK_AFTER_SIGN_ELEMENT = False

# Prueba: en «El código de tu nombre», mapa a la izquierda del texto (misma página).
TRIAL_CODIGO_MAPA_LEFT_OF_TEXT = True


def pick_section_layout(hero_index: int) -> SectionLayout:
    """Ciclo A → B → C según el índice de sección héroe."""
    return SectionLayout(hero_index % 3)


def build_pdf(  # noqa: ANN001 - firma idéntica a pdf_engine.build_pdf
    profile,
    narrative,
    output_path=None,
):
    from pdf_engine import build_pdf as _build

    return _build(profile, narrative, output_path)


__all__ = [
    "SectionLayout",
    "build_pdf",
    "pick_section_layout",
    "PREMIUM_COVER_USE_TEXT_ONLY_BLOCK",
    "PREMIUM_COVER_NAME_DATE_PANEL_ALPHA",
    "PREMIUM_COVER_NAME_FONT_SIZE",
    "PREMIUM_COVER_NAME_LEADING",
    "PREMIUM_COVER_BIRTH_FONT_SIZE",
    "PREMIUM_COVER_BIRTH_LEADING",
    "PREMIUM_COVER_NAME_SPACER_AFTER",
    "HERO_FRAC_MIN",
    "HERO_FRAC_MAX",
    "STAMP_MAX_WIDTH_FRAC",
    "STAMP_BUDGET_PT",
    "FIRMA_UNIVERSO_STAMP_LAST_PREMIUM_PT",
    "MERGE_HERO_PAGE_BREAK_AFTER_SIGN_ELEMENT",
    "TRIAL_CODIGO_MAPA_LEFT_OF_TEXT",
]
