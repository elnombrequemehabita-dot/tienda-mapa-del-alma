"""
Utilidades compartidas — Mapa del Alma V15.
"""
from __future__ import annotations

import re


def label_from_asset_filename(fname: str) -> str:
    """Convierte nombre de archivo PNG/JPG en etiqueta legible para narrativa."""
    if not fname:
        return ""
    base = fname.rsplit(".", 1)[0] if "." in fname else fname
    return base.replace("_", " ").strip()


def collapse_whitespace_html(html: str) -> str:
    """Normaliza espacios múltiples fuera de etiquetas HTML (uso interno)."""
    if not html:
        return html
    parts: list[str] = []
    for chunk in re.split(r"(<[^>]+>)", html):
        if chunk.startswith("<") and chunk.endswith(">"):
            parts.append(chunk)
        else:
            parts.append(re.sub(r"[ \t]+", " ", chunk))
    return "".join(parts)
