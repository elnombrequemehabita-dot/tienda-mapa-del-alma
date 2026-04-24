"""
Mapa del Alma — motor narrativo V15 (15 secciones editoriales).

Composición desde `narrative_banks_v15` únicamente; salida filtrada por `narrative_sanitize`
y reintentos con semilla desplazada si hiciera falta.
"""
from __future__ import annotations

import random
import re
from html import unescape
from dataclasses import dataclass
from typing import Mapping

from logic import (
    SoulProfile,
    element_label_es,
    planet_label_es,
    sign_label_es,
    universe_fingerprint_code,
)
from narrative_banks_v15 import (
    compose_afirmaciones_secas,
    compose_arcangel_pagina,
    compose_back_cover_human,
    compose_codigo_nombre,
    compose_cover_tagline,
    compose_eco_ancestros,
    compose_esencia_elemento,
    compose_esencia_signo,
    compose_gema_poder_pagina,
    compose_hilo_contradiccion,
    compose_mensaje_personal_climax,
    compose_numerologia_sagrada_pagina,
    compose_planeta_regente,
    compose_poder_y_sombra,
    compose_pregunta_alma,
    compose_respira_intercalada,
    compose_sabiduria_oriental_pagina,
    compose_totem_pagina,
    pick_planet_myth,
    pick_shadow,
)
from narrative_sanitize import NarrativeValidationError, emergency_strip_if_needed, finalize_html


@dataclass(frozen=True)
class BookNarrative:
    cover_subtitle: str
    cover_tagline: str
    cover_sacred_line: str
    cover_editorial_line: str
    cover_volume_title: str

    section_codigo_nombre: str
    section_eco_ancestros: str
    section_esencia_signo: str
    section_esencia_elemento: str
    section_planeta: str
    section_totem: str
    section_arcangel: str
    section_gema: str
    section_sabiduria_oriental: str
    section_numerologia: str
    section_hilo: str
    section_poder_sombra: str
    section_respira: str
    section_pregunta_alma: str
    section_mensaje_personal: str

    affirmation_one: str
    affirmation_two: str
    affirmation_three: str

    back_cover: str
    universe_firma_line: str

    def as_dict(self) -> Mapping[str, str]:
        return {k: v for k, v in self.__dict__.items()}


def _safe_finalize(key: str, text: str, *, allow_emergency: bool) -> str:
    try:
        return finalize_html(text, label=key, strict=True)
    except NarrativeValidationError:
        if not allow_emergency:
            raise
        return emergency_strip_if_needed(text, label=key)


def _trim_html_words(html: str, max_words: int) -> str:
    if max_words <= 0:
        return html
    parts = [p.strip() for p in html.split("<br/><br/>") if p.strip()]
    out: list[str] = []
    used = 0
    for part in parts:
        words = re.findall(r"\S+", part)
        if not words:
            continue
        left = max_words - used
        if left <= 0:
            break
        if len(words) <= left:
            out.append(part)
            used += len(words)
            continue
        # Evita frases truncadas: si no cabe completo, se corta por bloque.
        break
    return "<br/><br/>".join(out) if out else html


def _vocativo(p: SoulProfile) -> str:
    """Nombre corto para el cuerpo del libro: primera mención formal va en portada/cierre."""
    np = (p.nombre_pila or "").strip()
    if np:
        return np
    parts = (p.nombre or "").split()
    return parts[0] if parts else (p.nombre or "").strip()


def _density_cap_for_key(key: str) -> int:
    caps = {
        "section_codigo_nombre": 180,
        "section_eco_ancestros": 140,
        "section_esencia_signo": 135,
        "section_esencia_elemento": 200,
        "section_planeta": 110,
        "section_totem": 90,
        "section_arcangel": 88,
        "section_gema": 105,
        "section_sabiduria_oriental": 88,
        "section_mensaje_personal": 145,
        "section_poder_sombra": 175,
        "section_pregunta_alma": 70,
        "section_hilo": 130,
        "section_numerologia": 120,
        "back_cover": 18,
        "universe_firma_line": 110,
    }
    if key in caps:
        return caps[key]
    if key.startswith("section_"):
        return 75
    if key.startswith("affirmation_"):
        return 28
    return 90


def _apply_case(reference: str, replacement: str) -> str:
    if reference.isupper():
        return replacement.upper()
    if reference[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _genderize_text(html: str, sexo: str) -> str:
    """
    Ajuste ligero de género gramatical para evitar cruces amigo/amiga, agotada/agotado, etc.
    No reescribe toda la narrativa: solo términos sensibles.
    """
    if not html:
        return html
    out = html
    male = sexo == "masculino"

    # Pares explícitos "femenino o masculino" -> selecciona según sexo.
    pair_patterns: list[tuple[str, str, str]] = [
        (r"\b(atrapada)\s+o\s+(atrapado)\b", "atrapada", "atrapado"),
        (r"\b(fragmentada)\s+o\s+(fragmentado)\b", "fragmentada", "fragmentado"),
        (r"\b(partida)\s+o\s+(partido)\b", "partida", "partido"),
        (r"\b(agotada)\s+o\s+(agotado)\b", "agotada", "agotado"),
        (r"\b(sola)\s+o\s+(solo)\b", "sola", "solo"),
        (r"\b(traducida)\s+o\s+(traducido)\b", "traducida", "traducido"),
    ]
    for pat, fem, masc in pair_patterns:
        rep = masc if male else fem
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)

    # Palabras frecuentes en singular.
    word_map = {
        "femenino": {
            "amigo": "amiga",
            "gran amigo": "gran amiga",
            "esclavo": "esclava",
            "rezagado": "rezagada",
            "partido": "partida",
            "frío": "fría",
            "ingrato": "ingrata",
        },
        "masculino": {
            "amiga": "amigo",
            "gran amiga": "gran amigo",
            "esclava": "esclavo",
            "rezagada": "rezagado",
            "partida": "partido",
            "fría": "frío",
            "ingrata": "ingrato",
        },
    }
    target = word_map["masculino" if male else "femenino"]
    for src, dst in target.items():
        out = re.sub(
            rf"\b{re.escape(src)}\b",
            lambda m: _apply_case(m.group(0), dst),
            out,
            flags=re.IGNORECASE,
        )
    # "manual" es sustantivo masculino: no debe quedar "manual fría" al ajustar género.
    out = re.sub(r"\b(manual)\s+fría\b", r"\1 frío", out, flags=re.IGNORECASE)
    return out


def _neutralize_spanish_style(html: str) -> str:
    """Convierte voseo rioplatense a español estándar (tú) y limpia construcciones rotas (p. ej. *sobre tú*)."""
    if not html:
        return html
    out = unescape(html)
    # Frases con "vos" antes del reemplazo genérico vos→tú (evita *sobre tú*, *con tú*, etc.).
    phrase_first: list[tuple[str, str]] = [
        (r"\btraducerte\s+a\s+vos\b", "traducirte a ti"),
        (r"\btraducirte\s+a\s+vos\b", "traducirte a ti"),
        (r"\bsobre\s+vos\b", "sobre ti"),
        (r"\bpara\s+vos\b", "para ti"),
        (r"\bcon\s+vos\b", "contigo"),
        (r"\bde\s+vos\b", "de ti"),
        (r"\ba\s+vos\b", "a ti"),
        (r"\bsin\s+vos\b", "sin ti"),
        (r"\ben\s+vos\b", "en ti"),
        (r"\bni\s+vos\b", "ni tú"),
        (r"\by\s+vos\b", "y tú"),
        (r"\bque\s+vos\b", "que tú"),
        (r"\bmolestás\s+con\s+vos\b", "molestas contigo"),
        (r"\bcon\s+vos\s+por\b", "contigo por"),
        (r"\bacuerdo\s+silencioso\s+con\s+vos\b", "acuerdo silencioso contigo"),
        (r"\blo\s+que\s+vos\b", "lo que tú"),
        (r"\bparte\s+de\s+vos\b", "parte de ti"),
        (r"\bcuando\s+vos\b", "cuando tú"),
        (r"\bsolo\s+vos\b", "solo tú"),
        (r"\bdonde\s+vos\b", "donde tú"),
        (r"\bcomo\s+vos\b", "como tú"),
        (r"\bque\s+vos\s+te\b", "que tú te"),
        (r"\bni\s+vos\s+te\b", "ni tú te"),
    ]
    for pat, rep in phrase_first:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    replacements: list[tuple[str, str]] = [
        (r"\bvos\b", "tú"),
        (r"\bsos\b", "eres"),
        (r"\btenés\b", "tienes"),
        (r"\bpodés\b", "puedes"),
        (r"\bquerés\b", "quieres"),
        (r"\bdecís\b", "dices"),
        (r"\bhacés\b", "haces"),
        (r"\bsentís\b", "sientes"),
        (r"\bdejás\b", "dejas"),
        (r"\bdejá\b", "deja"),
        (r"\bpedís\b", "pides"),
        (r"\belegís\b", "eliges"),
        (r"\bsanás\b", "sanas"),
        (r"\bpeleás\b", "peleas"),
        (r"\bnombrás\b", "nombras"),
        (r"\bnecesitás\b", "necesitas"),
        (r"\bignorás\b", "ignoras"),
        (r"\bintegrás\b", "integras"),
        (r"\bcomparás\b", "comparas"),
        (r"\brespondés\b", "respondes"),
        (r"\bbuscás\b", "buscas"),
        (r"\blevantás\b", "levantas"),
        (r"\biniciás\b", "inicias"),
        (r"\bcerrás\b", "cierras"),
        (r"\bdisparás\b", "disparas"),
        (r"\bcontestás\b", "contestas"),
        (r"\brepetís\b", "repites"),
        (r"\bdefendés\b", "defiendes"),
        (r"\bprotegés\b", "proteges"),
        (r"\bencendés\b", "enciendes"),
        (r"\bprendés\b", "prendes"),
        (r"\btemés\b", "temes"),
        (r"\bamás\b", "amas"),
        (r"\bleés\b", "lees"),
        (r"\btardás\b", "tardas"),
        (r"\badministrás\b", "administras"),
        (r"\bsoltáis\b", "sueltas"),
        (r"\bmentís\b", "mientes"),
        (r"\bnegociás\b", "negocias"),
        (r"\baguantás\b", "aguantas"),
        (r"\bhacelo\b", "hazlo"),
        (r"\bmirá\b", "mira"),
        (r"\bvolvé\b", "vuelve"),
        (r"\bquedate\b", "quédate"),
        (r"\bdecilo\b", "dilo"),
        (r"\bcreés\b", "crees"),
        (r"\bmirás\b", "miras"),
        (r"\bsabés\b", "sabes"),
        (r"\bmostrás\b", "muestras"),
        (r"\bsostenés\b", "sostienes"),
        (r"\bnegás\b", "niegas"),
        (r"\bevitás\b", "evitas"),
        (r"\bcomprás\b", "compras"),
        (r"\btraducís\b", "traduces"),
        (r"\bperdés\b", "pierdes"),
        (r"\bguardás\b", "guardas"),
        (r"\bresolvés\b", "resuelves"),
        (r"\bafinás\b", "afinas"),
        (r"\bvolvés\b", "vuelves"),
        (r"\bcedés\b", "cedes"),
        (r"\bsuavizás\b", "suavizas"),
        (r"\bdesviás\b", "desvías"),
        (r"\bdelegás\b", "delegas"),
        (r"\banticipás\b", "anticipas"),
        (r"\bcorregís\b", "corriges"),
        (r"\bsupervisás\b", "supervisas"),
        (r"\bconvertís\b", "conviertes"),
        (r"\bmolestás\b", "molestas"),
        (r"\bolvidás\b", "olvidas"),
        (r"\bencontrás\b", "encuentras"),
        (r"\bempezás\b", "empiezas"),
        (r"\bterminás\b", "terminas"),
        (r"\banulás\b", "anulas"),
        (r"\bimaginá\b", "imagina"),
        (r"\bdecí\b", "di"),
        (r"\bescribí\b", "escribe"),
        (r"\benviala\b", "envíala"),
        (r"\bactuás\b", "actúas"),
        (r"\bpreferís\b", "prefieres"),
        (r"\baflojás\b", "aflojas"),
        (r"\bpensás\b", "piensas"),
        (r"\busás\b", "usas"),
        (r"\bexplicás\b", "explicas"),
        (r"\bexagerás\b", "exageras"),
        (r"\bpronunciás\b", "pronuncias"),
        (r"\bfingís\b", "finges"),
        (r"\bconfiás\b", "confías"),
        (r"\batravesás\b", "atraviesas"),
        (r"\bentendés\b", "entiendes"),
        (r"\bsoltás\b", "sueltas"),
        (r"\bte\s+resentís\b", "te resientes"),
        (r"\bresentís\b", "te resientes"),
        (r"\bte\s+mentís\b", "te mientes"),
        (r"\bculpás\b", "culpas"),
        (r"\bllamás\b", "llamas"),
        (r"\bquedás\b", "quedas"),
        (r"\benterás\b", "enteras"),
        (r"\baplicás\b", "aplicas"),
        (r"\babrís\b", "abres"),
        (r"\bordenás\b", "ordenas"),
        (r"\bPodés\b", "Puedes"),
        (r"\bElegí\b", "Elige"),
        (r"\bDejá\b", "Deja"),
        (r"\bDevolvés\b", "Devuelves"),
        (r"\bPará\.</b>", "Pausa.</b>"),
        (r"\bPará\.\s", "Pausa. "),
        (r"\bNotás\b", "Notas"),
        (r"\bnotás\b", "notas"),
        (r"\bintentás\b", "intentas"),
        (r"\bconfundís\b", "confundes"),
        (r"\breprimís\b", "reprimes"),
        (r"\bnegociá\b", "negocia"),
        (r"\bpostergás\b", "postergas"),
        (r"\bpriorizás\b", "priorizas"),
        (r"\bmetés\b", "metes"),
        (r"\bcomés\b", "comes"),
        (r"\bhonrás\b", "honras"),
        (r"\bposponés\b", "pospones"),
        (r"\bescuchás\b", "escuchas"),
        (r"\bmodulás\b", "modulas"),
        (r"\bDetectás\b", "Detectas"),
        (r"\bdetectás\b", "detectas"),
        (r"\bpreparás\b", "preparas"),
        (r"\bcambiás\b", "cambias"),
        (r"\bmovés\b", "mueves"),
        (r"\brecordás\b", "recuerdas"),
        (r"\bsolés\b", "sueles"),
        (r"\bandás\b", "andas"),
        (r"\bskipeás\b", "saltas"),
    ]
    for pat, rep in replacements:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    out = re.sub(r"\bno es castigo,\s*es\b", "significa", out, flags=re.IGNORECASE)
    out = re.sub(r"\bno es (adorno|drama|meme),\s*es\b", "significa", out, flags=re.IGNORECASE)
    return out


def _upgrade_tone_global(html: str) -> str:
    """Empuja el tono a presente directo y evita matices tibios."""
    if not html:
        return html
    out = html
    replacements: list[tuple[str, str]] = [
        (r"\bsuele sentirse como\b", "lo viviste como"),
        (r"\bsuele sentirse\b", "se te quedó grabado como"),
        (r"\bsuele reflejarse así\b", "se te manifiesta así"),
        (r"\bsuele reflejarse\b", "se te refleja"),
        (r"\bsuele percibirse como\b", "se percibe como"),
        (r"\bsuele percibirse\b", "se percibe"),
        (r"\bsuele transmitir\b", "transmite"),
        (r"\bsuele marcar\b", "marca"),
        (r"\bsuele traer\b", "trae"),
        (r"\bsuele leerse como\b", "se lee como"),
        (r"\bpuede indicar\b", "esto muestra que"),
        (r"\bpuede ser\b", "se vuelve"),
        (r"\btiende a\b", "terminas"),
        (r"\bse vive como\b", "lo viviste como"),
        (r"\ben la práctica\b", "en tu vida real"),
        (r"\bprobable\b", "latente"),
    ]
    for pat, rep in replacements:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    return out


def _impact_seed_line(p: SoulProfile, key: str, sign: str, elem: str, rng: random.Random) -> str:
    """Línea de impacto dinámica por sección para sostener intensidad global."""
    np = (p.nombre_pila or "").strip() or ((p.nombre or "").split()[0] if p.nombre else "tú")
    section_clause = {
        "section_codigo_nombre": "cada vez que te nombras sin presencia, te alejas de tu centro.",
        "section_eco_ancestros": "cargar la historia familiar te dio fuerza, pero también te enseñó a callarte.",
        "section_esencia_signo": "tu reflejo automático aparece antes de que puedas explicarlo.",
        "section_esencia_elemento": "tu cuerpo decide rápido y tu mente llega tarde a justificarlo.",
        "section_planeta": "el mismo conflicto vuelve hasta que cambias la forma de responder.",
        "section_totem": "tu instinto te avisa cuando te están pidiendo que te traiciones.",
        "section_arcangel": "poner límites todavía te activa culpa aunque sepas que son necesarios.",
        "section_gema": "la sensibilidad que ocultas es justamente la que te orienta.",
        "section_sabiduria_oriental": "tu ritmo profundo no negocia con la ansiedad del entorno.",
        "section_numerologia": "tus números muestran dónde estás repitiendo decisiones por inercia.",
        "section_hilo": "intentas sostener dos verdades opuestas y eso te consume energía.",
        "section_poder_sombra": "la parte que escondes termina tomando el volante por ti.",
        "section_respira": "si no paras, confundes urgencia con destino.",
        "section_pregunta_alma": "la respuesta que evitas ya se siente en el cuerpo.",
        "section_mensaje_personal": "este cierre te pide elegirte con hechos, no con promesas.",
    }.get(key, "tu patrón pide una decisión distinta hoy.")
    openers = (
        "Esto es lo que te pasa realmente",
        "Esto es lo que no dices en voz alta",
        "Este es el patrón que repites",
    )
    opener = openers[(p.seed + len(key) + p.camino_vida + rng.randint(0, 9999)) % len(openers)]
    return f"<b>{opener}.</b> {np}: {section_clause}"


def _ensure_section_impact(
    key: str,
    html: str,
    p: SoulProfile,
    sign: str,
    elem: str,
    rng: random.Random,
) -> str:
    """Garantiza al menos una línea de alto impacto por sección narrativa."""
    if not key.startswith("section_"):
        return html
    low = html.lower()
    markers = (
        "esto es lo que te pasa realmente",
        "esto es lo que no dices en voz alta",
        "este es el patrón que repites",
        "verdad incómoda",
        "qué te pasa realmente",
        "nudo",
        "hecho.",
        "patrón.",
        "clave.",
        "frase para guardar",
    )
    if any(m in low for m in markers):
        return html
    return f"{_impact_seed_line(p, key, sign, elem, rng)}<br/><br/>{html}"


def _ensure_premium_closure(
    key: str,
    html: str,
    p: SoulProfile,
    sign: str,
    elem: str,
    rng: random.Random,
) -> str:
    """Refuerzo final para cierre emocional consistente (mensaje + contraportada)."""
    if key not in {"section_mensaje_personal", "back_cover"}:
        return html
    np = (p.nombre_pila or "").strip() or ((p.nombre or "").split()[0] if p.nombre else "tú")
    cierre = rng.choice(
        (
            f"<b>Reflexión.</b> {np}, no eres lo que te pasó.<br/>"
            f"<b>Validación.</b> Lo que cargaste tuvo sentido en su momento; hoy puedes soltar culpa sin negar tu historia.<br/>"
            f"<b>Poder.</b> Con {sign} y {elem}, no viniste a desaparecerte: viniste a habitarte.",
            f"<b>Reflexión.</b> {np}, llegaste hasta aquí por sostener más de lo que se veía.<br/>"
            f"<b>Validación.</b> Tu cansancio no fue debilidad: fue señal de que necesitabas otra forma de cuidarte.<br/>"
            f"<b>Poder.</b> Lo que decidas sostener ahora cambia tu historia en tiempo real.",
            f"<b>Reflexión.</b> {np}, tu nombre no te encierra: te orienta.<br/>"
            f"<b>Validación.</b> No estás tarde; estás en el punto exacto para elegir distinto.<br/>"
            f"<b>Poder.</b> Tu verdad deja de pedir permiso cuando la conviertes en acción.",
        ),
    )
    if "reflexión." in html.lower() and "poder." in html.lower():
        return html
    return f"{html}<br/><br/>{cierre}"


def _add_action_clarity(key: str, html: str) -> str:
    """Añade orientación práctica para que cada sección cierre con utilidad concreta."""
    directives = {
        "section_planeta": "Aplicación práctica: observa este patrón durante 7 días y define un límite claro que sí vas a sostener.",
        "section_totem": "Acción concreta: cuando detectes una invasión de límites, responde con una frase breve y firme, sin justificarte de más.",
        "section_arcangel": "Límite saludable: no aceptes vínculos que pidan paz a cambio de silencio.",
        "section_gema": "Fortaleza: tu forma de sentir no es un problema; úsala para elegir mejor dónde invertir tu energía.",
        "section_numerologia": "Conclusión útil: estos números te orientan a decidir qué hábito reforzar y qué patrón cortar.",
        "section_poder_sombra": "Dirección clara: no confundas amor con aguante infinito. Si te desgasta de forma constante, pon límite.",
        "section_pregunta_alma": "Paso siguiente: escribe una respuesta breve y conviértela en una decisión concreta para esta semana.",
        "section_mensaje_personal": "Mensaje central: esto es una fortaleza, no un defecto. No tienes que aceptar falta de respeto de nadie.",
    }
    line = directives.get(key)
    if not line:
        return html
    if line.lower() in html.lower():
        return html
    return f"{html}<br/><br/>{line}"


def _final_narrative_cleanup(html: str) -> str:
    """Limpieza final: sin llaves, sin bloques duplicados, sin frases incompletas."""
    if not html:
        return html
    def _rhythmize_part(part: str) -> str:
        """Solo parte frases en finales de oración; evita cortes en ; o comas que suelen colgar ideas."""
        if "<br/>" in part:
            return part
        plain = re.sub(r"<[^>]+>", " ", part)
        words = re.findall(r"\S+", plain)
        if len(words) < 26:
            return part
        sents = [s.strip() for s in re.split(r"(?<=[\.\!\?])\s+", part) if s.strip()]
        if len(sents) < 2:
            return part
        lens = [len(re.findall(r"\S+", re.sub(r"<[^>]+>", " ", s))) for s in sents]
        if min(lens) < 8 or max(lens) > 36:
            return part
        return "<br/>".join(sents[:5])

    out = re.sub(r"[{}]", "", html)
    parts = [p.strip() for p in out.split("<br/><br/>") if p.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        norm = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", part)).strip().lower()
        if not norm:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        # Asegura cierre mínimo de frase incluso si termina en etiqueta HTML.
        plain_tail = re.sub(r"<[^>]+>\s*$", "", part).rstrip()
        if plain_tail and plain_tail[-1] not in ".!?":
            part = part.rstrip() + "."
        part = _rhythmize_part(part)
        deduped.append(part)
    out = "<br/><br/>".join(deduped)
    out = re.sub(r"(\b\w+\b)(\s+\1\b)+", r"\1", out, flags=re.IGNORECASE)
    return out


def build_narrative(p: SoulProfile) -> BookNarrative:
    nombre = p.nombre
    nombre_pila = p.nombre_pila
    voc = _vocativo(p)
    apellidos = p.apellidos
    sign = sign_label_es(p.signo)
    elem = element_label_es(p.elemento)
    planet = planet_label_es(p.planeta_regente)
    animal = p.animal_chino
    nacimiento = f"{p.birth_day_of_month} de {p.birth_month_name} de {p.fecha.year}"
    firma = universe_fingerprint_code(nombre, p.fecha, p.seed)

    last_err: BaseException | None = None
    for attempt in range(8):
        rng = random.Random(p.seed + attempt * 100_003)
        allow_emergency = attempt >= 6
        try:
            myth = pick_planet_myth(rng, p.planeta_regente)
            shadow_frag = pick_shadow(rng, elem)

            totem_hint = p.totem_file.replace(".png", "").replace("_", " ").strip()
            gema_hint = p.gema_file.replace(".png", "").replace("_", " ").strip()
            arch_label = p.arcangel_file.replace(".png", "").replace("_", " ").strip()
            arch_label = re.sub(r"(?i)\barcangel\b", "arcángel", arch_label)

            cover_subtitle = nombre
            cover_sacred_line = f"Lectura sagrada para <i>{nombre}</i>"
            cover_tagline = compose_cover_tagline(rng, p, sign, elem, nacimiento)
            cover_editorial_line = rng.choice(
                (
                    "Mapa personal · una sola vida, una sola lectura",
                    "Editorial de lujo · texto a medida",
                    "Carta viva · lectura escrita para tu nombre",
                )
            )
            cover_volume_title = "Mapa del Alma"
            a1, a2, a3 = compose_afirmaciones_secas(rng, p, nombre, sign, elem)
            raw = BookNarrative(
                cover_subtitle=cover_subtitle,
                cover_tagline=cover_tagline,
                cover_sacred_line=cover_sacred_line,
                cover_editorial_line=cover_editorial_line,
                cover_volume_title=cover_volume_title,
                section_codigo_nombre=compose_codigo_nombre(rng, p, nombre_pila, sign, elem),
                section_eco_ancestros=compose_eco_ancestros(rng, p, apellidos, nombre_pila, elem),
                section_esencia_signo=compose_esencia_signo(
                    rng, p, voc, (nombre_pila or "").strip() or voc, sign, elem
                ),
                section_esencia_elemento=compose_esencia_elemento(rng, p, voc, sign, elem),
                section_planeta=compose_planeta_regente(rng, p, voc, planet, myth),
                section_totem=compose_totem_pagina(rng, p, voc, totem_hint, sign),
                section_arcangel=compose_arcangel_pagina(rng, p, voc, arch_label, planet),
                section_gema=compose_gema_poder_pagina(rng, p, voc, gema_hint, sign, elem),
                section_sabiduria_oriental=compose_sabiduria_oriental_pagina(
                    rng, p, voc, animal, sign
                ),
                section_numerologia=compose_numerologia_sagrada_pagina(
                    rng, p, voc, sign, animal
                ),
                section_hilo=compose_hilo_contradiccion(
                    rng,
                    p,
                    sign,
                    totem_hint,
                    nombre_pila,
                    apellidos,
                    nombre,
                ),
                section_poder_sombra=compose_poder_y_sombra(
                    rng, p, voc, sign, elem, planet, shadow_frag
                ),
                section_respira=compose_respira_intercalada(rng, voc),
                section_pregunta_alma=compose_pregunta_alma(rng, p, voc, nombre_pila),
                section_mensaje_personal=compose_mensaje_personal_climax(
                    rng, p, voc, sign, elem
                ),
                affirmation_one=a1,
                affirmation_two=a2,
                affirmation_three=a3,
                back_cover=compose_back_cover_human(
                    rng, p, nombre, sign, planet, animal, nacimiento
                ),
                universe_firma_line=(
                    f"<b>Código del universo de tu lectura</b><br/><br/>"
                    f"{firma}<br/><br/>"
                    "<b>Qué es y de dónde sale:</b> una huella única calculada con tu nombre, tu fecha de nacimiento y la semilla matemática de este mapa.<br/><br/>"
                    "<b>Para qué se utiliza:</b> para validar que esta lectura corresponde a tus datos y distinguirla de cualquier otra.<br/><br/>"
                    "<b>Cómo se activa:</b> mira el sello durante un minuto, respira tres veces y declara en voz alta una decisión que sí vas a cumplir esta semana."
                ),
            )

            cleaned: dict[str, str] = {}
            for k, v in raw.as_dict().items():
                if isinstance(v, str):
                    sanitized = _safe_finalize(k, v, allow_emergency=allow_emergency)
                    sanitized = _genderize_text(sanitized, p.sexo)
                    sanitized = _ensure_section_impact(k, sanitized, p, sign, elem, rng)
                    sanitized = _ensure_premium_closure(k, sanitized, p, sign, elem, rng)
                    sanitized = _neutralize_spanish_style(sanitized)
                    sanitized = _upgrade_tone_global(sanitized)
                    capped = _trim_html_words(sanitized, _density_cap_for_key(k))
                    capped = _final_narrative_cleanup(capped)
                    cleaned[k] = _safe_finalize(k, capped, allow_emergency=allow_emergency)

            return BookNarrative(**cleaned)
        except NarrativeValidationError as exc:
            last_err = exc
            continue
    raise RuntimeError(
        "No se pudo generar una narrativa válida tras varios intentos."
    ) from last_err
