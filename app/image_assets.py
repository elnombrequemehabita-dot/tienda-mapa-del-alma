"""
Resolución explícita de imágenes por categoría (sin coincidencias parciales ni 'contains').

A) Signo solar — solo el archivo de SIGN_IMAGE[signo].
B) Temáticas — elemento, planeta, tótem, gema, arcángel, zodiaco chino, luna/sombra.
C) Decoración — no sustituye a A/B; usar solo donde el diseño lo indique.

Búsqueda: primero assets/imagenes/<subcarpeta>/archivo.ext, luego la raíz de imagenes/.
"""
from __future__ import annotations

import logging
from pathlib import Path
import unicodedata
from typing import Optional

from config import (
    ELEMENT_IMAGE,
    GEM_POOL,
    IMAGES_DIR,
    PLANET_IMAGE,
    SIGN_IMAGE,
    TOTEM_POOL,
    background_image_filenames_for_sign,
)
from logic import ElementKey, SignKey

logger = logging.getLogger(__name__)

# Orden: carpeta temática / raíz (compatibilidad con assets planos).
SUB_SIGNOS = ("signos", "")
SUB_ELEMENTOS = ("elementos", "")
SUB_PLANETAS = ("planetas", "")
SUB_TOTEMS = ("totems", "")
SUB_ARCAN = ("arcangeles", "")
SUB_GEMAS = ("gemas", "")
SUB_CHINO = ("zodiaco_chino", "")
SUB_SOMBRA = ("sombras", "")
SUB_DECO = ("decoraciones", "")
SUB_PORTADA = ("portada", "")
# Dígitos de numerología (1.png … 9.png): subcarpetas habituales y raíz de imagenes/.
SUB_NUMEROLOGIA = ("numerologia", "numeros", "")


def _norm_filename(name: str) -> str:
    """Normaliza nombre de archivo para comparación exacta robusta (acentos/case)."""
    n = unicodedata.normalize("NFKD", (name or "").strip().lower())
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    return n


def _iter_candidates(filename: str, subdirs: tuple[str, ...]) -> list[Path]:
    if not filename:
        return []
    target = _norm_filename(filename)
    ok_ext = (".png", ".jpg", ".jpeg", ".webp")
    out: list[Path] = []
    if not IMAGES_DIR.is_dir():
        return out
    for sub in subdirs:
        base = IMAGES_DIR / sub if sub else IMAGES_DIR
        if not base.is_dir():
            continue
        try:
            for p in base.iterdir():
                if p.suffix.lower() in ok_ext and _norm_filename(p.name) == target:
                    out.append(p.resolve())
                    return out
        except OSError as exc:
            logger.warning("No se pudo leer %s: %s", base, exc)
    return out


def resolve_numerology_digit_png(digit: int) -> Optional[Path]:
    """
    PNG del dígito 1–9 para numerología: busca en numerologia/, numeros/ y raíz (mismo nombre exacto).
    """
    if digit < 1 or digit > 9:
        return None
    for ext in (".png", ".PNG", ".jpg", ".jpeg", ".webp"):
        fname = f"{digit}{ext}"
        p = resolve_exact(fname, SUB_NUMEROLOGIA)
        if p:
            logger.info("[OK] Numerología dígito %s: %s", digit, p)
            return p
    p = resolve_flat_filename(f"{digit}.png")
    if p:
        logger.info("[OK] Numerología dígito %s (raíz): %s", digit, p)
        return p
    logger.debug("Sin imagen de dígito %s para numerología", digit)
    return None


def resolve_flat_filename(filename: str) -> Optional[Path]:
    """
    Un solo nombre de archivo en la raíz de assets/imagenes (p. ej. numerología 1.png … 9.png).
    Sin coincidencias parciales.
    """
    if not filename:
        return None
    hits = _iter_candidates(filename, ("",))
    return hits[0] if hits else None


def resolve_exact(filename: str, subdirs: tuple[str, ...]) -> Optional[Path]:
    hits = _iter_candidates(filename, subdirs)
    return hits[0] if hits else None


def resolve_background_sign(sign_key: SignKey) -> Optional[Path]:
    """Fondos por signo: lista fija en config; solo coincidencia exacta de nombre de archivo."""
    for fname in background_image_filenames_for_sign(sign_key):
        p = resolve_exact(fname, SUB_SIGNOS)
        if p:
            logger.debug("Fondo astral (signo %s): %s", sign_key, p)
            return p
        p = resolve_exact(fname, ("",))
        if p:
            logger.debug("Fondo astral (signo %s, raíz imágenes): %s", sign_key, p)
            return p
    logger.warning("[WARN] Sin archivo de fondo explícito para signo %s", sign_key)
    return None


def ruta_imagen_signo(sign: SignKey) -> Optional[Path]:
    fn = SIGN_IMAGE.get(sign)
    if not fn:
        logger.error("[ERROR] Falta entrada SIGN_IMAGE para el signo %s", sign)
        return None
    p = resolve_exact(fn, SUB_SIGNOS)
    if not p:
        p = resolve_exact(fn, ("",))
    if p:
        logger.info("[OK] Imagen principal del signo (%s): %s", sign, p)
    else:
        logger.error("[ERROR] Falta imagen principal del signo %s (%s)", sign, fn)
    return p


def ruta_imagen_elemento(elem: ElementKey) -> Optional[Path]:
    fn = ELEMENT_IMAGE.get(elem)
    if not fn:
        logger.error("[ERROR] ELEMENT_IMAGE sin clave %s", elem)
        return None
    p = resolve_exact(fn, SUB_ELEMENTOS) or resolve_exact(fn, ("",))
    if p:
        logger.info("[OK] Imagen de elemento (%s): %s", elem, p)
    else:
        logger.warning("[WARN] No existe imagen de elemento %s (%s)", elem, fn)
    return p


def ruta_imagen_planeta(planet_key: str) -> Optional[Path]:
    fn = PLANET_IMAGE.get(planet_key)
    if not fn:
        logger.warning("[WARN] Planeta %s no está en PLANET_IMAGE; se espera %s.png", planet_key, planet_key)
        fn = f"{planet_key}.png"
    p = resolve_exact(fn, SUB_PLANETAS) or resolve_exact(fn, ("",))
    if p:
        logger.info("[OK] Imagen de planeta (%s): %s", planet_key, p)
    else:
        logger.warning("[WARN] No se encontró imagen exacta para planeta %s (%s)", planet_key, fn)
    return p


def ruta_imagen_totem(filename: str) -> Optional[Path]:
    if filename not in TOTEM_POOL:
        logger.warning("[WARN] Tótem %s fuera del pool editorial TOTEM_POOL", filename)
    p = resolve_exact(filename, SUB_TOTEMS) or resolve_exact(filename, ("",))
    if p:
        logger.info("[OK] Imagen de tótem: %s", p)
    else:
        logger.warning("[WARN] No se encontró imagen de tótem: %s", filename)
    return p


def ruta_imagen_gema(filename: str) -> Optional[Path]:
    if filename not in GEM_POOL:
        logger.warning("[WARN] Gema %s fuera del pool editorial GEM_POOL", filename)
    p = resolve_exact(filename, SUB_GEMAS) or resolve_exact(filename, ("",))
    if p:
        logger.info("[OK] Imagen de gema: %s", p)
    else:
        logger.warning("[WARN] No se encontró imagen de gema: %s", filename)
    return p


def ruta_imagen_arcangel(filename: str) -> Optional[Path]:
    p = resolve_exact(filename, SUB_ARCAN) or resolve_exact(filename, ("",))
    if p:
        logger.info("[OK] Imagen de arcángel: %s", p)
    else:
        logger.warning(
            "[WARN] No hay imagen exacta para arcángel (%s); se usará marcador neutro en PDF.",
            filename,
        )
    return p


def ruta_imagen_zodiaco_chino(filename: str) -> Optional[Path]:
    p = resolve_exact(filename, SUB_CHINO) or resolve_exact(filename, ("",))
    if p:
        logger.info("[OK] Imagen zodiaco chino: %s", p)
    else:
        logger.warning("[WARN] Animal chino sin archivo: %s", filename)
    return p


def ruta_imagen_sombra(filename: str) -> Optional[Path]:
    p = resolve_exact(filename, SUB_SOMBRA) or resolve_exact(filename, ("",))
    if p:
        logger.info("[OK] Imagen sombra/luna temática: %s", p)
    else:
        logger.warning("[WARN] Sombra/luna sin archivo: %s", filename)
    return p


def ruta_mapa_portada(filename: str) -> Optional[Path]:
    """Portada: imagen «mapa» (no es el signo solar)."""
    p = resolve_exact(filename, SUB_PORTADA) or resolve_exact(filename, ("",))
    if p:
        logger.info("[OK] Imagen portada (mapa): %s", p)
    else:
        logger.error("[ERROR] Falta la imagen de portada %s", filename)
    return p


def ruta_logo(filename: str) -> Optional[Path]:
    p = resolve_exact(filename, ("",))
    if p:
        logger.info("[OK] Logo: %s", p)
    else:
        logger.error("[ERROR] Falta el logo %s", filename)
    return p


def ruta_decoracion_opcional(nombre_archivo: str) -> Optional[Path]:
    """Adornos pequeños: nunca como imagen protagonista de sección."""
    p = resolve_exact(nombre_archivo, SUB_DECO) or resolve_exact(nombre_archivo, ("",))
    if p:
        logger.info("[OK] Decoración: %s", p)
    return p
