"""
Componentes visuales V10 — paneles con roundRect, sombras suaves y sellos con glow.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Flowable, Image as RLImage

from config import FONT_TITLE_FIRE_EARTH, FONT_TITLE_WATER_AIR

logger = logging.getLogger(__name__)


class GlowStampFlowable(Flowable):
    """PNG con halos suaves detrás para integrarse en fondos místicos."""

    def __init__(self, path: Optional[Path], max_side: float):
        self.path = path
        self.side = max_side
        self._img: RLImage | None = None
        self.width = 1.0
        self.height = 1.0

    def wrap(self, availWidth, availHeight):
        if self.path is None or not self.path.exists():
            self._img = None
            # Reserva espacio visible para no colapsar el layout (evita “página sin símbolo”).
            s = float(self.side)
            self.width = s + 12.0
            self.height = s + 12.0
            return self.width, self.height
        try:
            ap = self.path.resolve()
            self._img = RLImage(
                str(ap),
                width=self.side,
                height=self.side,
                kind="proportional",
                mask="auto",
            )
            w, h = self._img.wrap(availWidth, availHeight)
        except Exception as exc:  # noqa: BLE001
            logger.info("GlowStamp omitido (%s): %s", self.path, exc)
            self._img = None
            s = float(self.side)
            self.width = s + 12.0
            self.height = s + 12.0
            return self.width, self.height
        pad = 12.0
        self.width = float(w) + pad
        self.height = float(h) + pad
        return self.width, self.height

    def draw(self):
        if self._img is None:
            c = self.canv
            s = float(self.side)
            cx = self.width / 2.0
            cy = self.height / 2.0
            mx = max(self.width, self.height)
            for i, alpha in enumerate((0.12, 0.08, 0.05)):
                r = mx * (0.38 + i * 0.09)
                c.setFillColorRGB(0.92, 0.78, 0.42, alpha=alpha)
                c.circle(cx, cy, r, stroke=0, fill=1)
            c.setStrokeColorRGB(0.55, 0.48, 0.38, alpha=0.55)
            c.setLineWidth(0.9)
            c.roundRect(
                cx - s / 2,
                cy - s / 2,
                s,
                s,
                min(10.0, s * 0.08),
                stroke=1,
                fill=0,
            )
            # Sin texto placeholder: solo luz y marco (evita sensación de plantilla).
            return
        c = self.canv
        cx = self.width / 2.0
        cy = self.height / 2.0
        mx = max(self.width, self.height)
        for i, alpha in enumerate((0.14, 0.09, 0.05, 0.03)):
            r = mx * (0.36 + i * 0.1)
            c.setFillColorRGB(0.95, 0.82, 0.48, alpha=alpha)
            c.circle(cx, cy, r, stroke=0, fill=1)
        c.setFillColorRGB(0.15, 0.12, 0.22, alpha=0.18)
        c.circle(cx - 1.2, cy - 1.2, mx * 0.25, stroke=0, fill=1)
        iw = getattr(self._img, "drawWidth", self.side)
        ih = getattr(self._img, "drawHeight", self.side)
        ix = (self.width - iw) / 2.0
        iy = (self.height - ih) / 2.0
        self._img.drawOn(c, ix, iy)


def _set_title_font(canvas, size: float) -> str:
    """Usa una fuente titular registrada obligatoria (sin fallback a Helvetica)."""
    for family in (FONT_TITLE_WATER_AIR, FONT_TITLE_FIRE_EARTH):
        if family in pdfmetrics.getRegisteredFontNames():
            canvas.setFont(family, size)
            return family
    raise RuntimeError("No hay fuente titular registrada para glifos editoriales")


class DigitGlyphFlowable(Flowable):
    """Dígito dibujado cuando falta 1.png…9.png (misma huella que un sello)."""

    def __init__(self, digit: int, side: float):
        self.digit = max(1, min(9, int(digit)))
        self.side = float(side)
        pad = 12.0
        self.width = self.side + pad
        self.height = self.side + pad

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        cx = self.width / 2.0
        cy = self.height / 2.0
        mx = max(self.width, self.height)
        for i, alpha in enumerate((0.14, 0.09, 0.05, 0.03)):
            r = mx * (0.36 + i * 0.1)
            c.setFillColorRGB(0.95, 0.82, 0.48, alpha=alpha)
            c.circle(cx, cy, r, stroke=0, fill=1)
        c.setFillColorRGB(0.15, 0.12, 0.22, alpha=0.18)
        c.circle(cx - 1.2, cy - 1.2, mx * 0.25, stroke=0, fill=1)
        ch = str(self.digit)
        fs = self.side * 0.52
        name = _set_title_font(c, fs)
        tw = pdfmetrics.stringWidth(ch, name, fs)
        while tw > self.side * 0.92 and fs > 10:
            fs *= 0.92
            c.setFont(name, fs)
            tw = pdfmetrics.stringWidth(ch, name, fs)
        c.setFillColorRGB(0.12, 0.10, 0.14)
        c.drawCentredString(cx, cy - fs * 0.35, ch)


class ChineseGlyphFlowable(Flowable):
    """Nombre del animal chino dibujado cuando falta el PNG (misma familia visual)."""

    def __init__(self, label_es: str, side: float):
        self.label = (label_es or "?").strip() or "?"
        self.side = float(side)
        pad = 12.0
        self.width = self.side + pad
        self.height = self.side + pad

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        cx = self.width / 2.0
        cy = self.height / 2.0
        mx = max(self.width, self.height)
        for i, alpha in enumerate((0.14, 0.09, 0.05, 0.03)):
            r = mx * (0.36 + i * 0.1)
            c.setFillColorRGB(0.95, 0.82, 0.48, alpha=alpha)
            c.circle(cx, cy, r, stroke=0, fill=1)
        c.setFillColorRGB(0.15, 0.12, 0.22, alpha=0.18)
        c.circle(cx - 1.2, cy - 1.2, mx * 0.25, stroke=0, fill=1)
        text = self.label
        fs = min(self.side * 0.22, 22.0)
        name = _set_title_font(c, fs)
        tw = pdfmetrics.stringWidth(text, name, fs)
        while tw > self.side * 0.88 and fs > 9:
            fs *= 0.9
            c.setFont(name, fs)
            tw = pdfmetrics.stringWidth(text, name, fs)
        c.setFillColorRGB(0.12, 0.10, 0.14)
        c.drawCentredString(cx, cy - fs * 0.32, text)

