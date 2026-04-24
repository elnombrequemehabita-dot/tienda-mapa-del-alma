"""
Validación y limpieza final de HTML narrativo antes del PDF.

Protocolo V15:
- Cero llaves `{}` en la salida: si aparecen, no se genera PDF hasta reescribir.
- Cero marcadores de plantilla ni texto vacío tipo «contenido aquí».
- Detección de repeticiones consecutivas sospechosas (eco de plantilla).
"""
from __future__ import annotations

import logging
import re
from typing import Iterable

logger = logging.getLogger(__name__)


class NarrativeValidationError(ValueError):
    """La narrativa no pasó la validación de salida; no debe generarse el PDF."""


# Patrones que delatan automatización incompleta o plantillas
_SUSPICIOUS_SUBSTRINGS = (
    "contenido aquí",
    "contenido aqui",
    "placeholder",
    "lorem ipsum",
    "{ap}",
    "{nombre}",
    "{np}",
    "símbolo símbolo",
    "simbolo simbolo",
    "todo:",
    "fixme",
    "xxx",
    "tbd",
    "rellenar",
)

_RE_BRACES = re.compile(r"\{[^{}]+\}")


def rewrite_html_natural_braces(html: str) -> str:
    """
    Reescribe párrafo HTML eliminando placeholders tipo {ap} o llaves sueltas
    para que el texto siga fluyendo sin código expuesto.
    """
    if not html:
        return html
    t = _RE_BRACES.sub("", html)
    t = t.replace("{", "").replace("}", "")
    t = re.sub(r"  +", " ", t)
    t = re.sub(r"\s+<", "<", t)
    t = re.sub(r">\s+", ">", t)
    return t.strip()

# Palabras cortas que pueden repetirse sin ser error (español)
_CONSEC_DUP_IGNORE = frozenset(
    {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "y",
        "o",
        "a",
        "de",
        "en",
        "que",
        "no",
        "si",
        "se",
        "es",
        "le",
        "te",
        "me",
        "lo",
        "al",
        "del",
        "con",
        "por",
        "su",
        "sus",
        "tu",
        "tus",
        "mi",
        "mis",
    }
)


def strip_orphan_braces(html: str) -> str:
    """Último recurso: elimina restos tipo {clave} y llaves sueltas."""
    if not html:
        return html
    cleaned = _RE_BRACES.sub("", html)
    cleaned = cleaned.replace("{", "").replace("}", "")
    return cleaned


def _words_for_scan(html: str) -> list[str]:
    low = re.sub(r"<[^>]+>", " ", html.lower())
    return re.findall(r"[\wáéíóúñüÁÉÍÓÚÑÜ]+", low)


def _normalized_tokens(html: str) -> list[str]:
    raw = _words_for_scan(html)
    out: list[str] = []
    for w in raw:
        if len(w) <= 2:
            continue
        if w in _CONSEC_DUP_IGNORE:
            continue
        out.append(w)
    return out


def _cross_field_dup_issues(fields: list[tuple[str, str]]) -> list[str]:
    """
    Detecta eco de plantilla entre secciones completas.
    Regla: no repetir segmentos de 9 palabras normalizadas entre campos distintos.
    """
    seen: dict[str, str] = {}
    issues: list[str] = []
    for label, text in fields:
        tokens = _normalized_tokens(text)
        if len(tokens) < 9:
            continue
        local_seen: set[str] = set()
        for i in range(len(tokens) - 8):
            gram = " ".join(tokens[i : i + 9])
            if gram in local_seen:
                continue
            local_seen.add(gram)
            other = seen.get(gram)
            if other is not None and other != label:
                issues.append(f"{label}: repite frase-base con {other} («{gram}»)")
                if len(issues) >= 8:
                    return issues
            else:
                seen[gram] = label
    return issues


def scan_narrative(html: str, *, label: str = "") -> list[str]:
    """
    Devuelve lista de problemas detectados (vacía = OK).
    No modifica el texto.
    """
    issues: list[str] = []
    if not html or not str(html).strip():
        issues.append(f"{label}: texto vacío" if label else "texto vacío")
        return issues
    text = str(html)
    if "{" in text or "}" in text:
        issues.append(f"{label}: contiene llaves sin resolver" if label else "contiene llaves sin resolver")
    low = text.lower()
    for s in _SUSPICIOUS_SUBSTRINGS:
        if s in low:
            issues.append(
                f"{label}: posible plantilla ({s})" if label else f"posible plantilla ({s})"
            )
    words = _words_for_scan(text)
    for i in range(len(words) - 2):
        if words[i] == words[i + 1] == words[i + 2]:
            w = words[i]
            # Camino/expresión/alma pueden coincidir (p. ej. 1-1-1 o 11-11-11); no es eco de plantilla.
            if w.isdigit():
                continue
            issues.append(
                f"{label}: repetición triple de «{words[i]}»" if label else f"repetición triple de «{words[i]}»"
            )
            break
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        if a == b and len(a) > 2 and a not in _CONSEC_DUP_IGNORE:
            issues.append(
                f"{label}: palabra repetida consecutiva «{a}»" if label else f"palabra repetida consecutiva «{a}»"
            )
            break
    return issues


def finalize_html(html: str, *, label: str = "", strict: bool = True) -> str:
    """
    Limpieza final antes del PDF. Si hay llaves `{` `}`, reescribe el párrafo
    para eliminar código expuesto; luego valida el resto (plantillas, repeticiones).
    """
    work = html
    if work and ("{" in work or "}" in work):
        rewritten = rewrite_html_natural_braces(work)
        if not scan_narrative(rewritten, label=label):
            logger.warning("Reescritura automática aplicada (llaves) [%s]", label)
            return rewritten
        work = rewritten

    issues = scan_narrative(work, label=label)
    if not issues:
        return work

    if strict:
        for msg in issues:
            logger.error("Narrativa [%s]: %s", label, msg)
        raise NarrativeValidationError("; ".join(issues))
    for msg in issues:
        logger.warning("Narrativa [%s]: %s", label, msg)
    out = strip_orphan_braces(work)
    if scan_narrative(out, label=label):
        raise NarrativeValidationError(f"Texto no limpio tras sanitize: {label!r}")
    return out


def validate_book_strings(fields: Iterable[tuple[str, str]]) -> None:
    """V15: valida todos los fragmentos; lanza si algo falla."""
    normalized_fields: list[tuple[str, str]] = []
    for key, text in fields:
        finalize_html(text, label=key, strict=True)
        normalized_fields.append((key, text))
    cross = _cross_field_dup_issues(normalized_fields)
    if cross:
        for msg in cross:
            logger.error("Narrativa libro: %s", msg)
        raise NarrativeValidationError("; ".join(cross))


def emergency_strip_if_needed(html: str, *, label: str = "") -> str:
    """
    Último recurso tras reintentos: quita llaves y vuelve a validar.
    Solo debe usarse cuando la composición falló de forma defensiva.
    """
    cleaned = strip_orphan_braces(html)
    issues = scan_narrative(cleaned, label=label)
    if issues:
        raise NarrativeValidationError(f"Emergencia: aún inválido [{label}]: {issues}")
    logger.warning("Se aplicó limpieza de emergencia a [%s]", label)
    return cleaned
