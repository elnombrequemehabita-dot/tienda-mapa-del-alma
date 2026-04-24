"""
Mapa del Alma V15 — motor PDF de lujo (ReportLab).

Integra `editorial_flowables` (sellos, glifos), `firma_universo` (cierre) y fondos por signo.
La narrativa llega ya filtrada por `narrative_sanitize`; aquí se valida de nuevo antes de maquetar.
"""
from __future__ import annotations

import logging
import math
import os
import random
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import ImageAndFlowables, _FUZZ
from reportlab.platypus import (
    Flowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    KeepTogether,
    KeepInFrame,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tables import LongTable

from config import (
    BORDE_ALPHA,
    CAJA_PADDING_X,
    CAJA_PADDING_Y,
    CAJA_STROKE_WIDTH,
    COLOR_BORDE_CAJA,
    COLOR_SUBTITULO_MARFIL,
    COLOR_TEXTO_CLARO,
    COLOR_TEXTO_SECUNDARIO,
    COLOR_TITULO_DORADO,
    COLOR_TITULO_DORADO_SUAVE,
    ELEMENT_PANEL_COLORS,
    COVER_GAP_MAP_TO_TEXT_MAX,
    COVER_GAP_MAP_TO_TEXT_MIN,
    COVER_NAME_DATE_PANEL_ALPHA,
    COVER_LOGO_CORNER_PT,
    COVER_TITLE_IMAGE,
    COVER_TITLE_IMAGE_MAX_PT,
    FIRMA_UNIVERSO_STAMP_LAST_PT,
    FIRMA_UNIVERSO_STAMP_PT,
    HERO_MAX_FRAC_MIN_SIDE,
    HERO_MIN_FRAC_MIN_SIDE,
    HERO_STAMP_PT,
    FONT_BODY_FIRE_EARTH,
    FONT_BODY_FIRE_EARTH_ITALIC,
    FONT_BODY_WATER_AIR,
    FONT_BODY_WATER_AIR_ITALIC,
    FONT_DETAIL_MONTSERRAT,
    FONT_DETAIL_POPPINS,
    FONT_FILES,
    FONT_SCRIPT_SIGNATURE,
    FONT_SUBTITULO,
    FONT_TEXTO,
    FONT_TEXTO_ITALICA,
    FONT_TITULO,
    FONT_DESTACADO,
    FONT_TITLE_FIRE_EARTH,
    FONT_TITLE_IMPACT,
    FONT_TITLE_WATER_AIR,
    FONTS_DIR,
    HEADING_ON_BACKGROUND_RGB,
    IMAGES_DIR,
    LOGO_FILE,
    OUTPUT_DIR,
    SIGN_THEMES,
    SIGN_BACKGROUND_VEIL_ALPHA,
    SIZE_FRASE_DESTACADA,
    SIZE_PORTADA_FECHA,
    SIZE_PORTADA_MAPA,
    SIZE_PORTADA_NOMBRE,
    SIZE_SUBTITULO,
    SIZE_TEXTO,
    SIZE_TEXTO_PEQUENO,
    SIZE_TITULO,
    LEADING_FRASE,
    LEADING_SUBTITULO,
    LEADING_TEXTO,
    LEADING_TITULO,
    SPACE_AFTER_PARRAFO,
    SPACE_AFTER_SUBTITULO,
    SPACE_AFTER_TITULO,
    SPACE_BEFORE_FRASE_DESTACADA,
    SPACE_AFTER_FRASE_DESTACADA,
    STAMP_DEFAULT_PT,
    TEXT_BODY_INK_RGB,
    TEXT_PANEL_ALPHA,
    TEXT_PANEL_PAD,
    TEXT_PANEL_RADIUS,
    TEXT_PANEL_RGB,
)
from editorial_flowables import (
    ChineseGlyphFlowable,
    DigitGlyphFlowable,
    GlowStampFlowable,
)
import image_assets
from firma_universo import dibujar_firma_universo, estimate_firma_block_height
from logic import SoulProfile, digits_for_numerology_stamp, element_for_sign, expected_image_paths, long_birth_date
from narrative import BookNarrative
from narrative_sanitize import validate_book_strings
from generador_pdf import (
    FIRMA_UNIVERSO_STAMP_LAST_PREMIUM_PT,
    HERO_FRAC_MAX,
    HERO_FRAC_MIN,
    MERGE_HERO_PAGE_BREAK_AFTER_SIGN_ELEMENT,
    PREMIUM_COVER_BIRTH_FONT_SIZE,
    PREMIUM_COVER_BIRTH_LEADING,
    PREMIUM_COVER_NAME_DATE_PANEL_ALPHA,
    PREMIUM_COVER_NAME_FONT_SIZE,
    PREMIUM_COVER_NAME_LEADING,
    PREMIUM_COVER_NAME_SPACER_AFTER,
    PREMIUM_COVER_USE_TEXT_ONLY_BLOCK,
    SectionLayout,
    STAMP_BUDGET_PT,
    STAMP_MAX_WIDTH_FRAC,
    TRIAL_CODIGO_MAPA_LEFT_OF_TEXT,
    pick_section_layout,
)

logger = logging.getLogger(__name__)

# Horizontal (apaisado): 11" de ancho × 8.5" de alto = US Letter landscape (792 × 612 pt).
PAGE_W = 11.0 * inch
PAGE_H = 8.5 * inch
PAGE_SIZE: tuple[float, float] = (PAGE_W, PAGE_H)


class ShadowParagraph(Flowable):
    """Mismo párrafo en dos capas: sombra oscura desplazada + tinta definitiva (profundidad)."""

    def __init__(
        self,
        html: str,
        style: ParagraphStyle,
        shadow_style: ParagraphStyle,
        shadow_dx: float = 1.2,
        shadow_dy: float = -1.2,
        *,
        _p: Paragraph | None = None,
        _ps: Paragraph | None = None,
    ):
        self._html = html
        self._p = Paragraph(html, style) if _p is None else _p
        self._ps = Paragraph(html, shadow_style) if _ps is None else _ps
        self._dx = shadow_dx
        self._dy = shadow_dy
        self.width = 0.0
        self.height = 0.0

    def wrap(self, availWidth, availHeight):
        w, h = self._p.wrap(availWidth, availHeight)
        # Misma geometría para la capa sombra (evita blPara ausente al drawOn)
        self._ps.wrap(availWidth, availHeight)
        self.width = w
        self.height = h
        return w, h

    def split(self, aW: float, aH: float) -> List[Flowable]:
        """Delega en Paragraph.split para que bloques largos no se recorten al pie de página."""
        if aW < _FUZZ or aH < _FUZZ:
            return []
        self._p.wrap(aW, aH)
        self._ps.wrap(aW, aH)
        mp = self._p.split(aW, aH)
        if not mp:
            return []
        if len(mp) == 1:
            return [self]
        sp = self._ps.split(aW, aH)
        if len(sp) != len(mp):
            return [self]
        return [
            ShadowParagraph(
                self._html,
                pm.style,
                psm.style,
                shadow_dx=self._dx,
                shadow_dy=self._dy,
                _p=pm,
                _ps=psm,
            )
            for pm, psm in zip(mp, sp)
        ]

    def draw(self):
        self._ps.drawOn(self.canv, self._dx, self._dy)
        self._p.drawOn(self.canv, 0, 0)


def _sp(
    html: str,
    styles: dict[str, ParagraphStyle],
    main_key: str,
    shadow_key: str,
    *,
    dx: float = 0.6,
    dy: float = -0.6,
) -> ShadowParagraph:
    # Se desactiva la doble capa para evitar efecto de texto "duplicado".
    del shadow_key, dx, dy
    return Paragraph(html, styles[main_key])


def _text_flow(html: str, styles: dict[str, ParagraphStyle], style_key: str) -> Flowable:
    """Párrafo con sombra solo en el trazo (capa duplicada), si existe style_key_sh."""
    sk = f"{style_key}_sh"
    if sk in styles:
        return _sp(html, styles, style_key, sk)
    return Paragraph(html, styles[style_key])


def _hp(html: str, styles: dict[str, ParagraphStyle]) -> ShadowParagraph:
    """Título de sección sobre fondo: sombra solo en el texto (no en el panel)."""
    return Paragraph(html, styles["heading"])


FIRMA_UNIVERSO_LEYENDA = (
    "El sello geométrico representa tu identidad simbólica en este mapa y se genera con tus datos base. "
    "Se utiliza como marca de autenticidad y se activa cuando lo contemplas, respiras y sellas una decisión concreta."
)


def _localized_strings() -> dict[str, str]:
    return {
        "book_title": "Mapa del Alma",
        "codigo_title": "<b>El código de tu nombre</b><br/><i>Origen, significado vivo y el nombre que te habita</i>",
        "eco_title": "<b>El eco de tus ancestros</b><br/><i>La fuerza del linaje en tus apellidos</i>",
        "tu_elemento": "Tu elemento",
        "esencia_title": "<b>Esencia astral</b><br/><i>Signo y elemento en acción</i>",
        "astro_title": "<b>Tu astro regente</b><br/><i>Influencia planetaria</i>",
        "totem_title": "<b>Tu animal tótem</b><br/><i>Instinto y poder silencioso</i>",
        "arcangel_title": "<b>Tu arcángel guía</b><br/><i>Protección y mensaje</i>",
        "gema_title": "<b>Tu gema de poder</b><br/><i>Energía y ancla</i>",
        "sabiduria_title": "<b>Sabiduría oriental</b><br/><i>Zodiaco chino integrado</i>",
        "numerologia_title": "<b>Numerología sagrada</b><br/><i>Tu vibración y misión numérica</i>",
        "wow_1": "Tu forma de amar<br/>no es debilidad.<br/><br/>Es historia viva en ti.<br/>Nadie te enseñó a sostenerla sin culpa.",
        "hilo_title": "<b>El hilo invisible</b><br/><i>La conexión maestra de tus contradicciones</i>",
        "sombra_title": "<b>Poder y sombra sagrada</b><br/><i>Luces y sombras con nombre</i>",
        "wow_2": "Tu problema no es sentir mucho.<br/>Es no saber dónde poner ese sentimiento.<br/><br/>Cuando le das lugar,<br/>tu vida respira.",
        "mensaje_title": "<b>Mensaje personal</b><br/><i>Clímax de esta lectura</i>",
        "cierre_title": "<b>Contraportada y firma del universo</b>",
        "cierre_1": "<i>Lectura cerrada; camino abierto: lo tuyo no se discute, se habita.</i>",
        "cierre_2": "<i>Un mapa no te salva: te recuerda quién eres cuando el mundo se vuelve ruido.</i>",
        "cierre_3": "<i>Llévate una verdad, no un manual: un paso honesto pesa más que mil promesas.</i>",
        "cierre_4": "<i>Tu nombre es puerta, no jaula: cruzarla es volver a elegirte.</i>",
        "cierre_5": "<i>El cierre no es despedida: es permiso para habitar lo que ya reconoces.</i>",
        "cierre_6": "<i>Lo que queda impreso aquí solo cobra vida si lo vuelves gesto en el día de hoy.</i>",
    }

# Paleta mate activa para paneles translúcidos (se actualiza por signo en build_pdf).
_ACTIVE_PANEL_RGB = TEXT_PANEL_RGB
_ACTIVE_PANEL_ALPHA = TEXT_PANEL_ALPHA


def _blend_rgb(a: tuple[float, float, float], b: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    """Interpolación RGB simple (t=0 -> a, t=1 -> b)."""
    tt = max(0.0, min(1.0, float(t)))
    return (
        a[0] + (b[0] - a[0]) * tt,
        a[1] + (b[1] - a[1]) * tt,
        a[2] + (b[2] - a[2]) * tt,
    )


def _activate_matte_palette(sign_key: str) -> None:
    """Configura panel mate por elemento con alpha editorial fijo."""
    global _ACTIVE_PANEL_RGB, _ACTIVE_PANEL_ALPHA
    elem = element_for_sign(sign_key if sign_key in SIGN_THEMES else "leo")
    _ACTIVE_PANEL_RGB = ELEMENT_PANEL_COLORS.get(elem, TEXT_PANEL_RGB)
    _ACTIVE_PANEL_ALPHA = TEXT_PANEL_ALPHA


class FirmaUniversoFlowable(Flowable):
    """Bloque de contraportada: mensaje del universo + sello único grande (canvas)."""

    def __init__(
        self,
        nombre: str,
        numero_maestro: int,
        fecha_nacimiento: date,
        box_width: float,
        *,
        stamp_size: float | None = None,
        leyenda: str | None = None,
    ):
        self.nombre = nombre
        self.numero_maestro = numero_maestro
        self.fecha_nacimiento = fecha_nacimiento
        self._bw = box_width
        self._size = float(stamp_size if stamp_size is not None else FIRMA_UNIVERSO_STAMP_PT)
        self._leyenda = leyenda if leyenda is not None else FIRMA_UNIVERSO_LEYENDA

    def wrap(self, availWidth, availHeight):
        h = estimate_firma_block_height(
            self._bw,
            size=self._size,
            leyenda=self._leyenda,
        )
        return min(self._bw, availWidth), h

    def draw(self):
        dibujar_firma_universo(
            self.canv,
            0,
            0,
            self.nombre,
            self.numero_maestro,
            size=self._size,
            fecha_nacimiento=self.fecha_nacimiento,
            box_width=self._bw,
            leyenda=self._leyenda,
        )


def resolve_asset(filename: str) -> Optional[Path]:
    """Alias: un nombre de archivo exacto en la raíz de assets/imagenes (p. ej. dígitos de numerología)."""
    if not filename:
        return None
    if not IMAGES_DIR.is_dir():
        logger.warning("Carpeta de imágenes no encontrada o no es directorio: %s", IMAGES_DIR)
        return None
    hit = image_assets.resolve_flat_filename(filename)
    if not hit:
        logger.debug("No se encontró archivo plano: %s", filename)
    return hit


def resolve_sign_background(sign_key: str) -> Optional[Path]:
    """Fondo por signo: solo archivos listados en config (sin mezclar otros assets)."""
    return image_assets.resolve_background_sign(sign_key)


def register_fonts() -> None:
    """Registra fuentes locales obligatorias (sin fallback a fuentes genéricas)."""
    registered: set[str] = set()
    missing_or_failed: list[str] = []
    for logical, fname in FONT_FILES.items():
        if logical in registered:
            continue
        path = FONTS_DIR / fname
        if not path.exists():
            missing_or_failed.append(f"{logical}: faltante ({path})")
            continue
        try:
            pdfmetrics.registerFont(TTFont(logical, str(path)))
            registered.add(logical)
        except Exception as exc:  # noqa: BLE001
            missing_or_failed.append(f"{logical}: error registro ({exc})")
    if missing_or_failed:
        msg = "Fuentes obligatorias no disponibles: " + " | ".join(missing_or_failed)
        logger.error(msg)
        raise RuntimeError(msg)


def _ensure_font(logical_name: str) -> str:
    if logical_name not in pdfmetrics.getRegisteredFontNames():
        raise RuntimeError(f"Fuente no registrada: {logical_name}")
    return logical_name


def _font_pack_for_sign(sign_key: str) -> dict[str, str]:
    elem = element_for_sign(sign_key if sign_key in SIGN_THEMES else "leo")
    if elem in ("agua", "aire"):
        title = _ensure_font(FONT_TITLE_WATER_AIR)
        body = _ensure_font(FONT_BODY_WATER_AIR)
        body_italic = _ensure_font(FONT_BODY_WATER_AIR_ITALIC)
        detail = _ensure_font(FONT_DETAIL_MONTSERRAT)
    else:
        title = _ensure_font(FONT_TITLE_FIRE_EARTH)
        body = _ensure_font(FONT_BODY_FIRE_EARTH)
        body_italic = _ensure_font(FONT_BODY_FIRE_EARTH_ITALIC)
        detail = _ensure_font(FONT_DETAIL_POPPINS)
    return {
        "title": title,
        "body": body,
        "body_italic": body_italic,
        "detail": detail,
        "script": _ensure_font(FONT_SCRIPT_SIGNATURE),
        "impact": _ensure_font(FONT_TITLE_IMPACT),
    }


def build_styles(sign_key: str = "leo") -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    pack = _font_pack_for_sign(sign_key)
    tf = _ensure_font(FONT_TITULO)
    bf = _ensure_font(FONT_TEXTO)
    bif = _ensure_font(FONT_TEXTO_ITALICA)
    df = _ensure_font(FONT_SUBTITULO)
    sf = pack["script"]
    impact_f = _ensure_font(FONT_DESTACADO)
    theme = SIGN_THEMES.get(sign_key, SIGN_THEMES["leo"])
    glow = theme["glow"]

    panel_luma = (
        0.2126 * _ACTIVE_PANEL_RGB[0]
        + 0.7152 * _ACTIVE_PANEL_RGB[1]
        + 0.0722 * _ACTIVE_PANEL_RGB[2]
    )
    dark_panel = panel_luma < 0.56
    ink = Color(COLOR_TEXTO_CLARO.red, COLOR_TEXTO_CLARO.green, COLOR_TEXTO_CLARO.blue, alpha=1)
    heading_bg = Color(
        COLOR_SUBTITULO_MARFIL.red,
        COLOR_SUBTITULO_MARFIL.green,
        COLOR_SUBTITULO_MARFIL.blue,
        alpha=1,
    )
    styles = {
        "title": ParagraphStyle(
            name="mda_title",
            parent=base["Title"],
            fontName=tf,
            fontSize=42,
            leading=46,
            textColor=colors.white,
            alignment=1,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            name="mda_subtitle",
            parent=base["Heading1"],
            fontName=df,
            fontSize=SIZE_SUBTITULO,
            leading=LEADING_SUBTITULO,
            textColor=Color(COLOR_SUBTITULO_MARFIL.red, COLOR_SUBTITULO_MARFIL.green, COLOR_SUBTITULO_MARFIL.blue, alpha=1),
            alignment=1,
            spaceAfter=SPACE_AFTER_SUBTITULO,
        ),
        "cover_tag": ParagraphStyle(
            name="mda_cover_tag",
            parent=base["Normal"],
            fontName=df,
            fontSize=14,
            leading=18,
            textColor=Color(1, 1, 1, alpha=0.88),
            alignment=1,
            spaceAfter=6,
        ),
        "intro_volume": ParagraphStyle(
            name="mda_intro_volume",
            parent=base["Heading1"],
            fontName=tf,
            fontSize=34,
            leading=40,
            textColor=ink,
            alignment=1,
            spaceAfter=10,
        ),
        "intro_sacred": ParagraphStyle(
            name="mda_intro_sacred",
            parent=base["BodyText"],
            fontName=bif,
            fontSize=18.0,
            leading=26,
            textColor=ink,
            alignment=1,
            spaceAfter=12,
        ),
        "intro_editorial": ParagraphStyle(
            name="mda_intro_editorial",
            parent=base["BodyText"],
            fontName=df,
            fontSize=14.5,
            leading=21,
            textColor=Color(0.28, 0.24, 0.30),
            alignment=1,
            spaceAfter=10,
        ),
        "intro_tag": ParagraphStyle(
            name="mda_intro_tag",
            parent=base["BodyText"],
            fontName=df,
            fontSize=15.5,
            leading=22,
            textColor=ink,
            alignment=1,
            spaceAfter=0,
        ),
        "heading": ParagraphStyle(
            name="mda_heading",
            parent=base["Heading2"],
            fontName=tf,
            fontSize=SIZE_TITULO,
            leading=LEADING_TITULO,
            textColor=Color(COLOR_TITULO_DORADO.red, COLOR_TITULO_DORADO.green, COLOR_TITULO_DORADO.blue, alpha=1),
            spaceAfter=SPACE_AFTER_TITULO,
        ),
        "body": ParagraphStyle(
            name="mda_body",
            parent=base["BodyText"],
            fontName=bf,
            fontSize=SIZE_TEXTO,
            leading=LEADING_TEXTO,
            textColor=ink,
            alignment=TA_LEFT,
            spaceAfter=SPACE_AFTER_PARRAFO,
        ),
        "affirm": ParagraphStyle(
            name="mda_affirm",
            parent=base["BodyText"],
            fontName=df,
            fontSize=15.0,
            leading=20,
            # Fuera del panel, sobre el fondo JPG (misma lógica que los títulos de sección)
            textColor=heading_bg,
            leftIndent=10,
            spaceAfter=10,
        ),
        "back": ParagraphStyle(
            name="mda_back",
            parent=base["BodyText"],
            fontName=bf,
            fontSize=15.0,
            leading=20,
            textColor=ink,
            alignment=1,
        ),
        "tiny": ParagraphStyle(
            name="mda_tiny",
            parent=base["Normal"],
            fontName=df,
            fontSize=SIZE_TEXTO_PEQUENO,
            leading=max(12, LEADING_TEXTO - 2),
            textColor=Color(COLOR_TEXTO_SECUNDARIO.red, COLOR_TEXTO_SECUNDARIO.green, COLOR_TEXTO_SECUNDARIO.blue, alpha=1),
            spaceAfter=4,
        ),
        "firma": ParagraphStyle(
            name="mda_firma",
            parent=base["Normal"],
            fontName=sf,
            fontSize=15.5,
            leading=21,
            textColor=Color(0.92, 0.78, 0.42),
            alignment=1,
            spaceAfter=12,
        ),
    }
    # Evitar warnings si <i> usa fuente sin itálica registrada con otro nombre
    styles["body"].fontName = bf
    styles["affirm"].fontName = df
    styles["firma"].fontName = sf

    styles["body_sh"] = ParagraphStyle(
        name="mda_body_sh",
        parent=styles["body"],
        textColor=Color(0, 0, 0, alpha=0.20),
    )
    styles["heading_sh"] = ParagraphStyle(
        name="mda_heading_sh",
        parent=styles["heading"],
        textColor=Color(0, 0, 0, alpha=0.30),
    )
    styles["affirm_panel"] = ParagraphStyle(
        name="mda_affirm_panel",
        parent=base["BodyText"],
        fontName=bif,
        fontSize=17.5,
        leading=26,
        textColor=ink,
        alignment=1,
        spaceAfter=0,
        leftIndent=0,
    )
    styles["affirm_panel_sh"] = ParagraphStyle(
        name="mda_affirm_panel_sh",
        parent=styles["affirm_panel"],
        textColor=Color(0, 0, 0, alpha=0.34),
    )
    styles["back_sh"] = ParagraphStyle(
        name="mda_back_sh",
        parent=styles["back"],
        textColor=Color(0, 0, 0, alpha=0.36),
    )
    styles["tiny_sh"] = ParagraphStyle(
        name="mda_tiny_sh",
        parent=styles["tiny"],
        textColor=Color(0, 0, 0, alpha=0.32),
    )
    styles["firma_sh"] = ParagraphStyle(
        name="mda_firma_sh",
        parent=styles["firma"],
        textColor=Color(0, 0, 0, alpha=0.35),
    )
    styles["cover_volume"] = ParagraphStyle(
        name="mda_cover_volume",
        parent=styles["title"],
        fontSize=SIZE_PORTADA_MAPA,
        leading=40,
        textColor=Color(COLOR_TITULO_DORADO.red, COLOR_TITULO_DORADO.green, COLOR_TITULO_DORADO.blue, alpha=1),
        alignment=1,
        spaceAfter=6,
    )
    styles["cover_name"] = ParagraphStyle(
        name="mda_cover_name",
        fontName=tf,
        fontSize=SIZE_PORTADA_NOMBRE,
        leading=36,
        textColor=Color(COLOR_TITULO_DORADO.red, COLOR_TITULO_DORADO.green, COLOR_TITULO_DORADO.blue, alpha=1),
        alignment=1,
        spaceAfter=8,
    )
    # Portada: texto más discreto que el mapa (jerarquía: imagen dominante).
    styles["cover_name_map_balance"] = ParagraphStyle(
        name="mda_cover_name_map_balance",
        parent=styles["cover_name"],
        fontSize=PREMIUM_COVER_NAME_FONT_SIZE,
        leading=PREMIUM_COVER_NAME_LEADING,
        spaceAfter=4,
    )
    styles["cover_sacred"] = ParagraphStyle(
        name="mda_cover_sacred",
        fontName=df,
        fontSize=16,
        leading=23,
        textColor=Color(0.98, 0.95, 0.90),
        alignment=1,
        spaceAfter=12,
    )
    styles["cover_birth"] = ParagraphStyle(
        name="mda_cover_birth",
        parent=styles["cover_sacred"],
        fontSize=SIZE_PORTADA_FECHA,
        leading=14,
        spaceAfter=10,
    )
    styles["cover_birth_map_balance"] = ParagraphStyle(
        name="mda_cover_birth_map_balance",
        parent=styles["cover_birth"],
        fontSize=PREMIUM_COVER_BIRTH_FONT_SIZE,
        leading=PREMIUM_COVER_BIRTH_LEADING,
        spaceAfter=4,
    )
    styles["impact"] = ParagraphStyle(
        name="mda_impact",
        fontName=impact_f,
        fontSize=SIZE_FRASE_DESTACADA,
        leading=LEADING_FRASE,
        textColor=Color(
            COLOR_TITULO_DORADO_SUAVE.red,
            COLOR_TITULO_DORADO_SUAVE.green,
            COLOR_TITULO_DORADO_SUAVE.blue,
            alpha=1,
        ),
        alignment=1,
        spaceBefore=SPACE_BEFORE_FRASE_DESTACADA,
        spaceAfter=SPACE_AFTER_FRASE_DESTACADA,
    )
    styles["giant"] = ParagraphStyle(
        name="mda_giant",
        fontName=impact_f,
        fontSize=34,
        leading=40,
        textColor=heading_bg,
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    styles["giant_left"] = ParagraphStyle(
        name="mda_giant_left",
        parent=styles["giant"],
        alignment=TA_LEFT,
        fontSize=28,
        leading=34,
    )
    styles["giant_panel"] = ParagraphStyle(
        name="mda_giant_panel",
        parent=styles["giant"],
        fontName=impact_f,
        fontSize=43,
        leading=50,
        textColor=ink,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    styles["quote_section_body"] = ParagraphStyle(
        name="mda_quote_section",
        parent=styles["body"],
        fontName=bif,
        fontSize=17.2,
        leading=25.6,
        textColor=ink,
        alignment=TA_CENTER,
        spaceAfter=12,
        leftIndent=8,
        rightIndent=8,
    )
    styles["section_title"] = ParagraphStyle(
        name="mda_section_title",
        parent=base["Heading2"],
        fontName=tf,
        fontSize=SIZE_TITULO,
        leading=LEADING_TITULO,
        textColor=Color(COLOR_TITULO_DORADO.red, COLOR_TITULO_DORADO.green, COLOR_TITULO_DORADO.blue, alpha=1),
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    styles["cover_name_panel"] = ParagraphStyle(
        name="mda_cover_name_panel",
        fontName=tf,
        fontSize=40,
        leading=46,
        textColor=ink,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    styles["body_climax"] = ParagraphStyle(
        name="mda_body_climax",
        parent=styles["body"],
        fontSize=17.8,
        leading=25.6,
    )
    styles["closing_firma_body"] = ParagraphStyle(
        name="mda_closing_firma_body",
        parent=styles["body_climax"],
        fontSize=SIZE_TEXTO,
        leading=LEADING_TEXTO,
        textColor=ink,
    )
    styles["numerologia_body"] = ParagraphStyle(
        name="mda_numerologia_body",
        parent=styles["body"],
        fontSize=SIZE_TEXTO,
        leading=LEADING_TEXTO,
    )
    styles["numerology_label"] = ParagraphStyle(
        name="mda_numerology_label",
        parent=styles["tiny"],
        fontName=df,
        fontSize=14.0,
        leading=18.2,
        textColor=Color(0.98, 0.96, 0.92),
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    styles["firma_panel"] = ParagraphStyle(
        name="mda_firma_panel",
        parent=styles["body"],
        fontName=bf,
        fontSize=SIZE_TEXTO,
        leading=LEADING_TEXTO,
        textColor=ink,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    styles["bleed"] = ParagraphStyle(
        name="mda_bleed",
        parent=styles["body"],
        fontSize=15.6,
        leading=23.4,
        leftIndent=0,
        spaceAfter=0,
        alignment=TA_LEFT,
    )
    styles["cover_editorial"] = ParagraphStyle(
        name="mda_cover_editorial",
        fontName=df,
        fontSize=13,
        leading=18,
        textColor=Color(0.92, 0.88, 0.82, alpha=0.94),
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    styles["body_panel"] = ParagraphStyle(
        name="mda_body_panel",
        parent=styles["body"],
        alignment=TA_LEFT,
        leading=26,
        spaceAfter=8,
        leftIndent=0,
        rightIndent=0,
    )
    # Capas *_sh: misma tipografía, tinta negra semitransparente (sombra del trazo únicamente).
    _shadow_alpha: list[tuple[str, float]] = [
        ("subtitle", 0.4),
        ("cover_tag", 0.38),
        ("intro_volume", 0.38),
        ("intro_sacred", 0.36),
        ("intro_editorial", 0.34),
        ("intro_tag", 0.36),
        ("section_title", 0.4),
        ("giant", 0.38),
        ("giant_left", 0.38),
        ("giant_panel", 0.38),
        ("quote_section_body", 0.35),
        ("body_climax", 0.37),
        ("closing_firma_body", 0.35),
        ("numerologia_body", 0.36),
        ("numerology_label", 0.42),
        ("firma_panel", 0.36),
        ("bleed", 0.38),
        ("cover_editorial", 0.32),
        ("body_panel", 0.38),
        ("cover_name_map_balance", 0.42),
        ("cover_birth_map_balance", 0.38),
        ("impact", 0.38),
    ]
    for key, alpha in _shadow_alpha:
        if key in styles and f"{key}_sh" not in styles:
            styles[f"{key}_sh"] = ParagraphStyle(
                name=f"mda_{key}_sh",
                parent=styles[key],
                textColor=Color(0, 0, 0, alpha=alpha),
            )

    # Reduce saltos feos (viudas/huérfanas) y compacta ligeramente para evitar páginas con una línea.
    for key in (
        "body",
        "bleed",
        "quote_section_body",
        "numerologia_body",
        "closing_firma_body",
        "firma_panel",
        "body_climax",
    ):
        if key in styles:
            styles[key].allowWidows = 0
            styles[key].allowOrphans = 0
            styles[key].leading = max(styles[key].fontSize + 3.2, styles[key].leading - 1.2)
    return styles


def _seed_for_sign(sign: str) -> int:
    h = 0
    for ch in sign:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def draw_programmatic_background(canvas, sign_key: str, seed: int) -> None:
    """Fallback si no hay JPG: constelación y destellos deterministas por semilla de identidad."""
    theme = SIGN_THEMES.get(
        sign_key,
        {"accent": (0.22, 0.20, 0.30), "glow": (0.75, 0.68, 0.88)},
    )
    accent = theme["accent"]
    glow = theme["glow"]
    rnd = random.Random(seed ^ _seed_for_sign(sign_key))

    canvas.setFillColorRGB(*accent)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    canvas.setFillColorRGB(glow[0], glow[1], glow[2], alpha=0.22)
    canvas.circle(PAGE_W * 0.78, PAGE_H * 0.72, 220, stroke=0, fill=1)
    canvas.setFillColorRGB(0.05, 0.04, 0.12, alpha=0.35)
    canvas.circle(PAGE_W * 0.18, PAGE_H * 0.25, 180, stroke=0, fill=1)

    canvas.setFillColorRGB(1, 1, 1, alpha=0.12)
    for _ in range(110):
        x = rnd.uniform(0, PAGE_W)
        y = rnd.uniform(0, PAGE_H)
        r = rnd.uniform(0.6, 1.6)
        canvas.circle(x, y, r, stroke=0, fill=1)

    canvas.setFillColorRGB(0.92, 0.82, 0.45, alpha=0.35)
    for _ in range(28):
        x = rnd.uniform(0, PAGE_W)
        y = rnd.uniform(0, PAGE_H)
        canvas.circle(x, y, rnd.uniform(0.8, 2.4), stroke=0, fill=1)

    canvas.setStrokeColorRGB(1, 1, 1, alpha=0.06)
    canvas.setLineWidth(0.4)
    for i in range(4):
        cx = PAGE_W * (0.2 + 0.2 * i)
        cy = PAGE_H * 0.55
        r = 80 + i * 40
        canvas.circle(cx, cy, r, stroke=1, fill=0)


def draw_full_page_background(canvas, doc, profile: SoulProfile) -> None:
    """
    Dibuja en canvas el fondo por signo (JPG/PNG a pantalla completa si existe),
    velo para legibilidad y polvo de estrellas sembrado por identidad.
    """
    _ = doc
    sign_key = profile.signo
    seed = profile.seed
    canvas.saveState()
    bg_path = resolve_sign_background(sign_key)
    used_jpg = False
    if bg_path and bg_path.exists():
        try:
            ir = ImageReader(str(bg_path))
            iw, ih = ir.getSize()
            if iw > 0 and ih > 0:
                scale = max(PAGE_W / float(iw), PAGE_H / float(ih))
                w = iw * scale
                h = ih * scale
                x = (PAGE_W - w) / 2.0
                y = (PAGE_H - h) / 2.0
                canvas.drawImage(str(bg_path), x, y, width=w, height=h, mask="auto")
                used_jpg = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fondo JPG no usable (%s): %s", bg_path, exc)

    if not used_jpg:
        draw_programmatic_background(canvas, sign_key, seed)

    canvas.setFillColorRGB(0.02, 0.02, 0.06, alpha=SIGN_BACKGROUND_VEIL_ALPHA)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    rnd = random.Random(seed)
    canvas.setFillColorRGB(1, 1, 1, alpha=0.05)
    for _ in range(72):
        x = rnd.uniform(0, PAGE_W)
        y = rnd.uniform(0, PAGE_H)
        r = rnd.uniform(0.4, 1.2)
        canvas.circle(x, y, r, stroke=0, fill=1)

    canvas.restoreState()


def _sharp_stamp(path: Optional[Path], max_side: float) -> Flowable:
    """
    PNG nítido para columnas (sin velos oscuros encima del arte).
    Si falta archivo o falla la decodificación, fallback a marco GlowStamp.
    """
    if path is None or not path.exists():
        return GlowStampFlowable(path, max_side)
    try:
        return RLImage(
            str(path.resolve()),
            width=max_side,
            height=max_side,
            kind="proportional",
            mask="auto",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Imagen no cargada (%s): %s", path, exc)
        return GlowStampFlowable(path, max_side)


def _make_stamp(path: Optional[Path], max_side: float = STAMP_DEFAULT_PT) -> Flowable:
    """Alias: sellos en el PDF usan imagen nítida (legible)."""
    return _sharp_stamp(path, max_side)


def _stamp_or_digit(path: Optional[Path], digit: int, max_side: float) -> Flowable:
    """PNG 1.png…9.png (raíz o carpeta numerologia/numeros); si no, glifo vectorial."""
    p = path
    if p is None or not p.exists():
        p = image_assets.resolve_numerology_digit_png(digit)
    if p is not None and p.exists():
        # Seguridad: evita desfases visuales (ej. pedir 4 y cargar archivo de 5).
        stem = p.stem.strip().lower()
        if stem != str(digit):
            logger.warning(
                "Descartando imagen de numerología por posible desfase (%s para dígito %s)",
                p,
                digit,
            )
            p = None
    if p is not None and p.exists():
        try:
            return RLImage(
                str(p.resolve()),
                width=max_side,
                height=max_side,
                kind="bound",
                mask="auto",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("PNG numerología %s no usable: %s", p, exc)
    return DigitGlyphFlowable(digit, max_side)


def _stamp_or_chinese(path: Optional[Path], animal_label_es: str, max_side: float) -> Flowable:
    """PNG del animal chino si existe; si no, glifo tipográfico con el nombre."""
    if path is not None and path.exists():
        return _sharp_stamp(path, max_side)
    return ChineseGlyphFlowable(animal_label_es, max_side)


def _cover_stamp(path: Optional[Path], max_side: float) -> Flowable:
    """Portada: PNG nítido (sin glow) para título visual y logo."""
    if path is None or not path.exists():
        return Spacer(1, 1)
    try:
        ap = path.resolve()
        return RLImage(
            str(ap),
            width=max_side,
            height=max_side,
            kind="proportional",
            mask="auto",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Portada imagen no cargada (%s): %s", path, exc)
        return Spacer(1, 1)


def _flatten_panel_cell(cell: Flowable, styles: dict[str, ParagraphStyle]) -> Flowable:
    """
    Table / LongTable: conserva ShadowParagraph para mantener sombra de texto sobre el panel.
    (El fondo semitransparente del panel es independiente; la sombra va solo al trazo.)
    """
    if isinstance(cell, ShadowParagraph):
        return cell
    return cell


def _centered_row(inner: Flowable, frame_width: float) -> Table:
    """Centra un flowable (p. ej. panel al 92 %) dentro del ancho útil del marco."""
    return Table(
        [[inner]],
        colWidths=[frame_width],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def _title_centered_panel(
    title_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    *,
    panel_width_mul: float = 0.88,
    panel_alpha: Optional[float] = None,
) -> Flowable:
    """Título de sección centrado dentro del velo alfa (75 % editorial)."""
    pa = TEXT_PANEL_ALPHA if panel_alpha is None else float(panel_alpha)
    inner = _panel_table(
        [_text_flow(title_html, styles, "section_title")],
        styles,
        inner_width * panel_width_mul,
        panel_alpha=pa,
    )
    return _centered_row(inner, inner_width)


def _panel_table(
    inner: Sequence[Flowable],
    styles: dict[str, ParagraphStyle],
    full_width: float,
    *,
    panel_alpha: Optional[float] = None,
) -> Flowable:
    """
    Texto largo: párrafo con fondo semitransparente (parte entre páginas).
    panel_alpha: si se indica (0.3–0.7), alterna el velo del panel sin tocar el texto.
    """
    cell: Flowable = inner[0] if len(inner) == 1 else list(inner)  # type: ignore[assignment]
    cell = _flatten_panel_cell(cell, styles)
    compact_w = full_width * 0.90 if full_width > 520.0 else full_width
    inner_w = max(compact_w - 2 * TEXT_PANEL_PAD, 120.0)
    alpha = _ACTIVE_PANEL_ALPHA if panel_alpha is None else float(panel_alpha)
    bg = Color(*_ACTIVE_PANEL_RGB, alpha=alpha)
    tbl = LongTable([[cell]], colWidths=[inner_w], repeatRows=0)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), CAJA_STROKE_WIDTH, Color(COLOR_BORDE_CAJA.red, COLOR_BORDE_CAJA.green, COLOR_BORDE_CAJA.blue, alpha=BORDE_ALPHA)),
                ("LEFTPADDING", (0, 0), (-1, -1), CAJA_PADDING_X),
                ("RIGHTPADDING", (0, 0), (-1, -1), CAJA_PADDING_X),
                ("TOPPADDING", (0, 0), (-1, -1), CAJA_PADDING_Y),
                ("BOTTOMPADDING", (0, 0), (-1, -1), CAJA_PADDING_Y),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROUNDEDCORNERS", [TEXT_PANEL_RADIUS]),
            ]
        )
    )
    return tbl


def _panel_table_multi_row(
    body_html: str,
    styles: dict[str, ParagraphStyle],
    full_width: float,
    *,
    panel_alpha: Optional[float] = None,
    style_key: str = "body",
) -> LongTable:
    """
    Varias filas de párrafo separadas por <br/><br/> para que LongTable pueda partir entre páginas.
    Un solo Paragraph gigante en una celda no siempre se fragmenta bien dentro de Table.
    """
    raw_parts = [p.strip() for p in body_html.split("<br/><br/>") if p.strip()]
    # Evita filas ultra-cortas que suelen provocar páginas con una sola línea al partir.
    parts: list[str] = []
    carry = ""
    for part in raw_parts:
        wc = len(re.findall(r"\S+", re.sub(r"<[^>]+>", " ", part)))
        if wc <= 9:
            # No usar str.strip() aquí: recorta por caracteres y puede romper tags como <b>...</b>.
            carry = f"{carry}<br/><br/>{part}" if carry else part
            continue
        if carry:
            parts.append(f"{carry}<br/><br/>{part}")
            carry = ""
        else:
            parts.append(part)
    if carry:
        if parts:
            parts[-1] = f"{parts[-1]}<br/><br/>{carry}"
        else:
            parts = [carry]
    if not parts:
        parts = [body_html.strip() if body_html.strip() else " "]
    compact_w = full_width * 0.90 if full_width > 520.0 else full_width
    inner_w = max(compact_w - 2 * TEXT_PANEL_PAD, 120.0)
    rows: List[List[Flowable]] = [[_text_flow(p, styles, style_key)] for p in parts]
    alpha = _ACTIVE_PANEL_ALPHA if panel_alpha is None else float(panel_alpha)
    bg = Color(*_ACTIVE_PANEL_RGB, alpha=alpha)
    tbl = LongTable(rows, colWidths=[inner_w], repeatRows=0)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), CAJA_STROKE_WIDTH, Color(COLOR_BORDE_CAJA.red, COLOR_BORDE_CAJA.green, COLOR_BORDE_CAJA.blue, alpha=BORDE_ALPHA)),
                ("LEFTPADDING", (0, 0), (-1, -1), CAJA_PADDING_X),
                ("RIGHTPADDING", (0, 0), (-1, -1), CAJA_PADDING_X),
                ("TOPPADDING", (0, 0), (-1, 0), CAJA_PADDING_Y),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), max(12, CAJA_PADDING_Y - 2)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROUNDEDCORNERS", [TEXT_PANEL_RADIUS]),
            ]
        )
    )
    return tbl


def _stamp_side_for_vertical_stack(
    n_images: int, base_side: float, budget_pt: float = STAMP_BUDGET_PT
) -> float:
    """Evita que 2–3 PNG apilados superen la altura útil del marco (LayoutError)."""
    n = max(1, n_images)
    gap = 10.0
    return min(base_side, max(96.0, (budget_pt - (n - 1) * gap) / float(n)))


def _section_img_left_text_right(
    title_html: str,
    body_html: str,
    image_paths: Sequence[Optional[Path]],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    max_side: float,
    *,
    panel_alpha: Optional[float] = None,
    bleed: bool = False,
    title_centered_panel: bool = False,
    stamp_lead_spacer: float = 0.0,
) -> List[Flowable]:
    """
    Sellos a la izquierda arriba; cuerpo a ancho completo debajo.
    (Una sola Table [imagen | texto] no puede partirse entre páginas y recortaba párrafos largos.)
    """
    if title_centered_panel:
        title = _title_centered_panel(title_html, styles, inner_width, panel_alpha=panel_alpha)
    else:
        title = _hp(title_html, styles)
    gap = 12.0
    n_paths = max(1, len(image_paths))
    ms = min(
        _stamp_side_for_vertical_stack(n_paths, max_side, budget_pt=STAMP_BUDGET_PT),
        inner_width * STAMP_MAX_WIDTH_FRAC,
    )
    img_col_w = min(ms + 44.0, inner_width * (STAMP_MAX_WIDTH_FRAC + 0.04))
    left_cells: List[Flowable] = []
    if stamp_lead_spacer > 0:
        left_cells.append(Spacer(1, stamp_lead_spacer))
    if not image_paths:
        left_cells.append(Spacer(1, 1))
    else:
        for p in image_paths:
            if p is None:
                continue
            left_cells.append(_sharp_stamp(p, ms))
            left_cells.append(Spacer(1, 6))
    left_stack = Table([[c] for c in left_cells], colWidths=[img_col_w])
    left_stack.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    rest_w = inner_width - img_col_w - gap
    image_row = Table(
        [[left_stack, Spacer(max(rest_w, 24.0), 1)]],
        colWidths=[img_col_w, rest_w],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 2),
            ]
        ),
    )
    pa = panel_alpha if panel_alpha is not None else TEXT_PANEL_ALPHA
    body_style = "bleed" if bleed else "body"
    body = _panel_table_multi_row(
        body_html, styles, inner_width, panel_alpha=pa, style_key=body_style
    )
    head = KeepTogether([title, Spacer(1, 6), image_row, Spacer(1, 8)])
    return [head, body, Spacer(1, 4)]


def _section_title_stamp_fullwidth_panel(
    title_html: str,
    body_html: str,
    stamp_path: Optional[Path],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    stamp_side: float,
    *,
    panel_alpha: Optional[float] = None,
    top_spacer_before_title: float = 0.0,
    title_in_panel: bool = True,
) -> List[Flowable]:
    """
    Título + sello centrado + panel de texto a ancho completo.
    Para secciones con mucho texto (p. ej. código del nombre): una Table de dos columnas
    no puede partir la fila entre páginas; este layout deja que LongTable parta el panel.
    """
    pa = TEXT_PANEL_ALPHA if panel_alpha is None else float(panel_alpha)
    if stamp_path is None:
        title = (
            _title_centered_panel(title_html, styles, inner_width, panel_alpha=pa)
            if title_in_panel
            else _hp(title_html, styles)
        )
        body = _panel_table_multi_row(body_html, styles, inner_width, panel_alpha=pa)
        out: List[Flowable] = []
        if top_spacer_before_title > 0:
            out.append(Spacer(1, top_spacer_before_title))
        return out + [KeepTogether([title, Spacer(1, 8)]), body, Spacer(1, 4)]
    if title_in_panel:
        title = _title_centered_panel(title_html, styles, inner_width, panel_alpha=pa)
    else:
        title = _hp(title_html, styles)
    ss = min(float(stamp_side), inner_width * 0.42, 380.0)
    stamp = _sharp_stamp(stamp_path, ss)
    top = Table(
        [[stamp]],
        colWidths=[inner_width],
        style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]),
    )
    body = _panel_table_multi_row(body_html, styles, inner_width, panel_alpha=pa)
    out: List[Flowable] = []
    if top_spacer_before_title > 0:
        out.append(Spacer(1, top_spacer_before_title))
    out.extend([KeepTogether([title, Spacer(1, 8), top, Spacer(1, 8)]), body, Spacer(1, 4)])
    return out


def _section_stamp_body_fullwidth_panel(
    body_html: str,
    stamp_path: Optional[Path],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    stamp_side: float,
    *,
    panel_alpha: Optional[float] = None,
) -> List[Flowable]:
    """Sello centrado + panel de texto, sin título (sigue a la página donde va solo el título en panel)."""
    pa = TEXT_PANEL_ALPHA if panel_alpha is None else float(panel_alpha)
    if stamp_path is None:
        return [
            _panel_table_multi_row(body_html, styles, inner_width, panel_alpha=pa),
            Spacer(1, 4),
        ]
    ss = min(float(stamp_side), inner_width * 0.42, 380.0)
    stamp = _sharp_stamp(stamp_path, ss)
    top = Table(
        [[stamp]],
        colWidths=[inner_width],
        style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]),
    )
    body = _panel_table_multi_row(body_html, styles, inner_width, panel_alpha=pa)
    return [top, Spacer(1, 8), body, Spacer(1, 4)]


def _trial_codigo_mapa_left_body_right(
    title_html: str,
    body_html: str,
    map_path: Optional[Path],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    hero: float,
    panel_alpha: float,
) -> List[Flowable]:
    """
    Prueba: título + mapa a la izquierda del cuerpo en la misma sección.
    Usa ImageAndFlowables (ReportLab) para que el texto pueda partir páginas sin LayoutError.
    """
    pa = float(panel_alpha)
    title = _title_centered_panel(title_html, styles, inner_width, panel_alpha=pa)
    img_col = min(inner_width * 0.32, 260.0)
    ms = min(max(img_col - 24.0, 112.0), hero * 0.48, 228.0, (PAGE_H - 2 * 42) * 0.38)
    text_budget = max(inner_width - ms - 36, 200.0)
    body = _panel_table_multi_row(body_html, styles, text_budget, panel_alpha=pa, style_key="body")
    if map_path is not None and map_path.exists():
        map_img = RLImage(
            str(map_path.resolve()),
            width=ms,
            height=ms,
            kind="bound",
            mask="auto",
        )
        combo = ImageAndFlowables(
            map_img,
            [body],
            imageSide="left",
            imageLeftPadding=4,
            imageRightPadding=16,
            imageTopPadding=2,
            imageBottomPadding=6,
        )
    else:
        combo = body
    return [KeepTogether([title, Spacer(1, 8), combo]), Spacer(1, 6)]


def _section_img_right_text_left(
    title_html: str,
    body_html: str,
    image_paths: Sequence[Optional[Path]],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    max_side: float,
    *,
    panel_alpha: Optional[float] = None,
    bleed: bool = False,
    title_centered_panel: bool = False,
    stamp_lead_spacer: float = 0.0,
) -> List[Flowable]:
    """Sellos a la derecha arriba; cuerpo a ancho completo debajo (evita recorte por Table de dos columnas)."""
    if title_centered_panel:
        title = _title_centered_panel(title_html, styles, inner_width, panel_alpha=panel_alpha)
    else:
        title = _hp(title_html, styles)
    gap = 12.0
    n_paths = max(1, len(image_paths))
    ms = min(
        _stamp_side_for_vertical_stack(n_paths, max_side, budget_pt=STAMP_BUDGET_PT),
        inner_width * STAMP_MAX_WIDTH_FRAC,
    )
    img_col_w = min(ms + 44.0, inner_width * (STAMP_MAX_WIDTH_FRAC + 0.04))
    img_cells: List[Flowable] = []
    if stamp_lead_spacer > 0:
        img_cells.append(Spacer(1, stamp_lead_spacer))
    if not image_paths:
        img_cells.append(Spacer(1, 1))
    else:
        for pth in image_paths:
            if pth is None:
                continue
            img_cells.append(_sharp_stamp(pth, ms))
            img_cells.append(Spacer(1, 6))
    right_stack = Table([[c] for c in img_cells], colWidths=[img_col_w])
    right_stack.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    rest_w = inner_width - img_col_w - gap
    image_row = Table(
        [[Spacer(max(rest_w, 24.0), 1), right_stack]],
        colWidths=[rest_w, img_col_w],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("RIGHTPADDING", (1, 0), (1, 0), 2),
            ]
        ),
    )
    pa = panel_alpha if panel_alpha is not None else TEXT_PANEL_ALPHA
    body_style = "bleed" if bleed else "body"
    body = _panel_table_multi_row(
        body_html, styles, inner_width, panel_alpha=pa, style_key=body_style
    )
    head = KeepTogether([title, Spacer(1, 6), image_row, Spacer(1, 8)])
    return [head, body, Spacer(1, 4)]


def _section_text_top_image_bottom(
    title_html: str,
    body_html: str,
    image_paths: Sequence[Optional[Path]],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    max_side: float,
    *,
    panel_alpha: Optional[float] = None,
    title_centered_panel: bool = False,
    stamp_lead_spacer: float = 0.0,
    body_in_panel: bool = True,
) -> List[Flowable]:
    """Layout B: título + cuerpo a ancho completo; sellos grandes centrados debajo."""
    if title_centered_panel:
        title = _title_centered_panel(title_html, styles, inner_width, panel_alpha=panel_alpha)
    else:
        title = _hp(title_html, styles)
    pa = panel_alpha if panel_alpha is not None else TEXT_PANEL_ALPHA
    # body_in_panel=False solo cambia el estilo (más "directo"), no quita el fondo del panel.
    body_style = "body" if body_in_panel else "bleed"
    body = _panel_table_multi_row(
        body_html, styles, inner_width, panel_alpha=pa, style_key=body_style
    )
    cells = [p for p in image_paths if p is not None]
    if not cells:
        return [title, Spacer(1, 6), body, Spacer(1, 4)]
    n_paths = max(1, len(cells))
    ms = min(
        _stamp_side_for_vertical_stack(n_paths, max_side * 1.1, budget_pt=STAMP_BUDGET_PT),
        inner_width * STAMP_MAX_WIDTH_FRAC,
    )
    ms = max(ms, inner_width * HERO_FRAC_MIN * 0.95)
    row_cells = [_sharp_stamp(p, ms) for p in cells]
    colw = inner_width / float(len(row_cells))
    stamp_row = Table(
        [row_cells],
        colWidths=[colw] * len(row_cells),
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )
    # Colocamos imagen antes del cuerpo para evitar páginas con imagen huérfana al final.
    out: List[Flowable] = [KeepTogether([title, Spacer(1, 6), stamp_row, Spacer(1, 6)]), body]
    if stamp_lead_spacer > 0:
        out.insert(2, Spacer(1, stamp_lead_spacer))
    out.append(Spacer(1, 4))
    return out


def _section_quote_centered_layout(
    title_html: str,
    body_html: str,
    image_paths: Sequence[Optional[Path]],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    max_side: float,
    *,
    panel_alpha: Optional[float] = None,
    title_centered_panel: bool = False,
    stamp_lead_spacer: float = 0.0,
) -> List[Flowable]:
    """Layout C: cita editorial centrada; sellos más contenidos al pie."""
    if title_centered_panel:
        title = _title_centered_panel(title_html, styles, inner_width, panel_alpha=panel_alpha)
    else:
        title = _hp(title_html, styles)
    pa = panel_alpha if panel_alpha is not None else TEXT_PANEL_ALPHA
    body = _panel_table_multi_row(
        body_html, styles, inner_width, panel_alpha=pa, style_key="quote_section_body"
    )
    cells = [p for p in image_paths if p is not None]
    out: List[Flowable] = [KeepTogether([title, Spacer(1, 7)]), body]
    if not cells:
        out.append(Spacer(1, 4))
        return out
    if stamp_lead_spacer > 0:
        out.append(Spacer(1, stamp_lead_spacer))
    n_paths = max(1, len(cells))
    ms = min(
        _stamp_side_for_vertical_stack(n_paths, max_side * 0.92, budget_pt=STAMP_BUDGET_PT),
        inner_width * 0.38,
    )
    row_cells = [_sharp_stamp(p, ms) for p in cells]
    colw = inner_width / float(len(row_cells))
    stamp_row = Table(
        [row_cells],
        colWidths=[colw] * len(row_cells),
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        ),
    )
    out.extend([Spacer(1, 10), stamp_row, Spacer(1, 4)])
    return out


def _phrase_stamp_beside_text(
    title_html: str | None,
    body_html: str,
    stamp_path: Optional[Path],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    stamp_pt: float = 168.0,
    *,
    body_style_key: str = "giant_left",
    title_centered_panel: bool = False,
    no_stamp: bool = False,
) -> List[Flowable]:
    """Imagen y texto en fila, o solo paneles centrados (sin sello del signo si no_stamp)."""
    pa = float(TEXT_PANEL_ALPHA)
    if no_stamp or stamp_path is None:
        out: List[Flowable] = []
        if title_html:
            if title_centered_panel:
                out.append(_title_centered_panel(title_html, styles, inner_width, panel_alpha=pa))
            else:
                out.append(_hp(title_html, styles))
            out.append(Spacer(1, 12))
        st_key = "giant_panel" if body_style_key in ("giant_left", "giant") else body_style_key
        body_flow = _panel_table_multi_row(
            body_html, styles, inner_width * 0.92, panel_alpha=pa, style_key=st_key
        )
        out.append(_centered_row(body_flow, inner_width))
        out.append(Spacer(1, 8))
        return out
    gap = 16.0
    col_img = min(float(stamp_pt) + 32.0, inner_width * 0.36)
    rest_w = inner_width - col_img - gap
    img = _sharp_stamp(stamp_path, min(stamp_pt, col_img - 8.0))
    image_row = Table(
        [[img, Spacer(max(rest_w, 24.0), 1)]],
        colWidths=[col_img, rest_w],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        ),
    )
    st_key = "giant_panel" if body_style_key in ("giant_left", "giant") else body_style_key
    txt_panel = _panel_table_multi_row(
        body_html, styles, inner_width * 0.92, panel_alpha=pa, style_key=st_key
    )
    out: List[Flowable] = []
    if title_html:
        if title_centered_panel:
            out.append(_title_centered_panel(title_html, styles, inner_width, panel_alpha=pa))
        else:
            out.append(_hp(title_html, styles))
        out.append(Spacer(1, 8))
    out.append(image_row)
    out.append(Spacer(1, 10))
    out.append(_centered_row(txt_panel, inner_width))
    out.append(Spacer(1, 6))
    return out


def _layout_una_pausa(
    profile: SoulProfile,
    narrative: object,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
) -> List[Flowable]:
    """Una pausa: página tipo cita — tipografía centrada, más aire."""
    pa = float(TEXT_PANEL_ALPHA)
    title_html = "<b>Una pausa</b><br/><i>Respira esta verdad</i>"
    impact_html = f"<b>{profile.nombre}</b>, irrepetible no es ego: es precisión."
    return [
        _title_centered_panel(title_html, styles, inner_width, panel_alpha=pa),
        Spacer(1, 16),
        _centered_row(
            _panel_table_multi_row(
                narrative.section_respira,
                styles,
                inner_width * 0.88,
                panel_alpha=pa,
                style_key="quote_section_body",
            ),
            inner_width,
        ),
        Spacer(1, 20),
        _centered_row(
            _panel_table(
                [_text_flow(impact_html, styles, "giant_panel")],
                styles,
                inner_width * 0.92,
                panel_alpha=pa,
            ),
            inner_width,
        ),
        Spacer(1, 10),
    ]


def _layout_wow_page(
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    wow_html: str,
    *,
    panel_alpha: Optional[float] = None,
) -> List[Flowable]:
    """Página de impacto: fondo + texto grande centrado."""
    pa = float(TEXT_PANEL_ALPHA if panel_alpha is None else panel_alpha)
    return [
        Spacer(1, 20),
        _centered_row(
            _panel_table_multi_row(
                wow_html,
                styles,
                inner_width * 0.84,
                panel_alpha=pa,
                style_key="giant",
            ),
            inner_width,
        ),
        Spacer(1, 10),
    ]


def _cover_first_page_only(
    profile: SoulProfile,
    inner_w: float,
    usable_h: float,
    styles: dict[str, ParagraphStyle],
    mapa_title_p: Optional[Path],
    logo_p: Optional[Path],
) -> List[Flowable]:
    """
    Portada: mapa grande, nombre y apellidos, fecha, logo abajo a la derecha (misma página).
    El hueco entre mapa y texto empuja el bloque inferior hacia la base de la página.
    """
    lw = float(COVER_LOGO_CORNER_PT)
    ap = profile.apellidos.strip()
    if ap:
        name_html = f"<b>{profile.nombre_pila}</b><br/><b>{ap}</b>"
    else:
        name_html = f"<b>{profile.nombre}</b>"
    nac_es = long_birth_date(profile.fecha)
    pw = inner_w * 0.88
    col_in = max(pw - 2 * TEXT_PANEL_PAD, 120.0)
    name_f = _text_flow(name_html, styles, "cover_name_map_balance")
    birth_f = _text_flow(nac_es, styles, "cover_birth_map_balance")
    name_stack = Table(
        [[name_f], [Spacer(1, PREMIUM_COVER_NAME_SPACER_AFTER)], [birth_f]],
        colWidths=[col_in],
    )
    name_stack.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    if PREMIUM_COVER_USE_TEXT_ONLY_BLOCK:
        name_panel = _centered_row(name_stack, inner_w)
    else:
        name_panel = _centered_row(
            _panel_table(
                [name_stack],
                styles,
                pw,
                panel_alpha=float(PREMIUM_COVER_NAME_DATE_PANEL_ALPHA),
            ),
            inner_w,
        )
    logo_cell = _cover_stamp(logo_p, lw) if logo_p else Spacer(1, 1)
    logo_row = Table(
        [[Spacer(1, 1), logo_cell]],
        colWidths=[inner_w - lw - 20, lw + 20],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    gap_map_text = min(
        float(COVER_GAP_MAP_TO_TEXT_MAX),
        max(float(COVER_GAP_MAP_TO_TEXT_MIN), usable_h * 0.048),
    )
    gap_name_logo = 10.0
    bottom_tail = 4.0
    if PREMIUM_COVER_USE_TEXT_ONLY_BLOCK:
        footer_h = 96.0 + gap_name_logo + lw + bottom_tail
    else:
        footer_h = 118.0 + 2 * TEXT_PANEL_PAD + gap_name_logo + lw + bottom_tail
    head_room = 4.0
    mapa_max = min(
        float(COVER_TITLE_IMAGE_MAX_PT),
        inner_w * 1.3,
        usable_h - head_room - gap_map_text - footer_h,
    )
    mapa_max = max(200.0, float(mapa_max))
    mapa_cell = _cover_stamp(mapa_title_p, mapa_max) if mapa_title_p else Spacer(1, 24)
    return [
        Spacer(1, 2),
        Table(
            [[mapa_cell]],
            colWidths=[inner_w],
            style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]),
        ),
        Spacer(1, gap_map_text),
        name_panel,
        Spacer(1, gap_name_logo),
        logo_row,
        Spacer(1, bottom_tail),
    ]


def _hero_one_image_layout(
    idx: int,
    title_html: str,
    body_html: str,
    stamp_path: Optional[Path],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    hero: float,
    panel_alpha: float,
    *,
    title_centered_panel: bool = False,
    stamp_scale: float = 1.0,
    stamp_lead_spacer: float = 0.0,
) -> List[Flowable]:
    """Un sello + texto con ritmo A/B/C: alterna sangre, asimetría y panel editorial."""
    if stamp_path is None:
        if title_centered_panel:
            title = _title_centered_panel(
                title_html, styles, inner_width, panel_alpha=panel_alpha
            )
        else:
            title = _hp(title_html, styles)
        body = _centered_row(
            _panel_table_multi_row(
                body_html, styles, inner_width, panel_alpha=panel_alpha
            ),
            inner_width,
        )
        return [title, Spacer(1, 10), body, Spacer(1, 8)]
    scaled = min(
        hero * max(1.0, stamp_scale),
        inner_width * STAMP_MAX_WIDTH_FRAC,
    )
    paths: List[Optional[Path]] = [stamp_path] if stamp_path is not None else []
    lk = pick_section_layout(idx)
    if lk == SectionLayout.LAYOUT_A:
        return _section_img_left_text_right(
            title_html,
            body_html,
            paths,
            styles,
            inner_width,
            scaled,
            panel_alpha=panel_alpha,
            bleed=False,
            title_centered_panel=title_centered_panel,
            stamp_lead_spacer=stamp_lead_spacer,
        )
    if lk == SectionLayout.LAYOUT_B:
        return _section_img_right_text_left(
            title_html,
            body_html,
            paths,
            styles,
            inner_width,
            scaled,
            panel_alpha=panel_alpha,
            bleed=False,
            title_centered_panel=title_centered_panel,
            stamp_lead_spacer=stamp_lead_spacer,
        )
    return _section_quote_centered_layout(
        title_html,
        body_html,
        paths,
        styles,
        inner_width,
        scaled,
        panel_alpha=panel_alpha,
        title_centered_panel=title_centered_panel,
        stamp_lead_spacer=stamp_lead_spacer,
    )


def _section_left_flowables_right_panel(
    title_html: str,
    body_html: str,
    left_column: Flowable,
    left_width: float,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    *,
    panel_alpha: Optional[float] = None,
    bleed: bool = False,
) -> List[Flowable]:
    """Columna izquierda arriba; cuerpo a ancho completo debajo (evita recorte en fila de dos columnas)."""
    title = _hp(title_html, styles)
    gap = 12.0
    rest_w = inner_width - left_width - gap
    head = Table(
        [[left_column, Spacer(max(rest_w, 24.0), 1)]],
        colWidths=[left_width, rest_w],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 2),
            ]
        ),
    )
    pa = panel_alpha if panel_alpha is not None else TEXT_PANEL_ALPHA
    body_style = "bleed" if bleed else "body"
    body = _panel_table_multi_row(
        body_html, styles, inner_width, panel_alpha=pa, style_key=body_style
    )
    return [title, Spacer(1, 10), head, Spacer(1, 12), body, Spacer(1, 8)]


def _giant_phrase_with_image_left(
    body_html: str,
    stamp_path: Optional[Path],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    max_side: float,
) -> List[Flowable]:
    gap = 12.0
    img_col_w = min(max_side + 28.0, inner_width * 0.38)
    left = Table(
        [[_sharp_stamp(stamp_path, max_side)]],
        colWidths=[img_col_w],
        style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]),
    )
    right_w = inner_width - img_col_w - gap
    off = right_w * 0.04
    tbl = Table(
        [[_text_flow(body_html, styles, "giant")]],
        colWidths=[right_w * 0.92],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), off),
                ("TOPPADDING", (0, 0), (-1, -1), 40),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 36),
            ]
        ),
    )
    row = Table([[left, tbl]], colWidths=[img_col_w, right_w])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return [row]


def _hero_stamp_layout(
    mode: int,
    title_html: str,
    body_html: str,
    stamp_path: Optional[Path],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    max_side: float,
    *,
    panel_alpha: Optional[float] = None,
) -> List[Flowable]:
    """Título + sello + panel (alpha opcional)."""
    _ = mode
    title = _hp(title_html, styles)
    body = _sp(body_html, styles, "body", "body_sh")
    img = GlowStampFlowable(stamp_path, max_side)
    align = ("LEFT", "CENTER", "RIGHT")[mode % 3]
    top = Table([[img]], colWidths=[inner_width])
    top.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), align)]))
    pw = inner_width * 0.96
    bot = _panel_table([body], styles, pw, panel_alpha=panel_alpha)
    return [
        title,
        Spacer(1, 10),
        top,
        Spacer(1, 11),
        bot,
        Spacer(1, 10),
    ]


def _hero_bleed_layout(
    mode: int,
    title_html: str,
    body_html: str,
    stamp_path: Optional[Path],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    max_side: float,
) -> List[Flowable]:
    """Título + sello + texto a sangre (sin caja), sobre el fondo del signo."""
    _ = mode
    title = _hp(title_html, styles)
    img = GlowStampFlowable(stamp_path, max_side)
    align = ("LEFT", "CENTER", "RIGHT")[mode % 3]
    top = Table([[img]], colWidths=[inner_width])
    top.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), align)]))
    pw = inner_width * 0.92
    bleed = _text_flow(body_html, styles, "bleed")
    return [
        title,
        Spacer(1, 10),
        top,
        Spacer(1, 14),
        Table([[bleed]], colWidths=[pw]),
        Spacer(1, 12),
    ]


def _hero_bleed_multi_layout(
    mode: int,
    title_html: str,
    body_html: str,
    stamp_paths: Sequence[Optional[Path]],
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    max_side: float,
) -> List[Flowable]:
    """Bleed con varios sellos (p. ej. elemento + signo en herencia)."""
    _ = mode
    title = _hp(title_html, styles)
    gap = 8.0
    ms = float(max_side)
    cw = ms + gap
    imgs = [_make_stamp(p, ms) for p in stamp_paths]
    top = Table(
        [imgs],
        colWidths=[cw] * len(imgs),
        rowHeights=[ms + 14],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        ),
    )
    top_wrap = Table([[top]], colWidths=[inner_width])
    top_wrap.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    pw = inner_width * 0.92
    bleed = _text_flow(body_html, styles, "bleed")
    return [
        title,
        Spacer(1, 10),
        top_wrap,
        Spacer(1, 14),
        Table([[bleed]], colWidths=[pw]),
        Spacer(1, 12),
    ]


def _section_block(
    title: str,
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
) -> List[Flowable]:
    story: List[Flowable] = [
        _hp(f"<b>{title}</b>", styles),
        Spacer(1, 8),
        _panel_table(
            [_sp(body_html, styles, "body", "body_sh")],
            styles,
            inner_width,
        ),
        Spacer(1, 12),
    ]
    return story


def _row_with_stamps(
    stamps: Sequence[Optional[Path]],
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    stamp_col: float = 112,
    *,
    max_side: float = STAMP_DEFAULT_PT,
) -> List[Flowable]:
    stamp_h = max_side + 18
    rows: List[list[Flowable]] = [[_make_stamp(p, max_side=max_side)] for p in stamps]
    if not rows:
        rows = [[Spacer(1, 1)]]
    row_heights = [stamp_h] * len(rows)
    left = Table(rows, colWidths=[stamp_col], rowHeights=row_heights)
    left.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    right_w = inner_width - stamp_col
    right = _panel_table([_sp(body_html, styles, "body", "body_sh")], styles, right_w)
    row = Table([[left, right]], colWidths=[stamp_col, right_w])
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return [row, Spacer(1, 16)]


def _grid_stamps_body(
    stamp_paths: Sequence[Optional[Path]],
    cols: int,
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
) -> List[Flowable]:
    """Varias imágenes en mini-parrilla a la izquierda."""
    cells: List[List[Flowable]] = []
    row: List[Flowable] = []
    col = 0
    cell_w = STAMP_DEFAULT_PT + 10
    for p in stamp_paths:
        row.append(_make_stamp(p, max_side=STAMP_DEFAULT_PT))
        col += 1
        if col >= cols:
            cells.append(row)
            row = []
            col = 0
    if row:
        while len(row) < cols:
            row.append(Spacer(1, 1))
        cells.append(row)
    row_h = cell_w + 12
    grid = Table(cells, colWidths=[cell_w] * cols, rowHeights=[row_h] * len(cells))
    grid.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    left_pad = 20
    left_w = cell_w * cols + left_pad
    left = Table([[grid]], colWidths=[left_w])
    left.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    right_w = inner_width - left_w
    right = _panel_table([_sp(body_html, styles, "body", "body_sh")], styles, max(right_w, 200))
    outer = Table([[left, right]], colWidths=[left_w, right_w])
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [outer, Spacer(1, 16)]


def _text_left_stamps_right(
    stamps: Sequence[Optional[Path]],
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    stamp_col: float = 118,
    *,
    max_side: float = STAMP_DEFAULT_PT,
) -> List[Flowable]:
    """Texto en panel a la izquierda, columna de sellos a la derecha (ritmo visual V7)."""
    stamp_h = max_side + 18
    rows: List[list[Flowable]] = [[_make_stamp(p, max_side=max_side)] for p in stamps]
    if not rows:
        rows = [[Spacer(1, 1)]]
    row_heights = [stamp_h] * len(rows)
    right = Table(rows, colWidths=[stamp_col], rowHeights=row_heights)
    right.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    left_w = inner_width - stamp_col
    left = _panel_table([_sp(body_html, styles, "body", "body_sh")], styles, left_w)
    row = Table([[left, right]], colWidths=[left_w, stamp_col])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [row, Spacer(1, 16)]


def _stamps_top_text_bottom_centered(
    stamps: Sequence[Optional[Path]],
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    *,
    max_side: Optional[float] = None,
    panel_alpha: Optional[float] = None,
) -> List[Flowable]:
    """Sellos en franja superior; texto centrado en panel inferior."""
    ms = float(max_side or STAMP_DEFAULT_PT)
    imgs = [_make_stamp(p, ms) for p in stamps]
    gap = 8.0
    cw = ms + gap
    top = Table(
        [imgs],
        colWidths=[cw] * len(imgs),
        rowHeights=[ms + 14],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        ),
    )
    top_wrap = Table([[top]], colWidths=[inner_width])
    top_wrap.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    panel_w = inner_width * 0.97
    bottom = _panel_table(
        [_sp(body_html, styles, "body", "body_sh")], styles, panel_w, panel_alpha=panel_alpha
    )
    return [top_wrap, Spacer(1, 14), bottom, Spacer(1, 16)]


def _flowable_row_stamps_top_text_bottom(
    stamp_flowables: Sequence[Flowable],
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    *,
    max_side: float,
    panel_alpha: Optional[float] = None,
) -> List[Flowable]:
    """Misma composición que _stamps_top_text_bottom_centered, con Flowables ya resueltos."""
    ms = float(max_side)
    gap = 8.0
    cw = ms + gap
    top = Table(
        [list(stamp_flowables)],
        colWidths=[cw] * len(stamp_flowables),
        rowHeights=[ms + 14],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        ),
    )
    top_wrap = Table([[top]], colWidths=[inner_width])
    top_wrap.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    panel_w = inner_width * 0.97
    bottom = _panel_table(
        [_sp(body_html, styles, "body", "body_sh")], styles, panel_w, panel_alpha=panel_alpha
    )
    return [top_wrap, Spacer(1, 14), bottom, Spacer(1, 16)]


def _grid_stamps_top_text_bottom(
    stamp_paths: Sequence[Optional[Path]],
    cols: int,
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
) -> List[Flowable]:
    """Parrilla de sellos arriba; texto centrado abajo."""
    cells: List[List[Flowable]] = []
    row_cells: List[Flowable] = []
    col = 0
    cell_w = STAMP_DEFAULT_PT + 10
    for p in stamp_paths:
        row_cells.append(_make_stamp(p, max_side=STAMP_DEFAULT_PT))
        col += 1
        if col >= cols:
            cells.append(row_cells)
            row_cells = []
            col = 0
    if row_cells:
        while len(row_cells) < cols:
            row_cells.append(Spacer(1, 1))
        cells.append(row_cells)
    row_h = cell_w + 12
    grid = Table(cells, colWidths=[cell_w] * cols, rowHeights=[row_h] * len(cells))
    grid.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    gw = cell_w * cols + 24
    inner_g = Table([[grid]], colWidths=[gw])
    top_wrap = Table([[inner_g]], colWidths=[inner_width])
    top_wrap.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    panel_w = inner_width * 0.97
    bottom = _panel_table([_sp(body_html, styles, "body", "body_sh")], styles, panel_w)
    return [top_wrap, Spacer(1, 12), bottom, Spacer(1, 16)]


def _text_left_grid_right(
    stamp_paths: Sequence[Optional[Path]],
    cols: int,
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
) -> List[Flowable]:
    """Panel de texto a la izquierda, parrilla de sellos a la derecha."""
    cells: List[List[Flowable]] = []
    row_cells: List[Flowable] = []
    col = 0
    cell_w = STAMP_DEFAULT_PT + 10
    for p in stamp_paths:
        row_cells.append(_make_stamp(p, max_side=STAMP_DEFAULT_PT))
        col += 1
        if col >= cols:
            cells.append(row_cells)
            row_cells = []
            col = 0
    if row_cells:
        while len(row_cells) < cols:
            row_cells.append(Spacer(1, 1))
        cells.append(row_cells)
    row_h = cell_w + 12
    grid = Table(cells, colWidths=[cell_w] * cols, rowHeights=[row_h] * len(cells))
    grid.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    left_pad = 20
    right_w = cell_w * cols + left_pad
    right = Table([[grid]], colWidths=[right_w])
    right.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    left_w = inner_width - right_w
    left = _panel_table([_sp(body_html, styles, "body", "body_sh")], styles, max(left_w, 200))
    outer = Table([[left, right]], colWidths=[left_w, right_w])
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [outer, Spacer(1, 16)]


def _row_body_with_right(
    body_html: str,
    right_flow: Flowable,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    right_width: float,
) -> List[Flowable]:
    """Panel de texto a la izquierda, bloque libre a la derecha."""
    left_w = max(inner_width - right_width, 200.0)
    left = _panel_table([_sp(body_html, styles, "body", "body_sh")], styles, left_w)
    row = Table([[left, right_flow]], colWidths=[left_w, right_width])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [row, Spacer(1, 16)]


def _numerology_three_column_digits(
    profile: SoulProfile,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    digit_pt: float,
) -> Flowable:
    """Camino, expresión, alma y personalidad en una fila (cuatro columnas)."""
    pairs = [
        ("Camino de vida", profile.camino_vida),
        ("Expresión", profile.expresion),
        ("Alma interior", profile.alma),
        ("Personalidad", profile.personalidad),
    ]
    gap = 6.0
    ncols = len(pairs)
    col_w = max((inner_width - gap * (ncols + 1)) / float(ncols), 84.0)
    cols: List[Flowable] = []
    base = float(digit_pt)
    for lab, n in pairs:
        digits = digits_for_numerology_stamp(n)
        dig_local = min(
            base,
            max(24.0, (col_w - 20.0) / max(len(digits), 1) - 3.2),
        )
        imgs = [_stamp_or_digit(image_assets.resolve_numerology_digit_png(d), d, dig_local) for d in digits]
        row_t = Table(
            [imgs],
            colWidths=[dig_local + 4] * len(imgs),
            rowHeights=[dig_local + 7],
            style=TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            ),
        )
        col_inner = Table(
            [
                [_text_flow(f"<i>{lab}</i>", styles, "numerology_label")],
                [row_t],
            ],
            colWidths=[col_w - 2],
        )
        col_inner.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        cols.append(col_inner)
    return Table(
        [cols],
        colWidths=[col_w] * ncols,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        ),
    )


def _numerology_section_story(
    profile: SoulProfile,
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    *,
    title_html: str,
    digit_pt: Optional[float] = None,
    body_panel_alpha: Optional[float] = None,
) -> List[Flowable]:
    """Título, franja de dígitos y narrativa en flujo vertical (una página cuando cabe)."""
    dpt = float(digit_pt) if digit_pt is not None else min(48.0, inner_width * 0.065)
    dpt = min(dpt, max(26.0, (inner_width - 52.0) / 6.2))
    # Usa el mismo ancho efectivo para cálculo y render para evitar recortes laterales.
    banner_outer_w = inner_width * 0.92
    compact_w = banner_outer_w * 0.90 if banner_outer_w > 520.0 else banner_outer_w
    banner_inner_w = max(compact_w - 2 * TEXT_PANEL_PAD, 120.0)
    banner = _numerology_three_column_digits(profile, styles, banner_inner_w, dpt)
    pa_body = TEXT_PANEL_ALPHA if body_panel_alpha is None else float(body_panel_alpha)
    body = _panel_table_multi_row(
        body_html,
        styles,
        inner_width,
        panel_alpha=pa_body,
        style_key="numerologia_body",
    )
    banner_panel = _centered_row(
        _panel_table(
            [banner],
            styles,
            banner_outer_w,
            panel_alpha=_ACTIVE_PANEL_ALPHA,
        ),
        inner_width,
    )
    return [
        _title_centered_panel(
            title_html,
            styles,
            inner_width,
            panel_alpha=_ACTIVE_PANEL_ALPHA,
        ),
        Spacer(1, 5),
        banner_panel,
        Spacer(1, 6),
        body,
        Spacer(1, 4),
    ]


def _section_block_layout(
    title: str,
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    layout_idx: int,
    *,
    panel_alpha: Optional[float] = None,
    bleed: bool = False,
    stamp_path: Optional[Path] = None,
    stamp_side: Optional[float] = None,
) -> List[Flowable]:
    """Sección: panel completo, sangre, o imagen izquierda + texto (una imagen representativa)."""
    if stamp_path is not None:
        ss = float(stamp_side if stamp_side is not None else HERO_STAMP_PT)
        return _section_img_left_text_right(
            f"<b>{title}</b>",
            body_html,
            [stamp_path],
            styles,
            inner_width,
            ss,
            panel_alpha=panel_alpha,
            bleed=bleed,
        )
    mode = layout_idx % 4
    widths = (0.94, 0.90, 0.92, 0.98)
    w = inner_width * widths[mode]
    if bleed:
        pa = TEXT_PANEL_ALPHA if panel_alpha is None else float(panel_alpha)
        return [
            _hp(f"<b>{title}</b>", styles),
            Spacer(1, 10),
            _panel_table([_text_flow(body_html, styles, "bleed")], styles, w, panel_alpha=pa),
            Spacer(1, 12),
        ]
    return [
        _hp(f"<b>{title}</b>", styles),
        Spacer(1, 9),
        _panel_table([_text_flow(body_html, styles, "body")], styles, w, panel_alpha=panel_alpha),
        Spacer(1, 10),
    ]


def _giant_phrase_block(
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
) -> List[Flowable]:
    """Una sola frase grande (media página aprox.)."""
    off = inner_width * 0.06
    tbl = Table(
        [[_text_flow(body_html, styles, "giant")]],
        colWidths=[inner_width * 0.88],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), off),
                ("TOPPADDING", (0, 0), (-1, -1), 52),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 44),
            ]
        ),
    )
    return [tbl]


def _row_body_with_left(
    left: Flowable,
    body_html: str,
    styles: dict[str, ParagraphStyle],
    inner_width: float,
    left_width: float,
) -> List[Flowable]:
    """Imagen(es) a la izquierda; panel de texto a la derecha."""
    gap = 12.0
    right_w = max(inner_width - left_width - gap, 180.0)
    right = _panel_table([_text_flow(body_html, styles, "body")], styles, right_w)
    row = Table([[left, right]], colWidths=[left_width, right_w])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return [row, Spacer(1, 8)]


def _horizontal_stamp_row(paths: Sequence[Optional[Path]], max_side: float = 68) -> Table:
    """Una fila de sellos (signo, tótem, dígitos del camino, etc.)."""
    gap = 6.0
    imgs = [_make_stamp(p, max_side) for p in paths]
    cw = max_side + gap
    return Table(
        [imgs],
        colWidths=[cw] * len(imgs),
        rowHeights=[max_side + 10],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        ),
    )


def _horizontal_stamp_flowables(flowables: Sequence[Flowable], max_side: float = 68) -> Table:
    """Fila de sellos ya construidos (mezcla PNG y glifos)."""
    gap = 6.0
    cw = max_side + gap
    return Table(
        [list(flowables)],
        colWidths=[cw] * len(flowables),
        rowHeights=[max_side + 10],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        ),
    )


def safe_mapa_filename_stem(nombre: str) -> str:
    """Nombre seguro para mapa_del_alma_<stem>.pdf (espacios → _, sin caracteres problemáticos)."""
    nf = unicodedata.normalize("NFKD", (nombre or "").strip())
    no_marks = "".join(c for c in nf if not unicodedata.combining(c))
    out: list[str] = []
    for ch in no_marks:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch.isspace():
            out.append("_")
        else:
            out.append("_")
    s = "".join(out).strip("_")
    while "__" in s:
        s = s.replace("__", "_")
    return s or "lectura"


def _log_story_preflight(story: List[Flowable]) -> None:
    """Conteo ligero antes de exportar (densidad / saltos; sin renderizar de nuevo)."""
    n_pb = sum(1 for f in story if isinstance(f, PageBreak))
    logger.info("[OK] Preflight PDF: %d flowables, %d saltos de página.", len(story), n_pb)


def build_pdf(
    profile: SoulProfile,
    narrative: BookNarrative,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Maquetación alineada al briefing editorial por secciones (páginas ≈ orden del story):
    P1 portada mapa+nombre en panel 75 %+logo abajo derecha · P2 texto grande+título «Código del nombre»
    abajo centrado en panel · eco con sello del elemento · esencias/astro/tótem/arca/gema títulos en panel 75 %
    y sellos mayores donde aplica · pausa sin signo, frase impacto en tinta · numerología título+cuerpo junto ·
    hilo/poder/pregunta/mensaje/cierre según bloques actuales en story (ver cuerpo de build_pdf).
    """
    validate_book_strings(list(narrative.as_dict().items()))
    register_fonts()
    _activate_matte_palette(profile.signo)
    styles = build_styles(profile.signo)
    loc = _localized_strings()
    voc = (profile.nombre_pila or "").strip() or (profile.nombre.split()[0] if profile.nombre else "tú")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        stem = safe_mapa_filename_stem(profile.nombre)
        output_path = OUTPUT_DIR / f"mapa_del_alma_{stem}.pdf"
    else:
        output_path = Path(output_path)
        if output_path.suffix.lower() != ".pdf":
            output_path = output_path.with_suffix(".pdf")

    output_path = Path(os.path.abspath(str(output_path)))
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("No se pudo crear la carpeta de salida: %s", exc)
        raise RuntimeError(f"ERROR al generar el PDF: no se puede crear la carpeta: {exc}") from exc

    margin_x = 48
    margin_y = 42
    inner_w = PAGE_W - 2 * margin_x

    logger.info("[OK] Signo calculado: %s", profile.sign_label)
    exp = expected_image_paths(profile)
    # No incrustamos PNG del signo solar occidental (aries.png, geminis.png, …); el fondo por signo sigue en canvas.
    elem_p = image_assets.ruta_imagen_elemento(profile.elemento)
    planet_p = image_assets.ruta_imagen_planeta(profile.planeta_regente)
    totem_p = image_assets.ruta_imagen_totem(exp["totem"])
    gema_p = image_assets.ruta_imagen_gema(exp["gema"])
    arch_p = image_assets.ruta_imagen_arcangel(exp["arcangel"])
    ch_path = image_assets.ruta_imagen_zodiaco_chino(exp["chino"])
    logo_p = image_assets.ruta_logo(LOGO_FILE)
    mapa_title_p = image_assets.ruta_mapa_portada(COVER_TITLE_IMAGE)
    luna_p = image_assets.ruta_imagen_planeta("luna")
    bg_interior = image_assets.resolve_background_sign(profile.signo)

    def _require_asset(label: str, path: Optional[Path]) -> Path:
        if path is None or not path.exists():
            raise RuntimeError(
                f"ERROR al generar el PDF: falta asset obligatorio para {label}."
            )
        return path

    # Garantía estricta: cada sección usa su imagen correcta o falla de forma explícita.
    elem_p = _require_asset("elemento", elem_p)
    planet_p = _require_asset("astro regente", planet_p)
    totem_p = _require_asset("animal tótem", totem_p)
    gema_p = _require_asset("gema de poder", gema_p)
    arch_p = _require_asset("arcángel guía", arch_p)
    ch_path = _require_asset("zodiaco chino", ch_path)
    logo_p = _require_asset("logo", logo_p)
    mapa_title_p = _require_asset("portada mapa", mapa_title_p)
    luna_p = _require_asset("luna", luna_p)
    _ = _require_asset("fondo por signo", bg_interior)

    story: List[Flowable] = []

    usable_h = PAGE_H - 2 * margin_y

    def on_page(canvas, doc):
        draw_full_page_background(canvas, doc, profile)

    _layout_seq = [0]
    _layout_rng = random.Random(int(profile.seed))

    def _layout_step() -> int:
        v = _layout_seq[0]
        _layout_seq[0] += 1
        return v

    base_alpha = float(TEXT_PANEL_ALPHA)
    _alpha_pool = [
        max(0.45, base_alpha - 0.10),
        max(0.45, base_alpha - 0.05),
        base_alpha,
        min(0.82, base_alpha + 0.05),
    ]
    _layout_rng.shuffle(_alpha_pool)

    def _next_alpha() -> float:
        i = _layout_step()
        return float(_alpha_pool[i % len(_alpha_pool)])

    ms = min(inner_w, usable_h)
    hero = min(
        max(float(HERO_STAMP_PT), ms * float(HERO_FRAC_MIN)),
        ms * float(HERO_FRAC_MAX),
    )
    logger.info(
        "[OK] Fondo de páginas interiores (no confundir con imagen de signo en secciones): %s",
        bg_interior,
    )

    def _compact_html_for_master_page(html: str, *, max_blocks: int = 4, max_words: int = 70) -> str:
        """Recorta por bloques completos para evitar frases partidas."""
        parts = [p.strip() for p in str(html or "").split("<br/><br/>") if p.strip()]
        kept: List[str] = []
        used = 0
        for part in parts[:max_blocks]:
            words = re.findall(r"\S+", part)
            if not words:
                continue
            left = max_words - used
            if left <= 0:
                break
            # Nunca incluimos párrafos cortados: o entra completo o se omite.
            if len(words) > left:
                break
            kept.append(part)
            used += len(words)
        return "<br/><br/>".join(kept) if kept else str(html or "")

    # Página 1: solo mapa + nombre + fecha + logo (sin lectura adicional)
    story.extend(
        _cover_first_page_only(
            profile,
            inner_w,
            usable_h,
            styles,
            mapa_title_p,
            logo_p,
        )
    )
    # No forzar salto aquí: permite que el cierre se integre con la página anterior
    # cuando hay espacio y evita una página residual casi vacía al final.
    # Eliminada la "segunda portada": pasamos directo al código del nombre.
    _codigo_titulo_html = loc["codigo_title"]
    story.append(Spacer(1, 8))
    if TRIAL_CODIGO_MAPA_LEFT_OF_TEXT:
        story.extend(
            _trial_codigo_mapa_left_body_right(
                _codigo_titulo_html,
                narrative.section_codigo_nombre,
                mapa_title_p,
                styles,
                inner_w,
                hero,
                _next_alpha(),
            )
        )
    else:
        story.append(
            _title_centered_panel(
                _codigo_titulo_html,
                styles,
                inner_w,
                panel_alpha=TEXT_PANEL_ALPHA,
            )
        )
        story.append(Spacer(1, 12))
        story.extend(
            _section_stamp_body_fullwidth_panel(
                narrative.section_codigo_nombre,
                None,
                styles,
                inner_w,
                min(hero, inner_w * 0.42),
                panel_alpha=_next_alpha(),
            )
        )
    story.append(PageBreak())

    # 3 — Eco de ancestros (título + texto + imagen)
    story.extend(
        _section_img_left_text_right(
            loc["eco_title"],
            narrative.section_eco_ancestros,
            [elem_p] if elem_p is not None else [],
            styles,
            inner_w,
            hero * 0.88,
            panel_alpha=_next_alpha(),
            title_centered_panel=True,
        )
    )
    story.append(PageBreak())

    # 4 — Signo + elemento en una sola página maestra.
    sign_elem_body = (
        f"{_compact_html_for_master_page(narrative.section_esencia_signo, max_blocks=5, max_words=88)}"
        f"<br/><br/><b>{loc['tu_elemento']}</b><br/><br/>"
        f"{_compact_html_for_master_page(narrative.section_esencia_elemento, max_blocks=7, max_words=175)}"
    )
    u_es = _layout_rng.random()
    if u_es < 0.34:
        story.extend(
            _section_text_top_image_bottom(
                loc["esencia_title"],
                sign_elem_body,
                [elem_p] if elem_p is not None else [],
                styles,
                inner_w,
                hero * 0.90,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
                body_in_panel=False,
            )
        )
    elif u_es < 0.67:
        story.extend(
            _section_img_left_text_right(
                loc["esencia_title"],
                sign_elem_body,
                [elem_p] if elem_p is not None else [],
                styles,
                inner_w,
                hero * 0.86,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
            )
        )
    else:
        story.extend(
            _section_img_right_text_left(
                loc["esencia_title"],
                sign_elem_body,
                [elem_p] if elem_p is not None else [],
                styles,
                inner_w,
                hero * 0.86,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
            )
        )
    story.append(PageBreak())

    # 5 — Astro regente
    u_pl = _layout_rng.random()
    planeta_html = _compact_html_for_master_page(narrative.section_planeta, max_blocks=4, max_words=60)
    if u_pl < 0.34:
        story.extend(
            _section_img_left_text_right(
                loc["astro_title"],
                planeta_html,
                [planet_p] if planet_p is not None else [],
                styles,
                inner_w,
                hero * 0.88,
                panel_alpha=_next_alpha(),
                title_centered_panel=bool((profile.seed + 3) % 2),
            )
        )
    elif u_pl < 0.67:
        story.extend(
            _section_img_right_text_left(
                loc["astro_title"],
                planeta_html,
                [planet_p] if planet_p is not None else [],
                styles,
                inner_w,
                hero * 0.88,
                panel_alpha=_next_alpha(),
                title_centered_panel=bool((profile.seed + 5) % 2),
            )
        )
    else:
        story.extend(
            _section_text_top_image_bottom(
                loc["astro_title"],
                planeta_html,
                [planet_p] if planet_p is not None else [],
                styles,
                inner_w,
                hero * 1.02,
                panel_alpha=_next_alpha(),
                title_centered_panel=False,
                body_in_panel=True,
            )
        )
    story.append(PageBreak())

    # 6 — Tótem
    u_to = _layout_rng.random()
    totem_html = _compact_html_for_master_page(narrative.section_totem, max_blocks=4, max_words=56)
    if u_to < 0.33:
        story.extend(
            _section_text_top_image_bottom(
                loc["totem_title"],
                totem_html,
                [totem_p] if totem_p is not None else [],
                styles,
                inner_w,
                hero * 1.04,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
                body_in_panel=False,
            )
        )
    elif u_to < 0.66:
        story.extend(
            _section_img_left_text_right(
                loc["totem_title"],
                totem_html,
                [totem_p] if totem_p is not None else [],
                styles,
                inner_w,
                hero * 0.92,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
            )
        )
    else:
        story.extend(
            _section_img_right_text_left(
                loc["totem_title"],
                totem_html,
                [totem_p] if totem_p is not None else [],
                styles,
                inner_w,
                hero * 0.92,
                panel_alpha=_next_alpha(),
                title_centered_panel=False,
            )
        )
    story.append(PageBreak())

    # 7 — Arcángel guía
    u_ar = _layout_rng.random()
    arch_html = _compact_html_for_master_page(narrative.section_arcangel, max_blocks=4, max_words=56)
    if u_ar < 0.33:
        story.extend(
            _section_img_right_text_left(
                loc["arcangel_title"],
                arch_html,
                [arch_p] if arch_p is not None else [],
                styles,
                inner_w,
                hero * 0.90,
                panel_alpha=_next_alpha(),
                title_centered_panel=False,
            )
        )
    elif u_ar < 0.66:
        story.extend(
            _section_text_top_image_bottom(
                loc["arcangel_title"],
                arch_html,
                [arch_p] if arch_p is not None else [],
                styles,
                inner_w,
                hero * 0.96,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
                body_in_panel=True,
            )
        )
    else:
        story.extend(
            _section_img_left_text_right(
                loc["arcangel_title"],
                arch_html,
                [arch_p] if arch_p is not None else [],
                styles,
                inner_w,
                hero * 0.90,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
            )
        )
    story.append(PageBreak())

    # 8 — Gema
    u_ge = _layout_rng.random()
    gema_html = _compact_html_for_master_page(narrative.section_gema, max_blocks=4, max_words=56)
    if u_ge < 0.33:
        story.extend(
            _section_img_left_text_right(
                loc["gema_title"],
                gema_html,
                [gema_p] if gema_p is not None else [],
                styles,
                inner_w,
                hero * 0.90,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
            )
        )
    elif u_ge < 0.66:
        story.extend(
            _section_text_top_image_bottom(
                loc["gema_title"],
                gema_html,
                [gema_p] if gema_p is not None else [],
                styles,
                inner_w,
                hero * 1.02,
                panel_alpha=None,
                title_centered_panel=False,
                body_in_panel=False,
            )
        )
    else:
        story.extend(
            _section_img_right_text_left(
                loc["gema_title"],
                gema_html,
                [gema_p] if gema_p is not None else [],
                styles,
                inner_w,
                hero * 0.90,
                panel_alpha=_next_alpha(),
                title_centered_panel=False,
            )
        )
    story.append(PageBreak())

    # 9 — Sabiduría oriental (variación: texto arriba e imagen abajo)
    u_sa = _layout_rng.random()
    sab_html = _compact_html_for_master_page(
        narrative.section_sabiduria_oriental, max_blocks=4, max_words=42
    )
    if u_sa < 0.30:
        story.extend(
            _section_quote_centered_layout(
                loc["sabiduria_title"],
                sab_html,
                [ch_path] if ch_path is not None else [],
                styles,
                inner_w,
                hero * 0.86,
                panel_alpha=_next_alpha(),
                title_centered_panel=False,
            )
        )
    else:
        body_in_panel = u_sa < 0.65
        story.extend(
            _section_text_top_image_bottom(
                loc["sabiduria_title"],
                sab_html,
                [ch_path] if ch_path is not None else [],
                styles,
                inner_w,
                hero * 0.98,
                panel_alpha=_next_alpha() if body_in_panel else None,
                title_centered_panel=False,
                body_in_panel=body_in_panel,
            )
        )
    story.append(PageBreak())

    # 10 — Numerología sagrada (título + tres columnas de dígitos + cuerpo en vertical)
    digit_pt = min(96.0, hero * 0.40)
    story.extend(
        _numerology_section_story(
            profile,
            _compact_html_for_master_page(narrative.section_numerologia, max_blocks=9, max_words=145),
            styles,
            inner_w,
            title_html=loc["numerologia_title"],
            digit_pt=digit_pt,
            body_panel_alpha=_next_alpha(),
        )
    )
    story.append(PageBreak())
    story.extend(
        _layout_wow_page(
            styles,
            inner_w,
            (
                loc["wow_1"].replace("en ti", f"en {voc}")
            ),
            panel_alpha=_next_alpha(),
        )
    )
    story.append(PageBreak())

    # 11 — Hilo invisible
    u_hi = _layout_rng.random()
    hilo_html = _compact_html_for_master_page(narrative.section_hilo, max_blocks=5, max_words=110)
    if u_hi < 0.28:
        story.extend(
            _section_img_right_text_left(
                loc["hilo_title"],
                hilo_html,
                [luna_p] if luna_p is not None else ([elem_p] if elem_p is not None else []),
                styles,
                inner_w,
                hero * 0.88,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
            )
        )
    else:
        body_in_panel = u_hi < 0.62
        title_centered = bool((profile.seed + 17) % 2)
        story.extend(
            _section_text_top_image_bottom(
                loc["hilo_title"],
                hilo_html,
                [luna_p] if luna_p is not None else ([elem_p] if elem_p is not None else []),
                styles,
                inner_w,
                hero * (0.98 if body_in_panel else 0.90),
                panel_alpha=_next_alpha() if (body_in_panel or title_centered) else None,
                title_centered_panel=title_centered,
                body_in_panel=body_in_panel,
            )
        )
    story.append(PageBreak())

    # 12 — Sombra sagrada
    u_sh = _layout_rng.random()
    sombra_html = _compact_html_for_master_page(narrative.section_poder_sombra, max_blocks=5, max_words=115)
    if u_sh < 0.35:
        story.extend(
            _section_img_left_text_right(
                loc["sombra_title"],
                sombra_html,
                [luna_p] if luna_p is not None else [],
                styles,
                inner_w,
                hero * 0.88,
                panel_alpha=None,
                title_centered_panel=False,
                bleed=True,
            )
        )
    elif u_sh < 0.70:
        story.extend(
            _section_img_right_text_left(
                loc["sombra_title"],
                sombra_html,
                [luna_p] if luna_p is not None else [],
                styles,
                inner_w,
                hero * 0.88,
                panel_alpha=None,
                title_centered_panel=False,
                bleed=True,
            )
        )
    else:
        story.extend(
            _section_text_top_image_bottom(
                loc["sombra_title"],
                sombra_html,
                [luna_p] if luna_p is not None else [],
                styles,
                inner_w,
                hero * 1.05,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
                body_in_panel=False,
            )
        )
    story.append(PageBreak())
    story.extend(
        _layout_wow_page(
            styles,
            inner_w,
            (
                loc["wow_2"]
            ),
            panel_alpha=_next_alpha(),
        )
    )
    story.append(PageBreak())

    # 13 — Mensaje personal
    u_ms = _layout_rng.random()
    mensaje_html = _compact_html_for_master_page(
        narrative.section_mensaje_personal, max_blocks=4, max_words=44
    )
    if u_ms < 0.50:
        story.extend(
            _section_img_left_text_right(
                loc["mensaje_title"],
                mensaje_html,
                [luna_p] if luna_p is not None else [],
                styles,
                inner_w,
                hero * 0.86,
                panel_alpha=_next_alpha(),
                title_centered_panel=True,
                bleed=True,
            )
        )
    else:
        story.extend(
            _section_img_right_text_left(
                loc["mensaje_title"],
                mensaje_html,
                [luna_p] if luna_p is not None else [],
                styles,
                inner_w,
                hero * 0.86,
                panel_alpha=None,
                title_centered_panel=False,
                bleed=True,
            )
        )
    story.append(PageBreak())

    # 14 — Contraportada + firma del universo en una sola página.
    firma_visual = FirmaUniversoFlowable(
        profile.nombre,
        profile.camino_vida,
        profile.fecha,
        inner_w,
        stamp_size=min(float(FIRMA_UNIVERSO_STAMP_LAST_PREMIUM_PT), 96.0),
        leyenda="",
    )
    cierre_logo = (
        Table(
            [[_cover_stamp(logo_p, 62.0)]],
            colWidths=[inner_w],
            style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]),
        )
        if logo_p is not None
        else Spacer(1, 1)
    )
    universe_panel = _centered_row(
        _panel_table_multi_row(
            _compact_html_for_master_page(narrative.universe_firma_line, max_blocks=3, max_words=34),
            styles,
            inner_w * 0.96,
            panel_alpha=TEXT_PANEL_ALPHA,
            style_key="firma_panel",
        ),
        inner_w,
    )
    _cierre_rng = random.Random(profile.seed + 91_919)
    _frases_memorables = (
        loc["cierre_1"],
        loc["cierre_2"],
        loc["cierre_3"],
        loc["cierre_4"],
        loc["cierre_5"],
        loc["cierre_6"],
    )
    frase_cierre_final = _cierre_rng.choice(_frases_memorables)
    cierre: List[Flowable] = [
        _title_centered_panel(
            loc["cierre_title"],
            styles,
            inner_w,
            panel_alpha=TEXT_PANEL_ALPHA,
        ),
        Spacer(1, 0.5),
        Table(
            [[firma_visual]],
            colWidths=[inner_w],
            style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]),
        ),
        Spacer(1, 0.5),
        _centered_row(
            _panel_table_multi_row(
                _compact_html_for_master_page(narrative.back_cover, max_blocks=2, max_words=16),
                styles,
                inner_w * 0.96,
                panel_alpha=TEXT_PANEL_ALPHA,
                style_key="closing_firma_body",
            ),
            inner_w,
        ),
        Spacer(1, 2),
        universe_panel,
        Spacer(1, 4),
        _centered_row(_text_flow(frase_cierre_final, styles, "impact"), inner_w),
        Spacer(1, 6),
        cierre_logo,
    ]
    story.extend(
        [
            KeepInFrame(
                maxWidth=inner_w,
                maxHeight=usable_h - 6,
                content=cierre,
                mode="shrink",
                hAlign="CENTER",
                vAlign="TOP",
            )
        ]
    )
    _log_story_preflight(story)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=PAGE_SIZE,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_y,
        bottomMargin=margin_y,
        title=loc["book_title"],
        author=profile.nombre,
    )
    try:
        logger.info(
            "[OK] Renderizando PDF (varias paginas; puede tardar 30-90 s; no cierres la ventana)... %s",
            output_path,
        )
        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        logger.info("[OK] Renderizado completado; comprobando archivo...")
    except Exception as exc:
        logger.exception("Fallo al construir el PDF con ReportLab")
        raise RuntimeError(f"ERROR al generar el PDF: {exc}") from exc

    final_abs = Path(os.path.abspath(str(output_path)))
    if not final_abs.is_file():
        msg = f"ERROR: el archivo PDF no existe tras doc.build(): {final_abs}"
        logger.error("%s", msg)
        raise IOError(msg)
    return final_abs
