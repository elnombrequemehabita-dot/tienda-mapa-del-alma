"""
Rutas, paletas por signo, tipografías y convenciones visuales para Mapa del Alma.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from reportlab.lib import colors

# Raíz del proyecto (carpeta que contiene main.py)
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
IMAGES_DIR = ASSETS / "imagenes"
FONTS_DIR = ASSETS / "fuentes"
OUTPUT_DIR = ROOT / "output"

# Fondos por signo en assets/imagenes (búsqueda en orden; resolve_asset es case-insensitive).
# Prioridad: {signo}_fondo.* → {signo}_signo.* → fondo_{signo}.* (compatibilidad)
def background_image_filenames_for_sign(sign_key: str) -> tuple[str, ...]:
    sk = sign_key.lower().strip()
    names: list[str] = []
    for ext in (".jpg", ".jpeg", ".png"):
        names.append(f"{sk}_fondo{ext}")
    for ext in (".jpg", ".jpeg", ".png"):
        names.append(f"{sk}_signo{ext}")
    for ext in (".jpg", ".jpeg", ".png"):
        names.append(f"fondo_{sk}{ext}")
    return tuple(names)


def fondo_filename_for_sign(sign_key: str) -> str:
    """Compatibilidad: primer nombre legacy."""
    return f"fondo_{sign_key.lower().strip()}.jpg"


# Velo oscuro sobre el JPG para legibilidad del texto (0 = sin velo).
# Más alto = fondo más “opaco” / menos foto visible, texto más legible.
SIGN_BACKGROUND_VEIL_ALPHA = 0.36

# PNG de dígitos para sección de numerología (1.png … 9.png)
NUMEROLOGY_DIGIT_FILES: list[str] = [f"{i}.png" for i in range(1, 10)]

# Tamaño sello / logo para PNG integrados en texto (pt ≈ px a 72 dpi; pauta editorial 60–80)
STAMP_MIN_PT = 68
STAMP_MAX_PT = 92
STAMP_DEFAULT_PT = 90

# Sellos en columna junto al texto: signo, planeta, tótem, etc. (pt ≈ px a 72 dpi)
HERO_STAMP_PT = 190.0
# Fracción del menor lado útil (marco interior) para escalar el héroe visual (~25–45 %).
HERO_MIN_FRAC_MIN_SIDE = 0.27
HERO_MAX_FRAC_MIN_SIDE = 0.42

# Portada: mapa dominante + logo grande abajo a la derecha
COVER_TITLE_IMAGE = "mapa.png"
# Tope del mapa en portada (el layout usa casi todo el alto útil)
COVER_TITLE_IMAGE_MAX_PT = 1200.0
# Velo del panel bajo nombre + fecha en portada (50 % = 0.5)
COVER_NAME_DATE_PANEL_ALPHA = 0.5
# Logo esquina inferior derecha (ligeramente más pequeño para subir el mapa)
COVER_LOGO_CORNER_PT = 122.0
# Aire mínimo entre mapa y bloque nombre/fecha (empuja logo y texto hacia abajo)
COVER_GAP_MAP_TO_TEXT_MIN = 18.0
COVER_GAP_MAP_TO_TEXT_MAX = 64.0
COVER_LOGO_MAX_PT = 176.0

# Firma del Universo: sello geométrico en canvas (diámetro visual ~size pt; trazo reforzado en firma_universo)
FIRMA_UNIVERSO_STAMP_PT = 198.0
# Página de cierre: sello algo más compacto para integrar título + texto + logo en una sola página si es posible.
FIRMA_UNIVERSO_STAMP_LAST_PT = 172.0

# Colores premium (fuente de verdad)
COLOR_TITULO_DORADO = colors.HexColor("#D4AF37")
COLOR_TITULO_DORADO_SUAVE = colors.HexColor("#E6C76A")
COLOR_SUBTITULO_MARFIL = colors.HexColor("#F3E7C2")
COLOR_TEXTO_CLARO = colors.HexColor("#F7F3EA")
COLOR_TEXTO_SECUNDARIO = colors.HexColor("#E8DDC2")
COLOR_SOMBRA_TEXTO = colors.HexColor("#000000")

COLOR_CAJA_OSCURA_AZUL = colors.HexColor("#14202B")
COLOR_CAJA_OSCURA_VINO = colors.HexColor("#2A1820")
COLOR_CAJA_OSCURA_VERDE = colors.HexColor("#1B241D")
COLOR_CAJA_OSCURA_MORADA = colors.HexColor("#21172C")
COLOR_BORDE_CAJA = colors.HexColor("#CBAE52")
BORDE_ALPHA = 0.18

# Panel (caja) principal
CAJA_ALPHA = 0.80
TEXT_PANEL_ALPHA = CAJA_ALPHA
TEXT_PANEL_RADIUS = 16
CAJA_PADDING_X = 24
CAJA_PADDING_Y = 18
TEXT_PANEL_PAD = CAJA_PADDING_X
CAJA_STROKE_WIDTH = 0.0
# Halo oscuro detrás del panel (profundidad sobre el fondo)
TEXT_PANEL_SHADOW_ALPHA = 0.26
TEXT_PANEL_SHADOW_INSET = 5.0

# Tintas y alias heredados
TEXT_BODY_INK_RGB = (COLOR_TEXTO_CLARO.red, COLOR_TEXTO_CLARO.green, COLOR_TEXTO_CLARO.blue)
HEADING_ON_BACKGROUND_RGB = (
    COLOR_SUBTITULO_MARFIL.red,
    COLOR_SUBTITULO_MARFIL.green,
    COLOR_SUBTITULO_MARFIL.blue,
)
TEXT_PANEL_RGB = (
    COLOR_CAJA_OSCURA_AZUL.red,
    COLOR_CAJA_OSCURA_AZUL.green,
    COLOR_CAJA_OSCURA_AZUL.blue,
)

# Caja por elemento (una firma visual por libro)
ELEMENT_PANEL_COLORS: dict[str, tuple[float, float, float]] = {
    "agua": (COLOR_CAJA_OSCURA_AZUL.red, COLOR_CAJA_OSCURA_AZUL.green, COLOR_CAJA_OSCURA_AZUL.blue),
    "fuego": (COLOR_CAJA_OSCURA_VINO.red, COLOR_CAJA_OSCURA_VINO.green, COLOR_CAJA_OSCURA_VINO.blue),
    "tierra": (COLOR_CAJA_OSCURA_VERDE.red, COLOR_CAJA_OSCURA_VERDE.green, COLOR_CAJA_OSCURA_VERDE.blue),
    "aire": (COLOR_CAJA_OSCURA_MORADA.red, COLOR_CAJA_OSCURA_MORADA.green, COLOR_CAJA_OSCURA_MORADA.blue),
}

# Sombra de texto
SOMBRA_X = 1.2
SOMBRA_Y = -1.2
SOMBRA_ALPHA = 0.30
SOMBRA_X_BODY = 0.6
SOMBRA_Y_BODY = -0.6
SOMBRA_ALPHA_BODY = 0.20
# Halo detrás de columnas de sellos (integra PNG con el fondo)
STAMP_PAD_RGB = (0.94, 0.91, 0.86)
STAMP_PAD_ALPHA = 0.52

# Tipografías físicas reales (assets/fuentes) — sin fuentes genéricas de sistema.
# Base solicitada: Playfair + Lora (fallback local cuando no hay Cormorant).
FONT_TITLE_WATER_AIR = "PlayfairSCBold"
FONT_TITLE_FIRE_EARTH = "PlayfairSCBold"
FONT_TITLE_IMPACT = "PlayfairSCBlack"
FONT_BODY_WATER_AIR = "LoraVariable"
FONT_BODY_WATER_AIR_ITALIC = "LoraItalicVariable"
FONT_BODY_FIRE_EARTH = "LoraVariable"
FONT_BODY_FIRE_EARTH_ITALIC = "LoraItalicVariable"
FONT_DETAIL_POPPINS = "PoppinsSemiBold"
FONT_DETAIL_MONTSERRAT = "PoppinsRegular"
FONT_SCRIPT_SIGNATURE = "PlaywriteIEVariable"

# Alias semánticos pedidos por diseño editorial
FONT_TITULO = FONT_TITLE_WATER_AIR
FONT_SUBTITULO = FONT_DETAIL_POPPINS
FONT_TEXTO = FONT_BODY_WATER_AIR
FONT_TEXTO_ITALICA = FONT_BODY_WATER_AIR_ITALIC
FONT_DESTACADO = FONT_TITLE_IMPACT

# Alias legacy conservados para compatibilidad con imports existentes.
FONT_TITLE = FONT_TITLE_WATER_AIR
FONT_TITLE_ITALIC = FONT_TITLE_WATER_AIR
FONT_BODY = FONT_BODY_WATER_AIR
FONT_BODY_ITALIC = FONT_BODY_WATER_AIR_ITALIC

FONT_FILES: dict[str, str] = {
    FONT_TITLE_WATER_AIR: "PlayfairDisplaySC-Bold.ttf",
    FONT_TITLE_FIRE_EARTH: "PlayfairDisplaySC-Bold.ttf",
    FONT_TITLE_IMPACT: "PlayfairDisplaySC-Black.ttf",
    FONT_BODY_WATER_AIR: "Lora-VariableFont_wght.ttf",
    FONT_BODY_WATER_AIR_ITALIC: "Lora-Italic-VariableFont_wght.ttf",
    FONT_BODY_FIRE_EARTH: "Lora-VariableFont_wght.ttf",
    FONT_BODY_FIRE_EARTH_ITALIC: "Lora-Italic-VariableFont_wght.ttf",
    FONT_DETAIL_POPPINS: "Poppins-SemiBold.ttf",
    FONT_DETAIL_MONTSERRAT: "Poppins-Regular.ttf",
    FONT_SCRIPT_SIGNATURE: "PlaywriteIE-VariableFont_wght.ttf",
}

# Escala tipográfica solicitada
SIZE_PORTADA_NOMBRE = 30.0
SIZE_PORTADA_FECHA = 11.0
SIZE_PORTADA_MAPA = 34.0
SIZE_TITULO = 27.0
SIZE_SUBTITULO = 17.0
SIZE_TEXTO = 13.2
SIZE_TEXTO_PEQUENO = 11.2
SIZE_FRASE_DESTACADA = 20.0
LEADING_TITULO = 33.0
LEADING_SUBTITULO = 23.0
LEADING_TEXTO = 19.0
LEADING_FRASE = 26.0

SPACE_AFTER_TITULO = 16.0
SPACE_AFTER_SUBTITULO = 10.0
SPACE_AFTER_PARRAFO = 12.0
SPACE_BETWEEN_BLOCKS = 14.0
SPACE_BEFORE_FRASE_DESTACADA = 12.0
SPACE_AFTER_FRASE_DESTACADA = 12.0

# Colores base editorial (compatibilidad)
COLOR_GOLD = (COLOR_TITULO_DORADO.red, COLOR_TITULO_DORADO.green, COLOR_TITULO_DORADO.blue)
COLOR_GOLD_SOFT = (
    COLOR_TITULO_DORADO_SUAVE.red,
    COLOR_TITULO_DORADO_SUAVE.green,
    COLOR_TITULO_DORADO_SUAVE.blue,
)
COLOR_INK = (COLOR_TEXTO_CLARO.red, COLOR_TEXTO_CLARO.green, COLOR_TEXTO_CLARO.blue)
COLOR_MIST = (COLOR_TEXTO_SECUNDARIO.red, COLOR_TEXTO_SECUNDARIO.green, COLOR_TEXTO_SECUNDARIO.blue)
COLOR_DEEP = (
    COLOR_CAJA_OSCURA_AZUL.red,
    COLOR_CAJA_OSCURA_AZUL.green,
    COLOR_CAJA_OSCURA_AZUL.blue,
)

# Acentos dinámicos por signo (fondos / detalles)
SIGN_THEMES: dict[str, dict[str, Any]] = {
    "aries": {"accent": (0.72, 0.22, 0.18), "glow": (0.95, 0.55, 0.35)},
    "tauro": {"accent": (0.45, 0.32, 0.22), "glow": (0.85, 0.70, 0.45)},
    "geminis": {"accent": (0.35, 0.45, 0.62), "glow": (0.65, 0.78, 0.95)},
    "cancer": {"accent": (0.25, 0.38, 0.55), "glow": (0.55, 0.72, 0.92)},
    "leo": {"accent": (0.78, 0.48, 0.12), "glow": (0.98, 0.78, 0.35)},
    "virgo": {"accent": (0.32, 0.48, 0.36), "glow": (0.72, 0.88, 0.76)},
    "libra": {"accent": (0.55, 0.42, 0.62), "glow": (0.88, 0.78, 0.95)},
    "escorpion": {"accent": (0.38, 0.16, 0.42), "glow": (0.62, 0.42, 0.78)},
    "sagitario": {"accent": (0.55, 0.32, 0.18), "glow": (0.95, 0.72, 0.42)},
    "capricornio": {"accent": (0.22, 0.22, 0.28), "glow": (0.65, 0.68, 0.78)},
    "acuario": {"accent": (0.18, 0.42, 0.55), "glow": (0.55, 0.82, 0.92)},
    "piscis": {"accent": (0.22, 0.38, 0.55), "glow": (0.55, 0.72, 0.88)},
}

# Planetas → archivo esperado (minúsculas; la resolución real es case-insensitive)
PLANET_IMAGE: dict[str, str] = {
    "sol": "sol.png",
    "luna": "luna.png",
    "mercurio": "mercurio.png",
    "venus": "venus.png",
    "marte": "marte.png",
    "jupiter": "jupiter.png",
    "saturno": "saturno.png",
}

ELEMENT_IMAGE: dict[str, str] = {
    "fuego": "fuego.png",
    "tierra": "tierra.png",
    "aire": "aire.png",
    "agua": "agua.png",
}

SIGN_IMAGE: dict[str, str] = {
    "aries": "aries.png",
    "tauro": "tauro.png",
    "geminis": "geminis.png",
    "cancer": "cancer.png",
    "leo": "leo.png",
    "virgo": "virgo.png",
    "libra": "libra.png",
    "escorpion": "escorpion.png",
    "sagitario": "sagitario.png",
    "capricornio": "capricornio.png",
    "acuario": "acuario.png",
    "piscis": "piscis.png",
}

# Zodiaco chino (archivos opcionales; si no existen, el motor usa fallback)
CHINESE_ANIMAL_FILES: list[str] = [
    "rata.png",
    "buey.png",
    "tigre.png",
    "conejo.png",
    "dragon.png",
    "serpiente.png",
    "caballo.png",
    "cabra.png",
    "mono.png",
    "gallo.png",
    "perro.png",
    "cerdo.png",
]

CHINESE_ANIMAL_LABELS_ES: list[str] = [
    "Rata",
    "Buey",
    "Tigre",
    "Conejo",
    "Dragón",
    "Serpiente",
    "Caballo",
    "Cabra",
    "Mono",
    "Gallo",
    "Perro",
    "Cerdo",
]

TOTEM_POOL: list[str] = [
    "leon.png",
    "colibri.png",
    "delfin.png",
    "ciervo.png",
    "oso.png",
    "pantera.png",
]

GEM_POOL: list[str] = [
    "esmeralda.png",
    "diamante.png",
    "amatista.png",
    "aguamarina.png",
    "granate.png",
    "peridot.png",
    "perla.png",
    "rubi.png",
    "topacio.png",
    "turmalina.png",
    "turquesa.png",
    "zafiro.png",
    "cristal_de_cuarzo.png",
]

ARCHANGEL_POOL: list[str] = [
    "arcangel_miguel.png",
    "arcangel_gabriel.png",
    "arcangel_rafael.png",
    "arcangel_uriel.png",
    "arcangel_Jofiel.png",
    "arcangel_Chamuel.png",
    "arcangel_Zadkiel.png",
    "arcangel_Metatron.png",
    "arcangel_Sandalphon.png",
]

ENERGY_FILES: list[str] = [
    "energia.png",
    "energia1.png",
    "energia2.png",
    "energia3.png",
    "energia4.png",
    "energia5.png",
]

LOGO_FILE = "logo.png"
