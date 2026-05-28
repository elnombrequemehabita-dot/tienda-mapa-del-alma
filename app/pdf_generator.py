from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fpdf import FPDF

# ============================================================
# MAPA DEL ALMA - PDF GENERATOR PREMIUM
# IMPORTANTE:
# - Este archivo NO llama OpenAI.
# - Este archivo NO importa app.openai_generator.
# - Solo toma contenido ya generado y arma el PDF.
# - Si falta contenido_openai, falla claro para no gastar dinero.
# ============================================================

PAGE_W = 215.9
PAGE_H = 279.4
PRINT_DPI = 300
PAGE_PX_W = int(round(8.5 * PRINT_DPI))
PAGE_PX_H = int(round(11.0 * PRINT_DPI))
INTERIOR_BODY_FONT_SIZE = 13.4
INTERIOR_BODY_BOTTOM_SAFE_MM = 24.0
INTERIOR_BODY_LINE_RATIO = 0.58
PRINT_MIN_INTERIOR_PAGES = 48

COSMIC_BG_KEYS = {
    "zodiaco",
    "zodiaco_chino",
    "numerologia",
    "animal_espiritual",
    "angel_guardian",
    "piedra_energetica",
    "mensaje_final",
    "esencia_alma",
}
TRANSFORMATION_BG_KEYS = {"energia", "dones", "sombras", "herida", "proposito"}
HIGH_CONTRAST_BG_KEYS = {
    "mensaje_alma",
    "origen_nombre",
    "linaje_apellidos",
    "esencia",
    "energia",
    "zodiaco",
    "zodiaco_chino",
    "numerologia",
    "animal_espiritual",
    "angel_guardian",
    "piedra_energetica",
    "dones",
    "sombras",
    "herida",
    "proposito",
    "amor_vinculos",
    "dinero_camino",
    "ritual_personalizado",
    "afirmaciones",
    "mensaje_final",
    "esencia_alma",
}

SECTION_TITLES = {
    "mensaje_alma": "Mensaje de tu alma",
    "origen_nombre": "Origen simbólico del nombre",
    "linaje_apellidos": "Linaje de tus apellidos",
    "esencia": "Esencia profunda",
    "energia": "Energía esencial",
    "zodiaco": "Zodiaco occidental",
    "zodiaco_chino": "Zodiaco chino",
    "numerologia": "Numerología del alma",
    "animal_espiritual": "Animal tótem",
    "angel_guardian": "Ángel de la guarda",
    "piedra_energetica": "Piedra energética",
    "dones": "Dones y talentos",
    "sombras": "Lado oscuro y sombras",
    "herida": "Herida emocional y sanación",
    "proposito": "Propósito de alma",
    "amor_vinculos": "Amor y vínculos",
    "dinero_camino": "Dinero, trabajo y expansión",
    "ritual_personalizado": "Ritual personalizado",
    "afirmaciones": "Afirmaciones de poder",
    "mensaje_final": "Mensaje final",
    "esencia_alma": "Esencia del Alma",
}

SECTION_ORDER = [
    "mensaje_alma",
    "origen_nombre",
    "linaje_apellidos",
    "esencia",
    "energia",
    "zodiaco",
    "zodiaco_chino",
    "numerologia",
    "animal_espiritual",
    "angel_guardian",
    "piedra_energetica",
    "dones",
    "sombras",
    "herida",
    "proposito",
    "amor_vinculos",
    "dinero_camino",
    "ritual_personalizado",
    "afirmaciones",
    "mensaje_final",
    "esencia_alma",
]

PAGE_HEADINGS = {
    "mensaje_alma": "Lo que tu alma reconoce",
    "origen_nombre": "El sonido que te nombra",
    "linaje_apellidos": "La memoria que camina contigo",
    "esencia": "Tu centro verdadero",
    "energia": "Tu campo magnético",
    "zodiaco": "Tu cielo de nacimiento",
    "zodiaco_chino": "Tu instinto ancestral",
    "numerologia": "Tus números guía",
    "animal_espiritual": "Tu guía instintiva",
    "angel_guardian": "Tu protección invisible",
    "piedra_energetica": "Tu amuleto mineral",
    "dones": "Lo que viniste a ofrecer",
    "sombras": "Lo que pide conciencia",
    "herida": "La herida que busca cuidado",
    "proposito": "La dirección de tu alma",
    "amor_vinculos": "Tu forma de amar",
    "dinero_camino": "Trabajo, valor y expansión",
    "ritual_personalizado": "Tu práctica de poder",
    "afirmaciones": "Palabras que te reordenan",
    "mensaje_final": "Cierre del mapa",
    "esencia_alma": "La verdad central de tu nombre",
}

SECTION_TITLES_I18N = {
    "en": {
        "mensaje_alma": "Message from your soul",
        "origen_nombre": "Symbolic origin of the name",
        "linaje_apellidos": "Lineage of your surnames",
        "esencia": "Deep essence",
        "energia": "Essential energy",
        "zodiaco": "Western zodiac",
        "zodiaco_chino": "Chinese zodiac",
        "numerologia": "Numerology of the soul",
        "animal_espiritual": "Spirit animal",
        "angel_guardian": "Guardian angel",
        "piedra_energetica": "Energy stone",
        "dones": "Gifts and talents",
        "sombras": "Shadows and inner work",
        "herida": "Emotional wound and healing",
        "proposito": "Soul purpose",
        "amor_vinculos": "Love and bonds",
        "dinero_camino": "Money, work and expansion",
        "ritual_personalizado": "Personalized ritual",
        "afirmaciones": "Power affirmations",
        "mensaje_final": "Final message",
        "esencia_alma": "Essence of the Soul",
    },
    "pt": {
        "mensaje_alma": "Mensagem da sua alma",
        "origen_nombre": "Origem simbólica do nome",
        "linaje_apellidos": "Linhagem dos seus sobrenomes",
        "esencia": "Essência profunda",
        "energia": "Energia essencial",
        "zodiaco": "Zodíaco ocidental",
        "zodiaco_chino": "Zodíaco chinês",
        "numerologia": "Numerologia da alma",
        "animal_espiritual": "Animal totêmico",
        "angel_guardian": "Anjo da guarda",
        "piedra_energetica": "Pedra energética",
        "dones": "Dons e talentos",
        "sombras": "Lado sombrio e sombras",
        "herida": "Ferida emocional e cura",
        "proposito": "Propósito da alma",
        "amor_vinculos": "Amor e vínculos",
        "dinero_camino": "Dinheiro, trabalho e expansão",
        "ritual_personalizado": "Ritual personalizado",
        "afirmaciones": "Afirmações de poder",
        "mensaje_final": "Mensagem final",
        "esencia_alma": "Essência da Alma",
    },
    "fr": {
        "mensaje_alma": "Message de votre âme",
        "origen_nombre": "Origine symbolique du prénom",
        "linaje_apellidos": "Lignée de vos noms",
        "esencia": "Essence profonde",
        "energia": "Énergie essentielle",
        "zodiaco": "Zodiaque occidental",
        "zodiaco_chino": "Zodiaque chinois",
        "numerologia": "Numérologie de l'âme",
        "animal_espiritual": "Animal spirituel",
        "angel_guardian": "Ange gardien",
        "piedra_energetica": "Pierre énergétique",
        "dones": "Dons et talents",
        "sombras": "Ombres intérieures",
        "herida": "Blessure émotionnelle et guérison",
        "proposito": "But de l'âme",
        "amor_vinculos": "Amour et liens",
        "dinero_camino": "Argent, travail et expansion",
        "ritual_personalizado": "Rituel personnalisé",
        "afirmaciones": "Affirmations de pouvoir",
        "mensaje_final": "Message final",
        "esencia_alma": "Essence de l'Âme",
    },
    "it": {
        "mensaje_alma": "Messaggio della tua anima",
        "origen_nombre": "Origine simbolica del nome",
        "linaje_apellidos": "Lignaggio dei tuoi cognomi",
        "esencia": "Essenza profonda",
        "energia": "Energia essenziale",
        "zodiaco": "Zodiaco occidentale",
        "zodiaco_chino": "Zodiaco cinese",
        "numerologia": "Numerologia dell'anima",
        "animal_espiritual": "Animale spirituale",
        "angel_guardian": "Angelo custode",
        "piedra_energetica": "Pietra energetica",
        "dones": "Doni e talenti",
        "sombras": "Ombre interiori",
        "herida": "Ferita emotiva e guarigione",
        "proposito": "Scopo dell'anima",
        "amor_vinculos": "Amore e legami",
        "dinero_camino": "Denaro, lavoro ed espansione",
        "ritual_personalizado": "Rituale personalizzato",
        "afirmaciones": "Affermazioni di potere",
        "mensaje_final": "Messaggio finale",
        "esencia_alma": "Essenza dell'Anima",
    },
}

PAGE_HEADINGS_I18N = {
    "en": {
        "mensaje_alma": "What your soul recognizes",
        "origen_nombre": "The sound that names you",
        "linaje_apellidos": "The memory that walks with you",
        "esencia": "Your true center",
        "energia": "Your magnetic field",
        "zodiaco": "Your birth sky",
        "zodiaco_chino": "Your ancestral instinct",
        "numerologia": "Your guiding numbers",
        "animal_espiritual": "Your instinctive guide",
        "angel_guardian": "Your invisible protection",
        "piedra_energetica": "Your mineral amulet",
        "dones": "What you came to offer",
        "sombras": "What asks for awareness",
        "herida": "The wound seeking care",
        "proposito": "The direction of your soul",
        "amor_vinculos": "Your way of loving",
        "dinero_camino": "Work, value and expansion",
        "ritual_personalizado": "Your practice of power",
        "afirmaciones": "Words that reorder you",
        "mensaje_final": "Closing the map",
        "esencia_alma": "The central truth of your name",
    }
}

PALETTES = {
    "portada": ((18, 15, 35), (253, 247, 230), (214, 174, 91), (72, 51, 97)),
    "contraportada": ((18, 15, 35), (253, 247, 230), (214, 174, 91), (72, 51, 97)),
    "mensaje_alma": ((23, 20, 44), (253, 247, 230), (214, 174, 91), (72, 51, 97)),
    "origen_nombre": ((26, 25, 52), (252, 245, 226), (211, 169, 88), (58, 64, 116)),
    "linaje_apellidos": ((35, 25, 34), (252, 242, 223), (204, 153, 76), (93, 54, 56)),
    "esencia": ((30, 22, 48), (253, 245, 229), (218, 174, 94), (89, 59, 112)),
    "energia": ((20, 36, 42), (248, 244, 226), (203, 161, 79), (42, 92, 95)),
    "zodiaco": ((18, 28, 57), (250, 244, 229), (218, 179, 99), (45, 72, 130)),
    "zodiaco_chino": ((42, 25, 30), (252, 241, 223), (204, 148, 73), (119, 58, 54)),
    "numerologia": ((27, 25, 55), (252, 247, 231), (213, 169, 87), (75, 63, 126)),
    "animal_espiritual": ((20, 42, 36), (248, 242, 224), (202, 156, 78), (47, 101, 84)),
    "angel_guardian": ((26, 29, 57), (253, 248, 233), (222, 184, 105), (74, 77, 130)),
    "piedra_energetica": ((31, 27, 57), (251, 246, 232), (213, 169, 92), (86, 68, 137)),
    "dones": ((22, 41, 42), (250, 245, 228), (207, 162, 82), (55, 105, 103)),
    "sombras": ((33, 25, 44), (250, 240, 227), (201, 149, 74), (82, 64, 93)),
    "herida": ((42, 26, 42), (253, 243, 231), (211, 157, 83), (122, 63, 83)),
    "proposito": ((20, 31, 55), (250, 244, 228), (215, 172, 91), (59, 83, 128)),
    "amor_vinculos": ((48, 25, 42), (253, 242, 229), (215, 161, 88), (133, 61, 84)),
    "dinero_camino": ((21, 40, 31), (248, 244, 226), (201, 156, 77), (57, 101, 75)),
    "ritual_personalizado": ((35, 28, 56), (252, 245, 231), (215, 169, 92), (95, 70, 126)),
    "afirmaciones": ((29, 28, 57), (253, 248, 234), (222, 181, 97), (79, 76, 133)),
    "mensaje_final": ((28, 24, 48), (252, 245, 228), (215, 169, 89), (82, 64, 108)),
    "esencia_alma": ((24, 22, 45), (252, 245, 228), (218, 174, 94), (84, 62, 112)),
}

SECTION_BACKGROUND_IMAGES = {
    "mensaje_alma": ["mensaje_alma_fondo_1.png"],
    "origen_nombre": ["origen_nombre_fondo_1.png"],
    "linaje_apellidos": ["linaje_apellidos_fondo_1.png"],
    "esencia": ["esencia_profunda_fondo_1.png"],
    "energia": ["energia_esencial_fondo_1.png"],
    "zodiaco": ["zodiaco_occidental_fondo_1.png"],
    "zodiaco_chino": ["zodiaco_chino_fondo_1.png"],
    "numerologia": ["numerologia_alma_fondo_1.png"],
    "animal_espiritual": ["animal_totem_fondo_1.png"],
    "angel_guardian": ["angel_guarda_fondo_1.png"],
    "piedra_energetica": ["piedra_energetica_fondo_1.png"],
    "dones": ["dones_talentos_fondo_1.png"],
    "sombras": ["sombras_fondo_1.png"],
    "herida": ["herida_sanacion_fondo_1.png"],
    "proposito": ["proposito_alma_fondo_1.png"],
    "amor_vinculos": ["amor_vinculos_fondo_1.png"],
    "dinero_camino": ["dinero_trabajo_expansion_fondo_1.png"],
    "ritual_personalizado": ["ritual_personalizado_fondo_1.png"],
    "afirmaciones": ["afirmaciones_poder_fondo_1.png"],
    "mensaje_final": ["mensaje_final_fondo_1.png"],
    "esencia_alma": ["esencia_del_alma_fondo_1.png"],
}


def _project_root() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name == "app":
        return here.parent.parent
    return here.parent


def _assets_img_dir() -> Path:
    opciones = [
        # Carpeta real usada por la tienda actual. Debe tener prioridad.
        _project_root() / "app" / "assets" / "imagenes",
        _project_root() / "assets" / "imagenes",
        _project_root() / "app" / "mapa_del_alma_v2" / "assets" / "imagenes",
        Path(__file__).resolve().parent / "assets" / "imagenes",
        Path(__file__).resolve().parent / "mapa_del_alma_v2" / "assets" / "imagenes",
    ]

    for folder in opciones:
        if folder.exists():
            return folder

    return opciones[0]


def _fonts_dir() -> Path:
    opciones = [
        _project_root() / "app" / "mapa_del_alma_v2" / "assets" / "fuentes",
        _project_root() / "app" / "assets" / "fuentes",
        _project_root() / "assets" / "fuentes",
        Path(__file__).resolve().parent / "mapa_del_alma_v2" / "assets" / "fuentes",
        Path(__file__).resolve().parent / "assets" / "fuentes",
    ]

    for folder in opciones:
        if folder.exists():
            return folder

    return opciones[0]


def _clean_text(text: Any, keep_breaks: bool = False) -> str:
    if text is None:
        return ""

    txt = str(text).strip()

    replacements = {
        "“": '"',
        "”": '"',
        "’": "'",
        "‘": "'",
        "—": "-",
        "–": "-",
        "…": "...",
        "\u200b": "",
        "\ufeff": "",
        "\u00a0": " ",
        "\t": " ",
        "\r": "\n" if keep_breaks else " ",
    }

    for a, b in replacements.items():
        txt = txt.replace(a, b)

    if keep_breaks:
        lines = [re.sub(r"[ ]+", " ", line).strip() for line in txt.split("\n")]
        txt = "\n".join(line for line in lines if line)
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        return txt.strip()

    return re.sub(r"\s+", " ", txt).strip()


def _safe(text: Any, keep_breaks: bool = False) -> str:
    return _clean_text(text, keep_breaks=keep_breaks).encode("latin-1", "replace").decode("latin-1")


def _palette(key: str):
    return PALETTES.get(key, PALETTES["mensaje_alma"])


def _nombre_completo(datos: dict[str, Any]) -> str:
    nombre = _clean_text(datos.get("nombre")) or "Alma"
    apellidos = _clean_text(datos.get("apellidos"))
    nombre_completo = _clean_text(datos.get("nombre_completo"))

    if nombre_completo:
        return nombre_completo

    return f"{nombre} {apellidos}".strip()


def _format_birthdate(datos: dict[str, Any], value: Any) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""

    parsed = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return raw

    months = {
        "es": [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ],
        "en": [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        "pt": [
            "Janeiro",
            "Fevereiro",
            "Março",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro",
        ],
        "fr": [
            "Janvier",
            "Février",
            "Mars",
            "Avril",
            "Mai",
            "Juin",
            "Juillet",
            "Août",
            "Septembre",
            "Octobre",
            "Novembre",
            "Décembre",
        ],
        "it": [
            "Gennaio",
            "Febbraio",
            "Marzo",
            "Aprile",
            "Maggio",
            "Giugno",
            "Luglio",
            "Agosto",
            "Settembre",
            "Ottobre",
            "Novembre",
            "Dicembre",
        ],
    }
    lang = _idioma_pdf(datos)
    month = months.get(lang, months["es"])[parsed.month - 1]

    if lang == "en":
        return f"{month} {parsed.day}, {parsed.year}"
    if lang in ("fr", "it"):
        return f"{parsed.day} {month} {parsed.year}"

    return f"{parsed.day} de {month} de {parsed.year}"


def _sexo_normalizado(valor: Any) -> str:
    sexo = _clean_text(valor).lower()

    if sexo in ("mujer", "femenino", "f", "female", "ella", "nina", "niña"):
        return "mujer"

    if sexo in ("hombre", "masculino", "m", "male", "el", "él", "nino", "niño"):
        return "hombre"

    return "neutral"


def _idioma_normalizado(valor: Any) -> str:
    raw = _clean_text(valor).lower().replace("_", "-")
    code = raw.split("-", 1)[0] if raw else "es"
    return code if code in {"es", "en", "pt", "fr", "it"} else "es"


def _idioma_pdf(datos: dict[str, Any]) -> str:
    return _idioma_normalizado(datos.get("idioma") or datos.get("language") or datos.get("locale") or "es")


def _fixed_text(datos: dict[str, Any], key: str) -> str:
    lang = _idioma_pdf(datos)
    texts = {
        "es": {
            "birthdate": "Fecha de nacimiento",
            "symbolic_reading_for": "Lectura simbólica personalizada para",
            "her": "ella",
            "him": "él",
            "soul": "su alma",
            "complete": "TU MAPA ESTÁ COMPLETO",
            "back_intro": "este libro fue creado como una lectura simbólica para recordar tu nombre, tu energía y la fuerza que puedes elegir encarnar.",
            "includes": "ESTE LIBRO INCLUYE",
            "footer": "Mapa del Alma - El nombre que me habita - Página",
            "brand": "El nombre que me habita",
            "intro_title": "CÓMO LEER TU MAPA",
            "intro_subtitle": "Este PDF no está pensado para leerse de prisa. Está creado para que encuentres frases que te acompañen, preguntas que ordenen tu historia y símbolos que puedas volver a mirar.",
            "intro_steps_title": "RITUAL DE LECTURA",
            "intro_steps": [
                "Lee primero el mensaje de tu alma sin intentar analizarlo todo.",
                "Subraya tres frases que te muevan por dentro o te den claridad.",
                "Vuelve a una sección por día durante la primera semana.",
                "Cierra con el ritual, las afirmaciones y una intención clara para integrar la lectura.",
            ],
            "intro_close": "Lo valioso de este mapa no es que te diga quién eres: es que te devuelve lenguaje para reconocerte con más verdad.",
            "opening_label": "Lectura inicial",
            "deep_label": "Profundización",
            "integration_label": "Integración",
            "section_label": "Portal",
            "items": [
                "21 lecturas interiores personalizadas",
                "Nombre, linaje, esencia y energía",
                "Zodiaco occidental y zodiaco chino",
                "Numerología, animal tótem, ángel y piedra",
                "Dones, sombras, herida, propósito y vínculos",
                "Dinero, ritual, afirmaciones y mensaje final",
                "Esencia del Alma, ritual y mensaje final",
            ],
        },
        "en": {
            "birthdate": "Birth date",
            "symbolic_reading_for": "Personalized symbolic reading for",
            "her": "her",
            "him": "him",
            "soul": "their soul",
            "complete": "YOUR MAP IS COMPLETE",
            "back_intro": "this book was created as a symbolic reading to remember your name, your energy, and the strength you can choose to embody.",
            "includes": "THIS BOOK INCLUDES",
            "footer": "Map of the Soul - The name that lives in me - Page",
            "brand": "The name that lives in me",
            "intro_title": "HOW TO READ YOUR MAP",
            "intro_subtitle": "This PDF is not meant to be rushed. It is created so you can find phrases that stay with you, questions that organize your story, and symbols you can return to.",
            "intro_steps_title": "READING RITUAL",
            "intro_steps": [
                "Read the message from your soul first, without trying to analyze everything.",
                "Underline three phrases that move you or give you clarity.",
                "Return to one section per day during the first week.",
                "Close with the ritual, the affirmations, and a clear intention to integrate the reading.",
            ],
            "intro_close": "The value of this map is not that it tells you who you are: it gives you language to recognize yourself with more truth.",
            "opening_label": "Opening reading",
            "deep_label": "Deepening",
            "integration_label": "Integration",
            "section_label": "Portal",
            "items": [
                "21 personalized inner readings",
                "Name, lineage, essence, and energy",
                "Western zodiac and Chinese zodiac",
                "Numerology, spirit animal, angel, and stone",
                "Gifts, shadows, wound, purpose, and bonds",
                "Money, ritual, affirmations, and final message",
                "Essence of the Soul, ritual, and final message",
            ],
        },
        "pt": {
            "birthdate": "Data de nascimento",
            "symbolic_reading_for": "Leitura simbólica personalizada para",
            "her": "ela",
            "him": "ele",
            "soul": "sua alma",
            "complete": "SEU MAPA ESTÁ COMPLETO",
            "back_intro": "este livro foi criado como uma leitura simbólica para recordar seu nome, sua energia e a força que você pode escolher encarnar.",
            "includes": "ESTE LIVRO INCLUI",
            "footer": "Mapa da Alma - O nome que me habita - Página",
            "brand": "O nome que me habita",
            "intro_title": "COMO LER O SEU MAPA",
            "intro_subtitle": "Este PDF não foi pensado para ser lido com pressa. Ele foi criado para que você encontre frases que acompanham, perguntas que organizam sua história e símbolos aos quais possa voltar.",
            "intro_steps_title": "RITUAL DE LEITURA",
            "intro_steps": [
                "Leia primeiro a mensagem da sua alma, sem tentar analisar tudo.",
                "Sublinhe três frases que mexam com você ou tragam clareza.",
                "Volte a uma seção por dia durante a primeira semana.",
                "Feche com o ritual, as afirmações e uma intenção clara para integrar a leitura.",
            ],
            "intro_close": "O valor deste mapa não é dizer quem você é: é devolver linguagem para que você se reconheça com mais verdade.",
            "opening_label": "Leitura inicial",
            "deep_label": "Aprofundamento",
            "integration_label": "Integração",
            "section_label": "Portal",
            "items": [
                "21 leituras interiores personalizadas",
                "Nome, linhagem, essência e energia",
                "Zodíaco ocidental e zodíaco chinês",
                "Numerologia, animal totêmico, anjo e pedra",
                "Dons, sombras, ferida, propósito e vínculos",
                "Dinheiro, ritual, afirmações e mensagem final",
                "Essência da Alma, ritual e mensagem final",
            ],
        },
        "fr": {
            "birthdate": "Date de naissance",
            "symbolic_reading_for": "Lecture symbolique personnalisée pour",
            "her": "elle",
            "him": "lui",
            "soul": "son âme",
            "complete": "VOTRE CARTE EST COMPLÈTE",
            "back_intro": "ce livre a été créé comme une lecture symbolique pour rappeler votre nom, votre énergie et la force que vous pouvez choisir d'incarner.",
            "includes": "CE LIVRE COMPREND",
            "footer": "Carte de l'Âme - Le nom qui m'habite - Page",
            "brand": "Le nom qui m'habite",
            "intro_title": "COMMENT LIRE VOTRE CARTE",
            "intro_subtitle": "Ce PDF n'est pas fait pour être lu trop vite. Il est créé pour vous offrir des phrases qui accompagnent, des questions qui ordonnent votre histoire et des symboles auxquels revenir.",
            "intro_steps_title": "RITUEL DE LECTURE",
            "intro_steps": [
                "Lisez d'abord le message de votre âme sans chercher à tout analyser.",
                "Soulignez trois phrases qui vous touchent ou vous donnent de la clarté.",
                "Revenez à une section par jour pendant la première semaine.",
                "Terminez avec le rituel, les affirmations et une intention claire pour intégrer la lecture.",
            ],
            "intro_close": "La valeur de cette carte n'est pas de vous dire qui vous êtes: elle vous rend un langage pour vous reconnaître avec plus de vérité.",
            "opening_label": "Lecture initiale",
            "deep_label": "Approfondissement",
            "integration_label": "Intégration",
            "section_label": "Portail",
            "items": [
                "21 lectures intérieures personnalisées",
                "Nom, lignée, essence et énergie",
                "Zodiaque occidental et zodiaque chinois",
                "Numérologie, animal spirituel, ange et pierre",
                "Dons, ombres, blessure, but et liens",
                "Argent, rituel, affirmations et message final",
                "Essence de l'Âme, rituel et message final",
            ],
        },
        "it": {
            "birthdate": "Data di nascita",
            "symbolic_reading_for": "Lettura simbolica personalizzata per",
            "her": "lei",
            "him": "lui",
            "soul": "la sua anima",
            "complete": "LA TUA MAPPA È COMPLETA",
            "back_intro": "questo libro è stato creato come lettura simbolica per ricordare il tuo nome, la tua energia e la forza che puoi scegliere di incarnare.",
            "includes": "QUESTO LIBRO INCLUDE",
            "footer": "Mappa dell'Anima - Il nome che mi abita - Pagina",
            "brand": "Il nome che mi abita",
            "intro_title": "COME LEGGERE LA TUA MAPPA",
            "intro_subtitle": "Questo PDF non è pensato per essere letto di fretta. È creato perché tu possa trovare frasi che ti accompagnano, domande che ordinano la tua storia e simboli a cui tornare.",
            "intro_steps_title": "RITUALE DI LETTURA",
            "intro_steps": [
                "Leggi prima il messaggio della tua anima senza cercare di analizzare tutto.",
                "Sottolinea tre frasi che ti muovono dentro o ti danno chiarezza.",
                "Torna a una sezione al giorno durante la prima settimana.",
                "Chiudi con il rituale, le affermazioni e un'intenzione chiara per integrare la lettura.",
            ],
            "intro_close": "Il valore di questa mappa non è dirti chi sei: ti restituisce un linguaggio per riconoscerti con più verità.",
            "opening_label": "Lettura iniziale",
            "deep_label": "Approfondimento",
            "integration_label": "Integrazione",
            "section_label": "Portale",
            "items": [
                "21 letture interiori personalizzate",
                "Nome, lignaggio, essenza ed energia",
                "Zodiaco occidentale e zodiaco cinese",
                "Numerologia, animale spirituale, angelo e pietra",
                "Doni, ombre, ferita, scopo e legami",
                "Denaro, rituale, affermazioni e messaggio finale",
                "Essenza dell'Anima, rituale e messaggio finale",
            ],
        },
    }
    return texts.get(lang, texts["es"]).get(key, texts["es"].get(key, key))


def _section_title(datos: dict[str, Any], key: str) -> str:
    lang = _idioma_pdf(datos)
    return SECTION_TITLES_I18N.get(lang, {}).get(key, SECTION_TITLES[key])


def _page_heading(datos: dict[str, Any], key: str) -> str:
    lang = _idioma_pdf(datos)
    return PAGE_HEADINGS_I18N.get(lang, {}).get(key, PAGE_HEADINGS.get(key, ""))


def _pedido_id(datos: dict[str, Any]) -> str:
    value = (
        datos.get("pedido_id")
        or datos.get("order_id")
        or datos.get("id")
        or datos.get("codigo_pedido")
        or ""
    )
    return _clean_text(value)


def _visual_seed(datos: dict[str, Any]) -> str:
    existing = _clean_text(datos.get("_pdf_visual_seed"))
    if existing:
        return existing

    pedido = _pedido_id(datos)
    if pedido:
        seed = f"pedido-{pedido}"
    else:
        nombre = _nombre_completo(datos)
        fecha = _clean_text(datos.get("fecha_nacimiento") or datos.get("fecha") or "")
        seed = f"temporal-{nombre}-{fecha}-{int(time.time())}"

    datos["_pdf_visual_seed"] = seed
    return seed


def _find_image_by_names(names: list[str]) -> Optional[Path]:
    folder = _assets_img_dir()

    if not folder.exists():
        return None

    for name in names:
        for ext in (".jpeg", ".jpg", ".png", ".webp"):
            candidate = folder / f"{name}{ext}"
            if candidate.exists():
                return candidate

    return None



def _debug_assets() -> bool:
    return str(__import__("os").environ.get("PDF_DEBUG_ASSETS", "")).strip().lower() in ("1", "true", "yes", "on")


def _prepared_image_for_pdf(path: Path) -> Path:
    """
    Convierte imagenes problemáticas (CMYK/progresivas/WEBP/PNG raros) a un formato seguro
    para fpdf2, sin cambiar tus archivos originales.
    """
    try:
        from PIL import Image, ImageOps
    except Exception:
        return path

    try:
        Image.MAX_IMAGE_PIXELS = None
        path = Path(path)
        cache_dir = _project_root() / "output" / "_pdf_image_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        stat = path.stat()

        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        max_long_edge = 3600
        has_alpha = img.mode in ("RGBA", "LA") or ("transparency" in img.info)
        cache_ext = ".png" if has_alpha else ".jpg"
        cache_name = f"{path.stem}_{stat.st_size}_{int(stat.st_mtime)}_print{max_long_edge}{cache_ext}"
        cache_path = cache_dir / cache_name

        if cache_path.exists() and cache_path.stat().st_size > 0:
            return cache_path

        longest = max(img.size)
        if longest > max_long_edge:
            ratio = max_long_edge / float(longest)
            new_size = (max(1, int(img.size[0] * ratio)), max(1, int(img.size[1] * ratio)))
            try:
                resampling = Image.Resampling.LANCZOS
            except Exception:
                resampling = getattr(Image, "LANCZOS", 1)
            img = img.resize(new_size, resampling)

        if has_alpha:
            if img.mode not in ("RGBA", "LA"):
                img = img.convert("RGBA")
            img.save(cache_path, format="PNG", optimize=True)
        else:
            if img.mode not in ("RGB",):
                img = img.convert("RGB")
            img.save(cache_path, format="JPEG", quality=94, optimize=True)

        return cache_path
    except Exception as exc:
        if _debug_assets():
            print(f"[PDF_DEBUG_ASSETS] No se pudo preparar imagen {path}: {exc}")
        return path


def _background_darken_alpha(key: str) -> float:
    if key == "esencia_alma":
        return 0.58
    if key in COSMIC_BG_KEYS or key in TRANSFORMATION_BG_KEYS:
        return 0.50
    if key in HIGH_CONTRAST_BG_KEYS:
        return 0.38
    return 0.22


def _prepared_page_canvas_for_pdf(path: Path, key: str, darken_alpha: float = 0.0) -> Path:
    """
    Crea una copia cacheada con la proporcion exacta Letter.
    No deforma ni corta el arte principal: rellena las diferencias de proporcion
    con una extension suave del propio fondo.
    """
    try:
        from PIL import Image, ImageFilter, ImageOps
    except Exception:
        return path

    try:
        Image.MAX_IMAGE_PIXELS = None
        path = Path(path)
        alpha = max(0.0, min(0.75, float(darken_alpha)))
        cache_dir = _project_root() / "output" / "_pdf_image_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        stat = path.stat()
        alpha_tag = int(round(alpha * 100))
        cache_path = cache_dir / (
            f"{path.stem}_{stat.st_size}_{int(stat.st_mtime)}_letter{PAGE_PX_W}x{PAGE_PX_H}_dark{alpha_tag}_{key}.jpg"
        )

        if cache_path.exists() and cache_path.stat().st_size > 0:
            return cache_path

        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            try:
                resampling = Image.Resampling.LANCZOS
            except Exception:
                resampling = getattr(Image, "LANCZOS", 1)

            src_w, src_h = img.size
            cover_scale = max(PAGE_PX_W / src_w, PAGE_PX_H / src_h)
            cover_size = (max(1, int(src_w * cover_scale)), max(1, int(src_h * cover_scale)))
            cover = img.resize(cover_size, resampling)
            cover_left = max(0, (cover_size[0] - PAGE_PX_W) // 2)
            cover_top = max(0, (cover_size[1] - PAGE_PX_H) // 2)
            cover = cover.crop((cover_left, cover_top, cover_left + PAGE_PX_W, cover_top + PAGE_PX_H))
            cover = cover.filter(ImageFilter.GaussianBlur(radius=18))

            contain_scale = min(PAGE_PX_W / src_w, PAGE_PX_H / src_h)
            contain_size = (max(1, int(src_w * contain_scale)), max(1, int(src_h * contain_scale)))
            foreground = img.resize(contain_size, resampling)
            paste_x = (PAGE_PX_W - contain_size[0]) // 2
            paste_y = (PAGE_PX_H - contain_size[1]) // 2
            cover.paste(foreground, (paste_x, paste_y))

            if alpha > 0:
                black = Image.new("RGB", cover.size, (0, 0, 0))
                cover = Image.blend(cover, black, alpha)

            cover.save(cache_path, format="JPEG", quality=94, optimize=True)

        return cache_path
    except Exception as exc:
        if _debug_assets():
            print(f"[PDF_DEBUG_ASSETS] No se pudo preparar lienzo Letter {path}: {exc}")
        return path


def _prepared_background_for_pdf(path: Path, key: str) -> Path:
    return _prepared_page_canvas_for_pdf(path, key, darken_alpha=_background_darken_alpha(key))


def _pdf_image(pdf: "MapaPDF", path: Path, x: float, y: float, w: float, h: Optional[float] = None) -> None:
    safe_path = _prepared_image_for_pdf(Path(path))
    if _debug_assets():
        print(f"[PDF_DEBUG_ASSETS] Usando imagen: {safe_path}")
    if h is None:
        pdf.image(str(safe_path), x, y, w=w)
    else:
        pdf.image(str(safe_path), x, y, w=w, h=h)


def _prepared_logo_for_pdf(path: Path) -> Path:
    """
    El logo oficial es de alta resolucion. Para no inflar cada PDF, se usa
    una copia PNG transparente optimizada solo para el tamano visible.
    """
    try:
        from PIL import Image, ImageOps
    except Exception:
        return path

    try:
        Image.MAX_IMAGE_PIXELS = None
        path = Path(path)
        cache_dir = _project_root() / "output" / "_pdf_image_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        stat = path.stat()
        max_long_edge = 900
        cache_path = cache_dir / f"{path.stem}_{stat.st_size}_{int(stat.st_mtime)}_logo{max_long_edge}.png"

        if cache_path.exists() and cache_path.stat().st_size > 0:
            return cache_path

        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            longest = max(img.size)
            if longest > max_long_edge:
                ratio = max_long_edge / float(longest)
                new_size = (max(1, int(img.size[0] * ratio)), max(1, int(img.size[1] * ratio)))
                try:
                    resampling = Image.Resampling.LANCZOS
                except Exception:
                    resampling = getattr(Image, "LANCZOS", 1)
                img = img.resize(new_size, resampling)

            if img.mode != "RGBA":
                img = img.convert("RGBA")
            img.save(cache_path, format="PNG", optimize=True)

        return cache_path
    except Exception as exc:
        if _debug_assets():
            print(f"[PDF_DEBUG_ASSETS] No se pudo preparar logo {path}: {exc}")
        return path


def _pdf_image_cover(pdf: "MapaPDF", path: Path, x: float, y: float, w: float, h: float) -> None:
    """
    Coloca una imagen completa dentro de la pagina, sin aplastarla ni recortarla.
    Si la proporcion no coincide exactamente con Letter, centra el arte sobre
    un fondo oscuro de sangre completa para que sea imprimible sin bordes blancos.
    """
    safe_path = _prepared_image_for_pdf(Path(path))
    pdf.set_fill_color(6, 10, 24)
    pdf.rect(x, y, w, h, "F")

    try:
        from PIL import Image

        with Image.open(safe_path) as img:
            img_w, img_h = img.size

        if img_w <= 0 or img_h <= 0:
            _pdf_image(pdf, safe_path, x, y, w, h)
            return

        img_ratio = img_w / img_h
        box_ratio = w / h

        if img_ratio > box_ratio:
            draw_w = w
            draw_h = w / img_ratio
            draw_x = x
            draw_y = y + (h - draw_h) / 2
        else:
            draw_h = h
            draw_w = h * img_ratio
            draw_x = x + (w - draw_w) / 2
            draw_y = y

        if _debug_assets():
            print(f"[PDF_DEBUG_ASSETS] Fondo completo: {safe_path} -> x={draw_x:.2f}, y={draw_y:.2f}, w={draw_w:.2f}, h={draw_h:.2f}")

        pdf.image(str(safe_path), draw_x, draw_y, w=draw_w, h=draw_h)
    except Exception:
        _pdf_image(pdf, safe_path, x, y, w=w)


def _section_official_image_options(key: str) -> list[Path]:
    folder = _assets_img_dir()
    opciones: list[Path] = []

    for name in SECTION_BACKGROUND_IMAGES.get(key, []):
        candidate = folder / name
        if candidate.exists() and candidate.is_file():
            opciones.append(candidate)

    return opciones


def _rotation_state_path() -> Path:
    path = _project_root() / "output" / "_pdf_image_rotation_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_rotation_state() -> dict[str, str]:
    path = _rotation_state_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_rotation_state(state: dict[str, str]) -> None:
    try:
        path = _rotation_state_path()
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        temp_path.replace(path)
    except Exception:
        # Nunca debe romper el PDF por no poder guardar el historial visual.
        pass


def _choose_section_image(key: str, datos: dict[str, Any]) -> Optional[Path]:
    """
    Devuelve el fondo correcto para cada pagina.

    IMPORTANTE:
    - Usa exclusivamente las imagenes oficiales de app/assets/imagenes.
    - No usa variantes antiguas por seccion.
    - La asignacion por seccion es fija para mantener identidad visual.
    """
    opciones = _section_official_image_options(key)

    if not opciones:
        return None

    if len(opciones) == 1:
        return opciones[0]
    return opciones[0]


def _draw_gradient_bg(pdf: "MapaPDF", key: str) -> None:
    bg, _cream, _gold, accent = _palette(key)

    steps = 60

    for i in range(steps):
        ratio = i / max(1, steps - 1)

        r = int(bg[0] * (1 - ratio) + accent[0] * ratio * 0.35)
        g = int(bg[1] * (1 - ratio) + accent[1] * ratio * 0.35)
        b = int(bg[2] * (1 - ratio) + accent[2] * ratio * 0.35)

        pdf.set_fill_color(r, g, b)
        pdf.rect(0, i * PAGE_H / steps, PAGE_W, PAGE_H / steps + 0.5, "F")


def _draw_overlay(pdf: "MapaPDF", color: tuple[int, int, int], alpha: float) -> None:
    if alpha <= 0:
        return
    used_alpha = _with_alpha(pdf, alpha)
    if not used_alpha:
        return
    pdf.set_fill_color(int(color[0]), int(color[1]), int(color[2]))
    pdf.rect(0, 0, PAGE_W, PAGE_H, "F")
    _restore_alpha(pdf, used_alpha)


def _draw_rounded_transparent_rect(
    pdf: "MapaPDF",
    x: float,
    y: float,
    w: float,
    h: float,
    radius: float,
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
    *,
    fill_alpha: float = 0.50,
    border_alpha: float = 0.78,
    line_width: float = 0.28,
) -> None:
    return


def _draw_page_border(pdf: "MapaPDF", key: str) -> None:
    return


def _page_bg(
    pdf: "MapaPDF",
    key: str,
    datos: dict[str, Any],
    overlay: float = 0.04,
    *,
    draw_border: bool = True,
) -> None:
    img = _choose_section_image(key, datos)

    if img:
        try:
            _pdf_image_cover(pdf, _prepared_background_for_pdf(img, key), 0, 0, PAGE_W, PAGE_H)
        except Exception as exc:
            if _debug_assets():
                print(f"[PDF_DEBUG_ASSETS] Fallo cargando fondo {img}: {exc}")
            _draw_gradient_bg(pdf, key)
    else:
        if _debug_assets():
            print(f"[PDF_DEBUG_ASSETS] No hay fondo para seccion: {key} en {_assets_img_dir()}")
        _draw_gradient_bg(pdf, key)

    # Estilo editorial: el texto vive directamente sobre la ilustracion.
    # Los fondos de seccion ya se preparan oscurecidos en cache; no usamos cajas.


def _required_image(filename: str) -> Path:
    path = _assets_img_dir() / filename
    if not path.exists():
        raise RuntimeError(f"No existe la imagen obligatoria del PDF: {path}")
    return path


def _draw_fixed_page_image(pdf: "MapaPDF", filename: str, *, darken_alpha: float = 0.0) -> None:
    prepared = _prepared_page_canvas_for_pdf(_required_image(filename), f"fixed_{filename}", darken_alpha=darken_alpha)
    _pdf_image_cover(pdf, prepared, 0, 0, PAGE_W, PAGE_H)


def _mark_no_footer(pdf: "MapaPDF") -> None:
    pages = getattr(pdf, "no_footer_pages", None)
    if isinstance(pages, set):
        pages.add(pdf.page_no())


def _set_text_color(pdf: "MapaPDF", color: tuple[int, int, int]) -> None:
    pdf.set_text_color(int(color[0]), int(color[1]), int(color[2]))


def _with_alpha(pdf: "MapaPDF", alpha: float) -> bool:
    try:
        pdf.set_alpha(max(0.0, min(1.0, alpha)))
        return True
    except Exception:
        return False


def _restore_alpha(pdf: "MapaPDF", used: bool) -> None:
    if used:
        try:
            pdf.set_alpha(1)
        except Exception:
            pass


def _begin_text_outline(
    pdf: "MapaPDF",
    line_width: float = 0.045,
    color: tuple[int, int, int] = (64, 44, 18),
) -> bool:
    try:
        pdf.set_draw_color(int(color[0]), int(color[1]), int(color[2]))
        pdf.set_line_width(line_width)
        pdf._out("2 Tr")
        return True
    except Exception:
        return False


def _end_text_outline(pdf: "MapaPDF", used: bool) -> None:
    if used:
        try:
            pdf._out("0 Tr")
        except Exception:
            pass


def _shadow_cell(
    pdf: "MapaPDF",
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    font: str,
    style: str,
    size: float,
    color: tuple[int, int, int],
    align: str = "C",
    shadow_alpha: float = 0.30,
) -> None:
    pdf.set_font(font, style, size)
    shadow_alpha = min(shadow_alpha, 0.14)

    used_alpha = _with_alpha(pdf, shadow_alpha)
    _set_text_color(pdf, (0, 0, 0))
    pdf.set_xy(x + 0.18, y + 0.22)
    pdf.cell(w, h, _safe(text), align=align)
    _restore_alpha(pdf, used_alpha)

    _set_text_color(pdf, color)
    pdf.set_xy(x, y)
    outline = _begin_text_outline(pdf, 0.010 if size < 12 else 0.018)
    pdf.cell(w, h, _safe(text), align=align)
    _end_text_outline(pdf, outline)


def _shadow_multi_cell(
    pdf: "MapaPDF",
    x: float,
    y: float,
    w: float,
    line_h: float,
    text: str,
    *,
    font: str,
    style: str,
    size: float,
    color: tuple[int, int, int],
    align: str = "C",
    shadow_alpha: float = 0.28,
    keep_breaks: bool = False,
) -> None:
    pdf.set_font(font, style, size)
    shadow_alpha = min(shadow_alpha, 0.12)

    used_alpha = _with_alpha(pdf, shadow_alpha)
    _set_text_color(pdf, (0, 0, 0))
    pdf.set_xy(x + 0.16, y + 0.20)
    pdf.multi_cell(w, line_h, _safe(text, keep_breaks=keep_breaks), align=align)
    _restore_alpha(pdf, used_alpha)

    _set_text_color(pdf, color)
    pdf.set_xy(x, y)
    outline = _begin_text_outline(pdf, 0.010 if size < 12 else 0.014)
    pdf.multi_cell(w, line_h, _safe(text, keep_breaks=keep_breaks), align=align)
    _end_text_outline(pdf, outline)


def _draw_logo_if_exists(pdf: "MapaPDF", x: float, y: float, w: float) -> None:
    # Logo oficial solicitado: app/assets/imagenes/logo.png
    # Mantiene alternativas para no romper instalaciones anteriores.
    logo = _find_image_by_names(["logo", "Logo", "LOGO", "el_nombre_que_me_habita", "sello"])

    if logo:
        try:
            safe_logo = _prepared_logo_for_pdf(logo)
            try:
                pdf.set_alpha(0.96)
            except Exception:
                pass
            pdf.image(str(safe_logo), x, y, w=w)
            try:
                pdf.set_alpha(1)
            except Exception:
                pass
        except Exception:
            pass


def _draw_cover_logo(pdf: "MapaPDF", *, back: bool = False) -> None:
    logo_w = 28
    x = PAGE_W - logo_w - 18
    y = PAGE_H - logo_w - 15
    _draw_logo_if_exists(pdf, x, y, logo_w)


def _find_book_title_image() -> Optional[Path]:
    candidates = [
        _project_root() / "app" / "static" / "img" / "mapa.png",
        _project_root() / "app" / "static" / "img" / "mapa.PNG",
        _find_image_by_names(["mapa", "Mapa", "MAPA", "mapa_del_alma"]),
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)

    return None


def _line_height(font_size: float) -> float:
    # Interlineado comodo sin empujar el texto hasta el pie de pagina.
    return font_size * INTERIOR_BODY_LINE_RATIO


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\wáéíóúÁÉÍÓÚñÑüÜ]+\b", _clean_text(text), flags=re.UNICODE))


def _estimate_lines(pdf: "MapaPDF", text: str, width: float, font_size: float) -> int:
    pdf.set_font(pdf.font_body, "", font_size)

    words = _safe(text).split()

    if not words:
        return 1

    lines = 1
    current = ""

    for word in words:
        test = f"{current} {word}".strip()

        if pdf.get_string_width(test) <= width:
            current = test
        else:
            lines += 1
            current = word

    return lines


def _fit_font_for_panel(
    pdf: "MapaPDF",
    text: str,
    width: float,
    height: float,
    start: float = 8.2,
    minimum: float = 6.4,
) -> float:
    size = start

    while size >= minimum:
        if _panel_needed_height(pdf, text, width, size) <= height:
            return size

        size -= 0.15

    return minimum


def _panel_needed_height(pdf: "MapaPDF", text: str, width: float, font_size: float) -> float:
    paragraphs = [
        _clean_text(p)
        for p in re.split(r"\n\s*\n", _clean_text(text, keep_breaks=True))
        if _clean_text(p)
    ] or [_clean_text(text)]
    lines = sum(_estimate_lines(pdf, paragraph, width - 6, font_size) for paragraph in paragraphs)
    return lines * _line_height(font_size) + max(0, len(paragraphs) - 1) * 2.4 + 4.0


def _draw_soft_panel(
    pdf: "MapaPDF",
    x: float,
    y: float,
    w: float,
    h: float,
    key: str,
    alpha: float = 0.86,
) -> None:
    return


def _write_panel_text(
    pdf: "MapaPDF",
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    key: str,
    font_size: float,
) -> None:
    paragraphs = [
        _clean_text(p)
        for p in re.split(r"\n\s*\n", _clean_text(text, keep_breaks=True))
        if _clean_text(p)
    ]

    if not paragraphs:
        return

    line_h = _line_height(font_size)
    current_y = y + 1.2

    for idx, paragraph in enumerate(paragraphs):
        if idx > 0:
            current_y += 1.8
        _shadow_multi_cell(
            pdf,
            x + 3,
            current_y,
            w - 6,
            line_h,
            paragraph,
            font=pdf.font_body,
            style="",
            size=font_size,
            color=(246, 225, 172),
            align="J",
            shadow_alpha=0.10,
        )
        current_y = pdf.get_y()


def _strip_internal_labels(text: str) -> str:
    text = _clean_text(text, keep_breaks=True)
    if not text:
        return ""
    labels = [
        "PROFUNDIZACION",
        "PROFUNDIZACIÓN",
        "INTEGRACION",
        "INTEGRACIÓN",
        "LECTURA INICIAL",
        "PRIMERA LECTURA",
    ]
    for label in labels:
        text = re.sub(rf"(?im)^\s*{label}\s*:?\s*", "", text)
    return _clean_text(text, keep_breaks=True)


def _duplicate_key(text: str) -> str:
    base = _clean_text(text).lower()
    base = re.sub(r"[^\wáéíóúñü]+", " ", base, flags=re.UNICODE)
    words = base.split()
    return " ".join(words[:90])


def _sentence_key(text: str) -> str:
    base = _clean_text(text).lower()
    base = re.sub(r"[^\wáéíóúñü]+", " ", base, flags=re.UNICODE)
    words = base.split()
    return " ".join(words[:18])


def _dedupe_repeated_sentences(text: str) -> str:
    sentences = [
        _clean_text(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", _clean_text(text))
        if _clean_text(sentence)
    ]
    if not sentences:
        return _clean_text(text)

    seen: set[str] = set()
    result: list[str] = []
    for sentence in sentences:
        key = _sentence_key(sentence)
        if key and key in seen:
            continue
        seen.add(key)
        result.append(sentence)
    return " ".join(result).strip()


def _dedupe_section_paragraphs(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        for paragraph in re.split(r"\n\s*\n", _strip_internal_labels(part)):
            paragraph = _clean_text(paragraph)
            if not paragraph:
                continue
            key = _duplicate_key(paragraph)
            if key and key in seen:
                continue
            seen.add(key)
            result.append(_dedupe_repeated_sentences(paragraph))
    return result


def _section_combined_text(sec: dict[str, str]) -> str:
    paragraphs = _dedupe_section_paragraphs(
        [
            _clean_text(sec.get("primera_lectura")),
            _clean_text(sec.get("profundizacion")),
            _clean_text(sec.get("integracion")),
        ]
    )
    return "\n\n".join(paragraphs)


def _split_text_for_pages(
    pdf: "MapaPDF",
    text: str,
    width: float,
    height: float,
    *,
    minimum_size: float,
) -> list[str]:
    text = _clean_text(text, keep_breaks=True)
    if not text:
        return []

    total_words = _count_words(text)
    if total_words < 120 and _panel_needed_height(pdf, text, width, minimum_size) <= height:
        return [text]

    units = [
        _clean_text(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", _clean_text(text))
        if _clean_text(sentence)
    ]
    if not units:
        units = _clean_text(text).split()

    if total_words >= 120:
        target = total_words / 2
        first_units: list[str] = []
        second_units: list[str] = []
        current_words = 0

        for index, unit in enumerate(units):
            first_units.append(unit)
            current_words += _count_words(unit)
            remaining_units = len(units) - index - 1
            if current_words >= target and remaining_units > 0:
                second_units = units[index + 1 :]
                break

        first = " ".join(first_units).strip()
        second = " ".join(second_units).strip()
        if first and second:
            first_words = _count_words(first)
            second_words = _count_words(second)
            balanced_enough = min(first_words, second_words) >= max(55, int(total_words * 0.34))
            both_fit = (
                _panel_needed_height(pdf, first, width, minimum_size) <= height
                and _panel_needed_height(pdf, second, width, minimum_size) <= height
            )
            if balanced_enough and both_fit:
                return [first, second]

    def build_greedy_chunks(source_units: list[str]) -> list[str]:
        chunks: list[str] = []
        current = ""
        for unit in source_units:
            candidate = f"{current} {unit}".strip() if current else unit
            if not current or _panel_needed_height(pdf, candidate, width, minimum_size) <= height:
                current = candidate
                continue

            chunks.append(current)
            current = unit

            if _panel_needed_height(pdf, current, width, minimum_size) > height:
                words = current.split()
                current = ""
                for word in words:
                    word_candidate = f"{current} {word}".strip() if current else word
                    if not current or _panel_needed_height(pdf, word_candidate, width, minimum_size) <= height:
                        current = word_candidate
                    else:
                        chunks.append(current)
                        current = word

        if current:
            chunks.append(current)
        return chunks

    greedy_chunks = build_greedy_chunks(units)
    if len(greedy_chunks) <= 1:
        return greedy_chunks

    page_count = len(greedy_chunks)
    total_words = max(1, sum(_count_words(unit) for unit in units))
    target_words = max(95, int(total_words / page_count))

    chunks: list[str] = []
    current = ""
    for index, unit in enumerate(units):
        candidate = f"{current} {unit}".strip() if current else unit
        remaining_units = len(units) - index - 1
        remaining_pages = page_count - len(chunks) - 1
        can_open_next_page = current and len(chunks) < page_count - 1 and remaining_units >= remaining_pages
        fits = _panel_needed_height(pdf, candidate, width, minimum_size) <= height

        if can_open_next_page and (not fits or _count_words(candidate) > target_words):
            chunks.append(current)
            current = unit
            continue

        if not current or fits:
            current = candidate
            continue

        chunks.append(current)
        current = unit

    if current:
        chunks.append(current)

    if len(chunks) > page_count or any(
        _panel_needed_height(pdf, chunk, width, minimum_size) > height for chunk in chunks
    ):
        chunks = greedy_chunks

    return _rebalance_sparse_last_chunk(pdf, chunks, width, height, minimum_size)


def _rebalance_sparse_last_chunk(
    pdf: "MapaPDF",
    chunks: list[str],
    width: float,
    height: float,
    minimum_size: float,
) -> list[str]:
    if len(chunks) <= 1:
        return chunks

    total_words = sum(_count_words(chunk) for chunk in chunks)
    expected_words = max(1, int(total_words / len(chunks)))
    minimum_last_words = min(125, max(80, int(expected_words * 0.58)))

    if _count_words(chunks[-1]) >= minimum_last_words:
        return chunks

    previous_units = [
        _clean_text(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", _clean_text(chunks[-2]))
        if _clean_text(sentence)
    ]
    last_units = [
        _clean_text(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", _clean_text(chunks[-1]))
        if _clean_text(sentence)
    ]
    if len(previous_units) < 2 or not last_units:
        return chunks

    while len(previous_units) > 1 and _count_words(" ".join(last_units)) < minimum_last_words:
        moved = previous_units.pop()
        new_previous = " ".join(previous_units).strip()
        new_last = " ".join([moved, *last_units]).strip()

        if (
            _panel_needed_height(pdf, new_previous, width, minimum_size) <= height
            and _panel_needed_height(pdf, new_last, width, minimum_size) <= height
        ):
            last_units.insert(0, moved)
            chunks[-2] = new_previous
            chunks[-1] = new_last
        else:
            previous_units.append(moved)
            break

    return chunks


def _words_excerpt(text: str, max_words: int = 34) -> str:
    clean = _clean_text(text)
    words = clean.split()

    if len(words) <= max_words:
        return clean

    return " ".join(words[:max_words]).rstrip(".,;:") + "..."


def _pull_quote(text: str) -> str:
    clean = _clean_text(text)
    if not clean:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", clean)
    for sentence in sentences[:3]:
        count = _count_words(sentence)
        if 10 <= count <= 26:
            return sentence

    return _words_excerpt(clean, 24)


def _normalizar_secciones(raw: dict[str, Any]) -> dict[str, dict[str, str]]:
    resultado: dict[str, dict[str, str]] = {}

    frases_prohibidas = [
        "esta seccion se revela",
        "esta sección se revela",
        "lectura simbolica personalizada creada",
        "creada para abrir una conversacion profunda",
        "el modo en que tu nombre habita tu camino",
        "la clave esta en volver al centro",
        "una decision pequena puede ordenar",
        "lo importante es practicar la verdad",
    ]

    for key in SECTION_ORDER:
        node = raw.get(key)

        if not isinstance(node, dict):
            raise RuntimeError(f"Falta la seccion obligatoria en el contenido: {key}")

        primera = _clean_text(node.get("primera_lectura"))
        profunda = _clean_text(node.get("profundizacion"))
        integra = _clean_text(node.get("integracion"))

        for campo, texto in [
            ("primera_lectura", primera),
            ("profundizacion", profunda),
            ("integracion", integra),
        ]:
            if len(texto) < 40:
                raise RuntimeError(
                    f"{key}.{campo} esta vacio o demasiado corto. No se genera PDF malo."
                )

            lower = texto.lower()

            if any(frase in lower for frase in frases_prohibidas):
                raise RuntimeError(
                    f"{key}.{campo} contiene texto generico prohibido. No se genera PDF malo."
                )

        resultado[key] = {
            "primera_lectura": primera,
            "profundizacion": profunda,
            "integracion": integra,
        }

    return resultado


def _extraer_contenido_openai(datos_pedido: dict[str, Any]) -> dict[str, Any]:
    contenido = datos_pedido.get("contenido_openai")

    if contenido is None:
        contenido_path = datos_pedido.get("contenido_openai_path") or datos_pedido.get("json_path")

        if contenido_path:
            path = Path(str(contenido_path))
            if not path.exists():
                raise RuntimeError(f"No existe el JSON de contenido OpenAI: {path}")

            with open(path, "r", encoding="utf-8") as f:
                contenido = json.load(f)

    if not isinstance(contenido, dict):
        raise RuntimeError(
            "Falta contenido_openai. pdf_generator.py no llama OpenAI. "
            "Primero genera el JSON con app.openai_generator y luego pasa ese contenido al PDF."
        )

    secciones = (
        contenido.get("secciones")
        or contenido.get("secciones_editoriales")
        or contenido
    )

    if not isinstance(secciones, dict) or not secciones:
        raise RuntimeError("contenido_openai no contiene secciones validas.")

    return _normalizar_secciones(secciones)


class MapaPDF(FPDF):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.font_title = "Times"
        self.font_subtitle = "Times"
        self.font_body = "Times"
        self.font_accent = "Times"
        self.font_script = "Times"
        self.font_subtitle_strong_style = "B"

        self.title_font_options: list[tuple[str, str]] = [("Times", "B")]
        self.subtitle_font_options: list[tuple[str, str]] = [("Times", "I")]
        self.name_font_options: list[tuple[str, str]] = [("Times", "I")]
        self._font_choice_cache: dict[str, tuple[str, str]] = {}
        self._font_rng = random.Random(f"{time.time_ns()}-{random.random()}")
        self.no_footer_pages: set[int] = set()

        self._register_fonts()
        self.set_auto_page_break(False)
        self.alias_nb_pages()

    def _try_font(self, family: str, style: str, filename: str) -> bool:
        path = _fonts_dir() / filename

        if not path.exists():
            return False

        try:
            self.add_font(family, style, str(path))
            return True
        except Exception:
            try:
                self.add_font(family, style, str(path), uni=True)
                return True
            except Exception:
                return False

    def _register_fonts(self) -> None:
        title_options: list[tuple[str, str]] = []
        subtitle_options: list[tuple[str, str]] = []
        name_options: list[tuple[str, str]] = []

        # Titulos y nombre con una letra corrida elegante, consistente en todo el libro.
        if self._try_font("PlaywriteIE", "", "PlaywriteIE-VariableFont_wght.ttf"):
            self.font_script = "PlaywriteIE"
            self.font_title = "PlaywriteIE"
            title_options.append(("PlaywriteIE", ""))
            name_options.append(("PlaywriteIE", ""))

        # Titulos editoriales premium: sobrios, misticos y legibles.
        if self._try_font("CinzelPDF", "", "Cinzel-VariableFont_wght.ttf"):
            title_options.append(("CinzelPDF", ""))
            self.font_title = self.font_title if self.font_title != "Times" else "CinzelPDF"

        if self._try_font("PlayfairSC", "", "PlayfairDisplaySC-Regular.ttf"):
            title_options.append(("PlayfairSC", ""))
            self.font_title = self.font_title if self.font_title != "Times" else "PlayfairSC"
            if self._try_font("PlayfairSC", "B", "PlayfairDisplaySC-Bold.ttf"):
                title_options.append(("PlayfairSC", "B"))
            if self._try_font("PlayfairSC", "I", "PlayfairDisplaySC-Italic.ttf"):
                subtitle_options.append(("PlayfairSC", "I"))
                name_options.append(("PlayfairSC", "I"))
            self._try_font("PlayfairSC", "BI", "PlayfairDisplaySC-BoldItalic.ttf")

        # Subtitulos cursivos/corridos: dan sensacion de libro de lujo sin sacrificar lectura.
        if self._try_font("LoraPDF", "", "Lora-VariableFont_wght.ttf"):
            self.font_body = "LoraPDF"
            if self._try_font("LoraPDF", "I", "Lora-Italic-VariableFont_wght.ttf"):
                subtitle_options.append(("LoraPDF", "I"))
                name_options.append(("LoraPDF", "I"))

        if self._try_font("MerriPDF", "", "Merriweather-VariableFont_opsz,wdth,wght.ttf"):
            self.font_body = "MerriPDF"
            self.font_accent = "MerriPDF"
            if self._try_font("MerriPDF", "I", "Merriweather-Italic-VariableFont_opsz,wdth,wght.ttf"):
                subtitle_options.append(("MerriPDF", "I"))
                name_options.append(("MerriPDF", "I"))

        # Fuentes limpias para metadatos y apoyo visual.
        if self._try_font("MontserratPDF", "", "Montserrat-VariableFont_wght.ttf"):
            self.font_subtitle = "MontserratPDF"
            self.font_subtitle_strong_style = ""
            if self._try_font("MontserratPDF", "I", "Montserrat-Italic-VariableFont_wght.ttf"):
                subtitle_options.append(("MontserratPDF", "I"))

        if self._try_font("PoppinsPDF", "", "Poppins-Regular.ttf"):
            self.font_subtitle = "PoppinsPDF"
            self.font_subtitle_strong_style = "B" if self._try_font("PoppinsPDF", "B", "Poppins-SemiBold.ttf") else ""
            self._try_font("PoppinsPDF", "I", "Poppins-Italic.ttf")

        if title_options:
            self.title_font_options = title_options
        if subtitle_options:
            self.subtitle_font_options = subtitle_options
            self.font_accent = subtitle_options[0][0]
        if name_options:
            self.name_font_options = name_options

    def _choose_font_once(self, bucket: str, key: str, options: list[tuple[str, str]]) -> tuple[str, str]:
        cache_key = f"{bucket}:{key}"
        if cache_key not in self._font_choice_cache:
            self._font_choice_cache[cache_key] = options[0]
        return self._font_choice_cache[cache_key]

    def title_font_for(self, key: str) -> tuple[str, str]:
        return self._choose_font_once("title", key, self.title_font_options)

    def subtitle_font_for(self, key: str) -> tuple[str, str]:
        return self._choose_font_once("subtitle", key, self.subtitle_font_options)

    def name_font_for(self, key: str) -> tuple[str, str]:
        return self._choose_font_once("name", key, self.name_font_options)

    def subtitle_strong_style(self) -> str:
        return self.font_subtitle_strong_style

    def footer(self) -> None:
        if self.page_no() <= 1 or self.page_no() in self.no_footer_pages:
            return

        footer_y = PAGE_H - 7.1
        text = f"{_fixed_text({'idioma': getattr(self, 'language', 'es')}, 'footer')} {self.page_no()}"
        _shadow_cell(
            self,
            0,
            footer_y + 0.35,
            PAGE_W,
            4.0,
            text,
            font=self.font_subtitle,
            style=self.subtitle_strong_style(),
            size=7.4,
            color=(255, 246, 220),
            align="C",
            shadow_alpha=0.18,
        )


def _draw_header_block(pdf: MapaPDF, key: str, datos: dict[str, Any]) -> None:
    _bg, _cream, gold, _accent = _palette(key)

    title = _section_title(datos, key)
    heading = _page_heading(datos, key)

    nombre = _profile_nombre(datos)
    fecha = _profile_fecha_formatted(datos)

    title_font, title_style = pdf.title_font_for(key)

    _shadow_cell(
        pdf,
        22,
        17.4,
        PAGE_W - 44,
        11.2,
        title,
        font=title_font,
        style=title_style,
        size=29.8,
        color=gold,
        align="C",
        shadow_alpha=0.28,
    )

    _shadow_cell(
        pdf,
        25,
        40.6,
        PAGE_W - 50,
        8.6,
        heading,
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=18.0,
        color=(248, 244, 234),
        align="C",
        shadow_alpha=0.26,
    )

    meta = f"{nombre}"
    if fecha:
        meta = f"{nombre} · {fecha}"

    _shadow_cell(
        pdf,
        25,
        55.0,
        PAGE_W - 50,
        7.8,
        meta,
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=14.3,
        color=(255, 248, 226),
        align="C",
        shadow_alpha=0.24,
    )

    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.18)
    pdf.line(52, 69.2, PAGE_W - 52, 69.2)


def _draw_gold_divider(pdf: MapaPDF, x: float, y: float, w: float, key: str) -> None:
    _bg, _cream, gold, accent = _palette(key)
    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.22)
    pdf.line(x, y, x + w, y)
    pdf.set_fill_color(*gold)
    try:
        pdf.ellipse(x + (w / 2) - 1.2, y - 1.2, 2.4, 2.4, "F")
    except Exception:
        pdf.rect(x + (w / 2) - 1.1, y - 1.1, 2.2, 2.2, "F")
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.08)
    pdf.line(x + (w * 0.28), y + 3.2, x + (w * 0.72), y + 3.2)


def _draw_section_watermark(pdf: MapaPDF, index: int, key: str) -> None:
    _bg, _cream, gold, _accent = _palette(key)
    try:
        pdf.set_alpha(0.16)
    except Exception:
        pass
    pdf.set_text_color(*gold)
    pdf.set_font(pdf.font_title, "B" if pdf.font_title == "Times" else "", 68)
    pdf.set_xy(PAGE_W - 92, 23)
    pdf.cell(70, 32, f"{index:02d}", align="R")
    try:
        pdf.set_alpha(1)
    except Exception:
        pass


def _section_layout(index: int) -> tuple[float, float, float, float]:
    layouts = [
        # Paneles más amplios: permiten letra mayor sin dejar páginas vacías.
        (15, 70, 186, 198),
        (17, 71, 182, 197),
        (14, 72, 188, 196),
        (18, 70, 180, 198),
    ]
    return layouts[(index - 1) % len(layouts)]


def _write_labeled_panel(
    pdf: MapaPDF,
    label: str,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    key: str,
    *,
    start_size: float = 10.8,
    minimum: float = 8.2,
    alpha: float = 0.86,
) -> None:
    text = _clean_text(text, keep_breaks=True)
    font_size = _fit_font_for_panel(pdf, text, w, h - 14, start=start_size * 1.12, minimum=minimum)

    _bg, _cream, gold, _accent = _palette(key)
    _shadow_cell(
        pdf,
        x + 8,
        y + 3.4,
        w - 16,
        6.0,
        label.upper(),
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=11.2,
        color=gold,
        align="C",
        shadow_alpha=0.22,
    )

    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.10)
    pdf.line(x + 30, y + 14.5, x + w - 30, y + 14.5)

    line_h = _line_height(font_size)
    paragraphs = [
        _clean_text(p)
        for p in re.split(r"\n\s*\n", text)
        if _clean_text(p)
    ]

    current_y = y + 21
    for idx, paragraph in enumerate(paragraphs):
        if idx > 0:
            current_y += 2.4
        _shadow_multi_cell(
            pdf,
            x + 6,
            current_y,
            w - 12,
            line_h,
            paragraph,
            font=pdf.font_body,
            style="",
            size=font_size,
            color=(246, 225, 172),
            align="J",
            shadow_alpha=0.10,
        )
        current_y = pdf.get_y()


def _render_section_opener_page(
    pdf: MapaPDF,
    key: str,
    sec: dict[str, str],
    datos: dict[str, Any],
    index: int,
) -> None:
    pdf.add_page()

    _page_bg(pdf, key, datos, overlay=0.055)
    _draw_section_watermark(pdf, index, key)

    title = _section_title(datos, key)
    heading = _page_heading(datos, key)
    quote = _pull_quote(sec.get("primera_lectura", ""))
    section_label = f"{_fixed_text(datos, 'section_label')} {index:02d}"
    nombre = _nombre_completo(datos)

    _bg, _cream, gold, accent = _palette(key)
    panel_fill = (8, 14, 30)
    panel_border = tuple(int(gold[i] * 0.88 + accent[i] * 0.12) for i in range(3))

    x, y, w, h = 18, 28, PAGE_W - 36, 222
    _draw_rounded_transparent_rect(
        pdf,
        x,
        y,
        w,
        h,
        12,
        panel_fill,
        panel_border,
        fill_alpha=0.82,
        border_alpha=0.96,
        line_width=0.34,
    )

    title_font, title_style = pdf.title_font_for(f"{key}_opener")
    subtitle_font, subtitle_style = pdf.subtitle_font_for(f"{key}_opener_sub")

    _shadow_cell(
        pdf,
        x + 14,
        y + 16,
        w - 28,
        5.2,
        section_label.upper(),
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=9.4,
        color=gold,
        align="C",
        shadow_alpha=0.20,
    )

    _shadow_multi_cell(
        pdf,
        x + 16,
        y + 31,
        w - 32,
        11.5,
        title.upper(),
        font=title_font,
        style=title_style,
        size=27.4,
        color=(248, 244, 234),
        align="C",
        shadow_alpha=0.26,
    )

    _shadow_multi_cell(
        pdf,
        x + 20,
        y + 61,
        w - 40,
        7.4,
        heading,
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=13.0,
        color=(255, 248, 226),
        align="C",
        shadow_alpha=0.24,
    )

    _draw_gold_divider(pdf, x + 42, y + 82, w - 84, key)

    _shadow_multi_cell(
        pdf,
        x + 20,
        y + 103,
        w - 40,
        8.6,
        f'"{quote}"',
        font=subtitle_font,
        style=subtitle_style,
        size=15.5,
        color=(248, 244, 234),
        align="C",
        shadow_alpha=0.26,
    )

    _shadow_cell(
        pdf,
        x + 16,
        y + 168,
        w - 32,
        5.2,
        nombre,
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=10.6,
        color=(255, 246, 220),
        align="C",
        shadow_alpha=0.20,
    )

    _draw_logo_if_exists(pdf, PAGE_W - 44, PAGE_H - 42, 27)


def _render_section_initial_reading_page(
    pdf: MapaPDF,
    key: str,
    sec: dict[str, str],
    datos: dict[str, Any],
    index: int,
) -> None:
    pdf.add_page()

    _page_bg(pdf, key, datos, overlay=0.050)
    _draw_header_block(pdf, key, datos)

    _write_labeled_panel(
        pdf,
        _fixed_text(datos, "opening_label"),
        sec.get("primera_lectura", ""),
        18,
        78,
        PAGE_W - 36,
        176,
        key,
        start_size=12.0,
        minimum=9.0,
        alpha=0.86,
    )


def _render_section_text_page(
    pdf: MapaPDF,
    key: str,
    label: str,
    text: str,
    datos: dict[str, Any],
    *,
    start_size: float = 11.4,
    minimum: float = 8.8,
) -> None:
    pdf.add_page()

    _page_bg(pdf, key, datos, overlay=0.050)
    _draw_header_block(pdf, key, datos)

    _write_labeled_panel(
        pdf,
        label,
        text,
        18,
        78,
        PAGE_W - 36,
        176,
        key,
        start_size=start_size,
        minimum=minimum,
        alpha=0.84,
    )


def _render_section_deep_page(
    pdf: MapaPDF,
    key: str,
    sec: dict[str, str],
    datos: dict[str, Any],
    index: int,
) -> None:
    if _debug_assets():
        print(
            f"[PDF_DEBUG_ASSETS] {key}: profundizacion={_count_words(sec.get('profundizacion', ''))} "
            f"integracion={_count_words(sec.get('integracion', ''))}"
        )

    _render_section_text_page(
        pdf,
        key,
        _fixed_text(datos, "deep_label"),
        sec.get("profundizacion", ""),
        datos,
        start_size=12.2,
        minimum=9.2,
    )
    _render_section_text_page(
        pdf,
        key,
        _fixed_text(datos, "integration_label"),
        sec.get("integracion", ""),
        datos,
        start_size=13.0,
        minimum=10.0,
    )


def _render_section_full_reading_page(
    pdf: MapaPDF,
    key: str,
    sec: dict[str, str],
    datos: dict[str, Any],
    index: int,
) -> None:
    combined = _section_combined_text(sec)
    x, y, w = 16, 72, PAGE_W - 32
    usable_h = PAGE_H - y - INTERIOR_BODY_BOTTOM_SAFE_MM
    h = usable_h
    body_size = INTERIOR_BODY_FONT_SIZE
    chunks = _split_text_for_pages(pdf, combined, w, usable_h, minimum_size=body_size)
    if not chunks:
        chunks = [combined]

    if _debug_assets():
        print(
            f"[PDF_DEBUG_ASSETS] {key}: lectura_completa={_count_words(combined)} "
            f"paginas={len(chunks)}"
        )

    for chunk in chunks:
        pdf.add_page()
        _page_bg(pdf, key, datos, overlay=0.050)
        _draw_header_block(pdf, key, datos)

        _write_panel_text(pdf, chunk, x, y, w, h, key, body_size)


def _render_section_page(
    pdf: MapaPDF,
    key: str,
    sec: dict[str, str],
    datos: dict[str, Any],
    index: int,
) -> None:
    _render_section_full_reading_page(pdf, key, sec, datos, index)


def _cover(pdf: MapaPDF, datos: dict[str, Any]) -> None:
    pdf.add_page()
    _mark_no_footer(pdf)
    _draw_fixed_page_image(pdf, "portada.png")
    _draw_cover_logo(pdf)


def _load_openai_content_for_client_page(datos: dict[str, Any]) -> dict[str, Any]:
    contenido = datos.get("contenido_openai")

    if contenido is None:
        contenido_path = datos.get("contenido_openai_path") or datos.get("json_path")
        if contenido_path:
            path = Path(str(contenido_path))
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    contenido = json.load(f)

    return contenido if isinstance(contenido, dict) else {}


def _client_page_text(datos: dict[str, Any], key: str) -> str:
    lang = _idioma_pdf(datos)
    texts = {
        "es": {
            "created_for": "Este mapa ha sido creado exclusivamente para",
            "birthdate": "Fecha de nacimiento",
            "zodiac": "Signo zodiacal",
            "element": "Elemento",
            "planet": "Planeta regente",
            "life_number": "Número de vida",
            "spirit_animal": "Animal espiritual",
            "guardian_angel": "Ángel guardián",
            "energy_stone": "Piedra energética",
        },
        "en": {
            "created_for": "This map has been created exclusively for",
            "birthdate": "Birth date",
            "zodiac": "Zodiac sign",
            "element": "Element",
            "planet": "Ruling planet",
            "life_number": "Life path number",
            "spirit_animal": "Spirit animal",
            "guardian_angel": "Guardian angel",
            "energy_stone": "Energy stone",
        },
        "pt": {
            "created_for": "Este mapa foi criado exclusivamente para",
            "birthdate": "Data de nascimento",
            "zodiac": "Signo zodiacal",
            "element": "Elemento",
            "planet": "Planeta regente",
            "life_number": "Número de vida",
            "spirit_animal": "Animal espiritual",
            "guardian_angel": "Anjo da guarda",
            "energy_stone": "Pedra energética",
        },
        "fr": {
            "created_for": "Cette carte a été créée exclusivement pour",
            "birthdate": "Date de naissance",
            "zodiac": "Signe du zodiaque",
            "element": "Élément",
            "planet": "Planète dominante",
            "life_number": "Nombre de vie",
            "spirit_animal": "Animal spirituel",
            "guardian_angel": "Ange gardien",
            "energy_stone": "Pierre énergétique",
        },
        "it": {
            "created_for": "Questa mappa è stata creata esclusivamente per",
            "birthdate": "Data di nascita",
            "zodiac": "Segno zodiacale",
            "element": "Elemento",
            "planet": "Pianeta dominante",
            "life_number": "Numero di vita",
            "spirit_animal": "Animale spirituale",
            "guardian_angel": "Angelo custode",
            "energy_stone": "Pietra energetica",
        },
    }
    return texts.get(lang, texts["es"]).get(key, texts["es"][key])


def _calc_value(calculos: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = calculos.get(key)
        if value is not None and _clean_text(value):
            return _clean_text(value)
    return ""


def _profile_calculos(datos: dict[str, Any]) -> dict[str, Any]:
    contenido = _load_openai_content_for_client_page(datos)
    calculos = contenido.get("calculos") if isinstance(contenido.get("calculos"), dict) else {}
    return calculos if isinstance(calculos, dict) else {}


def _profile_nombre(datos: dict[str, Any]) -> str:
    calculos = _profile_calculos(datos)
    return _calc_value(calculos, "nombre_completo") or _nombre_completo(datos)


def _profile_fecha_raw(datos: dict[str, Any]) -> str:
    calculos = _profile_calculos(datos)
    return (
        _calc_value(calculos, "fecha_nacimiento")
        or _clean_text(datos.get("fecha_nacimiento") or datos.get("fecha") or "")
    )


def _profile_fecha_formatted(datos: dict[str, Any]) -> str:
    raw = _profile_fecha_raw(datos)
    return _format_birthdate(datos, raw) if raw else ""


def _profile_value(datos: dict[str, Any], *keys: str) -> str:
    return _calc_value(_profile_calculos(datos), *keys)


def _profile_compare_text(value: Any) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"[^\wáéíóúñü]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _date_compare_key(value: Any) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return _profile_compare_text(raw)


def _validate_profile_consistency(datos: dict[str, Any]) -> None:
    if datos.get("allow_profile_mismatch"):
        return

    calculos = _profile_calculos(datos)
    if not calculos:
        return

    nombre_json = _calc_value(calculos, "nombre_completo")
    nombre_pedido = _nombre_completo(datos)
    if nombre_json and nombre_pedido and _profile_compare_text(nombre_json) != _profile_compare_text(nombre_pedido):
        raise RuntimeError(
            "El JSON de OpenAI no coincide con el nombre del pedido. "
            f"Pedido: {nombre_pedido}. JSON: {nombre_json}. "
            "No se genera PDF para evitar entregar un libro con datos cruzados."
        )

    fecha_json = _calc_value(calculos, "fecha_nacimiento")
    fecha_pedido = _clean_text(datos.get("fecha_nacimiento") or datos.get("fecha") or "")
    if fecha_json and fecha_pedido and _date_compare_key(fecha_json) != _date_compare_key(fecha_pedido):
        raise RuntimeError(
            "El JSON de OpenAI no coincide con la fecha de nacimiento del pedido. "
            f"Pedido: {fecha_pedido}. JSON: {fecha_json}. "
            "No se genera PDF para evitar inconsistencias visibles."
        )


def _dedicatoria_text(datos: dict[str, Any]) -> str:
    if not datos.get("es_regalo"):
        return ""
    text = _clean_text(datos.get("dedicatoria") or "", keep_breaks=True)
    return text[:500].strip()


def _render_client_page(pdf: MapaPDF, datos: dict[str, Any]) -> None:
    pdf.add_page()
    _mark_no_footer(pdf)
    _draw_fixed_page_image(pdf, "nombre.png", darken_alpha=0.18)

    nombre = _profile_nombre(datos)
    fecha = _profile_fecha_formatted(datos)

    rows = [
        (_client_page_text(datos, "birthdate"), fecha),
        (_client_page_text(datos, "zodiac"), _profile_value(datos, "signo", "zodiaco")),
        (_client_page_text(datos, "element"), _profile_value(datos, "elemento")),
        (_client_page_text(datos, "planet"), _profile_value(datos, "planeta_regente")),
        (_client_page_text(datos, "life_number"), _profile_value(datos, "numero_vida", "numero_de_vida")),
        (_client_page_text(datos, "spirit_animal"), _profile_value(datos, "animal_totem", "animal_espiritual")),
        (_client_page_text(datos, "guardian_angel"), _profile_value(datos, "angel_guardian", "angel_guardián")),
        (_client_page_text(datos, "energy_stone"), _profile_value(datos, "piedra_energetica", "piedra_energética")),
    ]
    rows = [(label, value) for label, value in rows if value]
    dedicatoria = _dedicatoria_text(datos)

    _bg, _cream, gold, _accent = _palette("portada")
    title_font, title_style = pdf.title_font_for("pagina_cliente_titulo")
    name_font, name_style = pdf.name_font_for("pagina_cliente_nombre")

    intro_y = 51 if dedicatoria else 61
    name_y = 70 if dedicatoria else 82

    _shadow_multi_cell(
        pdf,
        28,
        intro_y,
        PAGE_W - 56,
        7.6,
        _client_page_text(datos, "created_for"),
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=15.8,
        color=(255, 248, 226),
        align="C",
        shadow_alpha=0.24,
    )

    name_size = 40.0 if len(nombre) <= 30 else 36.0 if len(nombre) <= 42 else 32.0
    _shadow_multi_cell(
        pdf,
        18,
        name_y,
        PAGE_W - 36,
        name_size * 0.46,
        nombre,
        font=name_font,
        style=name_style,
        size=name_size,
        color=gold,
        align="C",
        shadow_alpha=0.26,
    )

    divider_y = max(pdf.get_y() + 7.0, 109 if dedicatoria else 124)
    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.18)
    pdf.line(56, divider_y, PAGE_W - 56, divider_y)

    if dedicatoria:
        dedication_text = f'"{dedicatoria}"'
        dedication_x = 31
        dedication_y = divider_y + 9.0
        dedication_w = PAGE_W - 62
        dedication_max_h = 54.0
        dedication_font = _fit_font_for_panel(
            pdf,
            dedication_text,
            dedication_w,
            dedication_max_h,
            start=13.4,
            minimum=9.2,
        )
        _shadow_multi_cell(
            pdf,
            dedication_x,
            dedication_y,
            dedication_w,
            _line_height(dedication_font),
            dedication_text,
            font=name_font,
            style=name_style,
            size=dedication_font,
            color=(248, 244, 234),
            align="C",
            shadow_alpha=0.24,
            keep_breaks=True,
        )
        second_divider_y = min(max(pdf.get_y() + 7.0, dedication_y + 25.0), 180.0)
        pdf.set_draw_color(*gold)
        pdf.set_line_width(0.14)
        pdf.line(66, second_divider_y, PAGE_W - 66, second_divider_y)
        current_y = second_divider_y + 9.0
        row_size = 11.6
        row_step = 9.5
    else:
        current_y = divider_y + 13.0
        row_size = 13.4
        row_step = 10.8

    for label, value in rows:
        text = f"{label}: {value}"
        _shadow_cell(
            pdf,
            30,
            current_y,
            PAGE_W - 60,
            7.4,
            text,
            font=pdf.font_subtitle,
            style=pdf.subtitle_strong_style(),
            size=row_size,
            color=(248, 244, 234),
            align="C",
            shadow_alpha=0.22,
        )
        current_y += row_step


def _render_intro_page(pdf: MapaPDF, datos: dict[str, Any]) -> None:
    pdf.add_page()

    _page_bg(pdf, "mensaje_alma", datos, overlay=0.050)

    _bg, _cream, gold, accent = _palette("mensaje_alma")
    panel_fill = (8, 14, 30)
    panel_border = tuple(int(gold[i] * 0.88 + accent[i] * 0.12) for i in range(3))

    x, y, w, h = 20, 30, PAGE_W - 40, 212
    _draw_rounded_transparent_rect(
        pdf,
        x,
        y,
        w,
        h,
        10,
        panel_fill,
        panel_border,
        fill_alpha=0.86,
        border_alpha=0.96,
        line_width=0.34,
    )

    title_font, title_style = pdf.title_font_for("intro_titulo")
    subtitle_font, subtitle_style = pdf.subtitle_font_for("intro_subtitulo")

    _shadow_multi_cell(
        pdf,
        x + 12,
        y + 17,
        w - 24,
        11.7,
        _fixed_text(datos, "intro_title"),
        font=title_font,
        style=title_style,
        size=27.8,
        color=gold,
        align="C",
        shadow_alpha=0.26,
    )

    _shadow_multi_cell(
        pdf,
        x + 17,
        y + 53,
        w - 34,
        7.4,
        _fixed_text(datos, "intro_subtitle"),
        font=subtitle_font,
        style=subtitle_style,
        size=12.7,
        color=(248, 244, 234),
        align="C",
        shadow_alpha=0.24,
    )

    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.22)
    pdf.line(x + 34, y + 88, x + w - 34, y + 88)

    _shadow_cell(
        pdf,
        x + 16,
        y + 101,
        w - 32,
        6,
        _fixed_text(datos, "intro_steps_title"),
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=11.3,
        color=(255, 246, 220),
        align="C",
        shadow_alpha=0.22,
    )

    steps = _fixed_text(datos, "intro_steps")
    if not isinstance(steps, list):
        steps = []

    pdf.set_font(pdf.font_body, "", 10.8)
    pdf.set_text_color(248, 244, 234)
    current_y = y + 122

    for index, step in enumerate(steps, start=1):
        pdf.set_xy(x + 18, current_y)
        pdf.set_text_color(*gold)
        pdf.set_font(pdf.font_subtitle, pdf.subtitle_strong_style(), 10.9)
        pdf.cell(9, 5.4, _safe(f"{index}."))

        _shadow_multi_cell(
            pdf,
            x + 29,
            current_y,
            w - 47,
            6.8,
            step,
            font=pdf.font_body,
            style="",
            size=10.8,
            color=(248, 244, 234),
            align="L",
            shadow_alpha=0.20,
        )
        current_y = pdf.get_y() + 4

    _shadow_multi_cell(
        pdf,
        x + 17,
        y + h - 43,
        w - 34,
        6.8,
        _fixed_text(datos, "intro_close"),
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=11.1,
        color=(255, 246, 220),
        align="C",
        shadow_alpha=0.22,
    )

    _draw_logo_if_exists(pdf, PAGE_W - 45, PAGE_H - 42, 28)


def _print_signature_specs(datos: dict[str, Any]) -> list[dict[str, str]]:
    nombre = _profile_nombre(datos)
    signo = _profile_value(datos, "signo", "zodiaco") or "tu signo"
    numero = _profile_value(datos, "numero_vida", "numero_de_vida") or "tu número de vida"
    angel = _profile_value(datos, "angel_guardian", "angel_guardián") or "tu guía espiritual"
    piedra = _profile_value(datos, "piedra_energetica", "piedra_energética") or "tu piedra energética"

    lang = _idioma_pdf(datos)
    texts = {
        "es": [
            {
                "key": "mensaje_final",
                "title": "Guía de integración",
                "subtitle": "Para volver a tu mapa sin prisa",
                "body": (
                    f"{nombre}, este libro no termina cuando llegas a la última página. "
                    "Su valor real aparece cuando eliges volver a una frase, respirarla y convertirla en una decisión pequeña.\n\n"
                    "Durante los próximos siete días, lee una sola sección por día. No busques entenderlo todo de una vez. "
                    "Elige una línea que te toque, escríbela en un lugar visible y pregúntate: qué parte de mí está lista para vivir esto con más verdad.\n\n"
                    f"Usa tus símbolos como brújula: {signo} te recuerda una forma de mirar la vida; "
                    f"{numero} habla de un ritmo interior; {piedra} puede ser un ancla para volver al cuerpo cuando la mente se disperse. "
                    "Lo importante no es creerlo todo de forma rígida, sino permitir que cada símbolo abra una conversación honesta contigo."
                ),
            },
            {
                "key": "ritual_personalizado",
                "title": "Ritual de cierre",
                "subtitle": "Una forma sencilla de sellar la lectura",
                "body": (
                    "Cuando termines este mapa, busca un momento de silencio. Coloca una mano en el corazón y otra sobre el abdomen. "
                    "Respira lento tres veces, como si cada exhalación quitara una capa de ruido.\n\n"
                    "Después, di en voz baja: recibo lo que me fortalece, suelto lo que ya no necesita seguir conmigo y regreso a mi nombre con presencia. "
                    "No lo digas perfecto; dilo verdadero.\n\n"
                    f"Si deseas acompañarlo con un símbolo, usa {piedra} o una vela pequeña. "
                    f"Puedes invocar la presencia de {angel} como una imagen de protección, calma y dirección. "
                    "Cierra el ritual eligiendo una acción concreta para las próximas veinticuatro horas. El alma confía más en los actos simples que en las promesas enormes."
                ),
            },
            {
                "key": "esencia_alma",
                "title": "Bendición final",
                "subtitle": "Para llevar este mapa contigo",
                "body": (
                    f"Que este libro sea para ti, {nombre}, una puerta y no una jaula. "
                    "Que ninguna frase te limite, y que toda palabra luminosa te recuerde una libertad que ya estaba naciendo dentro de ti.\n\n"
                    "Que puedas caminar con más claridad, amar con más presencia, elegir con más honestidad y volver a tu centro cada vez que el mundo haga demasiado ruido.\n\n"
                    "Tu nombre no es una casualidad vacía. Es una casa simbólica, una memoria, una invitación. "
                    "Habitarlo con amor es permitir que tu vida deje de sentirse prestada y empiece a sentirse profundamente tuya."
                ),
            },
        ],
        "en": [
            {
                "key": "mensaje_final",
                "title": "Integration Guide",
                "subtitle": "A gentle way to return to your map",
                "body": (
                    f"{nombre}, this book does not end on the last page. Its real value appears when you return to one sentence, breathe with it, and turn it into a small decision.\n\n"
                    "For the next seven days, read only one section per day. Choose one line that moves you and ask: what part of me is ready to live this with more truth.\n\n"
                    f"Let your symbols become a compass: {signo}, {numero}, and {piedra} are not limits; they are invitations to listen to yourself with more honesty."
                ),
            },
            {
                "key": "ritual_personalizado",
                "title": "Closing Ritual",
                "subtitle": "A simple way to seal the reading",
                "body": (
                    "When you finish this map, find a quiet moment. Place one hand on your heart and one on your abdomen. Take three slow breaths.\n\n"
                    "Then say softly: I receive what strengthens me, I release what no longer needs to remain with me, and I return to my name with presence.\n\n"
                    f"If you wish, use {piedra} as an anchor and imagine {angel} as a presence of protection, calm, and direction."
                ),
            },
            {
                "key": "esencia_alma",
                "title": "Final Blessing",
                "subtitle": "To carry this map with you",
                "body": (
                    f"May this book be a doorway for you, {nombre}, not a cage. May no phrase limit you, and may every luminous word remind you of a freedom already awakening within.\n\n"
                    "May you walk with clarity, love with presence, choose with honesty, and return to your center whenever the world becomes too loud."
                ),
            },
        ],
    }
    return texts.get(lang, texts["es"])


def _render_print_signature_page(pdf: MapaPDF, datos: dict[str, Any], spec: dict[str, str]) -> None:
    pdf.add_page()
    key = spec.get("key") or "mensaje_final"
    _page_bg(pdf, key, datos, overlay=0.050)
    _bg, _cream, gold, _accent = _palette(key)

    title_font, title_style = pdf.title_font_for(f"print_signature_{spec.get('title', key)}")
    subtitle_font, subtitle_style = pdf.subtitle_font_for(f"print_signature_sub_{spec.get('title', key)}")

    _shadow_cell(
        pdf,
        22,
        28,
        PAGE_W - 44,
        12,
        spec.get("title", ""),
        font=title_font,
        style=title_style,
        size=29.4,
        color=gold,
        align="C",
        shadow_alpha=0.26,
    )
    _shadow_cell(
        pdf,
        28,
        54,
        PAGE_W - 56,
        8,
        spec.get("subtitle", ""),
        font=subtitle_font,
        style=subtitle_style,
        size=15.2,
        color=(255, 250, 238),
        align="C",
        shadow_alpha=0.24,
    )

    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.18)
    pdf.line(56, 72, PAGE_W - 56, 72)

    x, y, w, h = 31, 91, PAGE_W - 62, 136
    body = spec.get("body", "")
    font_size = _fit_font_for_panel(pdf, body, w, h, start=15.4, minimum=11.8)
    _shadow_multi_cell(
        pdf,
        x,
        y,
        w,
        _line_height(font_size),
        body,
        font=pdf.font_body,
        style="",
        size=font_size,
        color=(248, 244, 234),
        align="L",
        shadow_alpha=0.28,
    )

    _shadow_cell(
        pdf,
        28,
        PAGE_H - 30,
        PAGE_W - 56,
        6,
        _fixed_text(datos, "brand"),
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=9.0,
        color=(255, 238, 198),
        align="C",
        shadow_alpha=0.20,
    )


def _print_note_specs(datos: dict[str, Any]) -> list[dict[str, str]]:
    lang = _idioma_pdf(datos)
    specs = {
        "es": [
            {
                "key": "mensaje_final",
                "title": "Notas del alma",
                "subtitle": "Frases, señales y recuerdos que quiero guardar",
                "prompt": "Lo que mi alma no quiere olvidar",
            },
            {
                "key": "ritual_personalizado",
                "title": "Notas de integración",
                "subtitle": "Intenciones, símbolos y pequeñas decisiones",
                "prompt": "Lo que deseo honrar después de esta lectura",
            },
        ],
        "en": [
            {
                "key": "mensaje_final",
                "title": "Soul Notes",
                "subtitle": "Phrases, signs, and memories I want to keep",
                "prompt": "What my soul does not want to forget",
            },
            {
                "key": "ritual_personalizado",
                "title": "Integration Notes",
                "subtitle": "Intentions, symbols, and small decisions",
                "prompt": "What I want to honor after this reading",
            },
        ],
    }
    return specs.get(lang, specs["es"])


def _render_notes_page(pdf: MapaPDF, datos: dict[str, Any], spec: dict[str, str]) -> None:
    pdf.add_page()
    key = spec.get("key") or "mensaje_final"
    _draw_fixed_page_image(pdf, "nombre.png", darken_alpha=0.22)
    _bg, _cream, gold, _accent = _palette(key)

    title_font, title_style = pdf.title_font_for(f"notes_{spec.get('title', key)}")
    subtitle_font, subtitle_style = pdf.subtitle_font_for(f"notes_sub_{spec.get('title', key)}")

    _shadow_cell(
        pdf,
        22,
        29,
        PAGE_W - 44,
        12,
        spec.get("title", ""),
        font=title_font,
        style=title_style,
        size=31.0,
        color=gold,
        align="C",
        shadow_alpha=0.12,
    )
    _shadow_multi_cell(
        pdf,
        31,
        55,
        PAGE_W - 62,
        7.0,
        spec.get("subtitle", ""),
        font=subtitle_font,
        style=subtitle_style,
        size=13.6,
        color=(255, 250, 238),
        align="C",
        shadow_alpha=0.10,
    )

    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.18)
    pdf.line(56, 75, PAGE_W - 56, 75)

    _shadow_cell(
        pdf,
        27,
        87,
        PAGE_W - 54,
        7,
        spec.get("prompt", ""),
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=12.2,
        color=(246, 225, 172),
        align="L",
        shadow_alpha=0.08,
    )

    used_alpha = _with_alpha(pdf, 0.48)
    pdf.set_draw_color(228, 192, 113)
    pdf.set_line_width(0.12)
    x1, x2 = 27, PAGE_W - 27
    y = 108
    for _ in range(13):
        pdf.line(x1, y, x2, y)
        y += 10.4
    _restore_alpha(pdf, used_alpha)

    used_alpha = _with_alpha(pdf, 0.34)
    pdf.set_draw_color(248, 244, 234)
    pdf.set_line_width(0.08)
    for yy in (108, 170, 232):
        pdf.line(27, yy, 33, yy)
        pdf.line(PAGE_W - 33, yy, PAGE_W - 27, yy)
    _restore_alpha(pdf, used_alpha)

    _shadow_cell(
        pdf,
        28,
        PAGE_H - 30,
        PAGE_W - 56,
        6,
        _fixed_text(datos, "brand"),
        font=pdf.font_subtitle,
        style=pdf.subtitle_strong_style(),
        size=9.0,
        color=(255, 238, 198),
        align="C",
        shadow_alpha=0.08,
    )


def _add_print_signature_pages(pdf: MapaPDF, datos: dict[str, Any]) -> int:
    pages_added = 0

    current_pages = pdf.page_no()
    target_before_notes = max(current_pages, PRINT_MIN_INTERIOR_PAGES - 2)
    signature_pages_needed = target_before_notes - current_pages
    while (current_pages + signature_pages_needed + 2) % 4 != 0:
        signature_pages_needed += 1

    if signature_pages_needed:
        signature_specs = _print_signature_specs(datos)
        for index in range(signature_pages_needed):
            _render_print_signature_page(pdf, datos, signature_specs[index % len(signature_specs)])
            pages_added += 1

    note_specs = _print_note_specs(datos)
    for index in range(2):
        _render_notes_page(pdf, datos, note_specs[index % len(note_specs)])
        pages_added += 1

    return pages_added


def _back_cover(pdf: MapaPDF, datos: dict[str, Any]) -> None:
    pdf.add_page()
    _mark_no_footer(pdf)
    _draw_fixed_page_image(pdf, "contraportada.png")
    _draw_cover_logo(pdf, back=True)


def _output_path(datos_pedido: dict[str, Any]) -> Path:
    out_dir_raw = datos_pedido.get("output_dir") or datos_pedido.get("carpeta_salida")

    if out_dir_raw:
        out_dir = Path(str(out_dir_raw))
    else:
        out_dir = _project_root() / "output"

    out_dir.mkdir(parents=True, exist_ok=True)

    pedido_id = datos_pedido.get("pedido_id") or datos_pedido.get("order_id") or datos_pedido.get("id")

    if pedido_id:
        return out_dir / f"mapa_alma_{int(pedido_id)}.pdf"

    nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", _nombre_completo(datos_pedido)).strip("_") or "Mapa_del_Alma"
    stamp = time.strftime("%Y%m%d_%H%M%S")

    return out_dir / f"Mapa_del_Alma_{nombre}_{stamp}.pdf"


def generar_pdf_desde_tienda(datos_pedido: dict[str, Any]) -> str:
    """
    Genera PDF vertical premium usando contenido ya generado.

    Requisito obligatorio:
    - datos_pedido["contenido_openai"] debe existir
      o datos_pedido["contenido_openai_path"] debe apuntar a un JSON.

    Este archivo NO llama OpenAI.
    """

    if not isinstance(datos_pedido, dict):
        raise TypeError("datos_pedido debe ser un diccionario.")

    _visual_seed(datos_pedido)
    _validate_profile_consistency(datos_pedido)

    secciones = _extraer_contenido_openai(datos_pedido)

    faltantes = [key for key in SECTION_ORDER if key not in secciones]
    if faltantes:
        raise RuntimeError(f"Faltan secciones obligatorias para generar el PDF: {faltantes}")

    pdf = MapaPDF(orientation="P", unit="mm", format="Letter")
    pdf.language = _idioma_pdf(datos_pedido)
    pdf.set_title("Mapa del Alma")
    pdf.set_author("El nombre que me habita")

    _render_client_page(pdf, datos_pedido)

    for index, key in enumerate(SECTION_ORDER, start=1):
        _render_section_page(pdf, key, secciones[key], datos_pedido, index)

    _add_print_signature_pages(pdf, datos_pedido)

    path = _output_path(datos_pedido)
    pdf.output(str(path))

    return str(path)


def generar_pdf(datos_pedido: dict[str, Any]) -> str:
    return generar_pdf_desde_tienda(datos_pedido)


def crear_pdf(datos_pedido: dict[str, Any]) -> str:
    return generar_pdf_desde_tienda(datos_pedido)


def generar_mapa_pdf(datos_pedido: dict[str, Any]) -> str:
    return generar_pdf_desde_tienda(datos_pedido)


if __name__ == "__main__":
    raise RuntimeError(
        "pdf_generator.py no debe ejecutarse directo porque no genera texto. "
        "Primero genera JSON con app.openai_generator. "
        "Luego llama generar_pdf_desde_tienda con contenido_openai o contenido_openai_path."
    )
