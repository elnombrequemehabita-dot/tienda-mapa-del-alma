from __future__ import annotations

import json
import random
import re
import time
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

SECTION_TITLES = {
    "mensaje_alma": "Mensaje de tu alma",
    "origen_nombre": "Origen simbolico del nombre",
    "linaje_apellidos": "Linaje de tus apellidos",
    "esencia": "Esencia profunda",
    "energia": "Energia esencial",
    "zodiaco": "Zodiaco occidental",
    "zodiaco_chino": "Zodiaco chino",
    "numerologia": "Numerologia del alma",
    "animal_espiritual": "Animal totem",
    "angel_guardian": "Angel de la guarda",
    "piedra_energetica": "Piedra energetica",
    "dones": "Dones y talentos",
    "sombras": "Lado oscuro y sombras",
    "herida": "Herida emocional y sanacion",
    "proposito": "Proposito de alma",
    "amor_vinculos": "Amor y vinculos",
    "dinero_camino": "Dinero, trabajo y expansion",
    "ritual_personalizado": "Ritual personalizado",
    "afirmaciones": "Afirmaciones de poder",
    "mensaje_final": "Mensaje final",
    "esencia_alma": "Esencia del Alma",
}

SECTION_ORDER = list(SECTION_TITLES.keys())

PAGE_HEADINGS = {
    "mensaje_alma": "Lo que tu alma reconoce",
    "origen_nombre": "El sonido que te nombra",
    "linaje_apellidos": "La memoria que camina contigo",
    "esencia": "Tu centro verdadero",
    "energia": "Tu campo magnetico",
    "zodiaco": "Tu cielo de nacimiento",
    "zodiaco_chino": "Tu instinto ancestral",
    "numerologia": "Tus numeros guia",
    "animal_espiritual": "Tu guia instintiva",
    "angel_guardian": "Tu proteccion invisible",
    "piedra_energetica": "Tu amuleto mineral",
    "dones": "Lo que viniste a ofrecer",
    "sombras": "Lo que pide conciencia",
    "herida": "La herida que busca cuidado",
    "proposito": "La direccion de tu alma",
    "amor_vinculos": "Tu forma de amar",
    "dinero_camino": "Trabajo, valor y expansion",
    "ritual_personalizado": "Tu practica de poder",
    "afirmaciones": "Palabras que te reordenan",
    "mensaje_final": "Cierre del mapa",
    "esencia_alma": "La verdad central de tu nombre",
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
    "notas": ((24, 22, 45), (252, 245, 228), (218, 174, 94), (84, 62, 112)),
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


def _sexo_normalizado(valor: Any) -> str:
    sexo = _clean_text(valor).lower()

    if sexo in ("mujer", "femenino", "f", "female", "ella", "nina", "niña"):
        return "mujer"

    if sexo in ("hombre", "masculino", "m", "male", "el", "él", "nino", "niño"):
        return "hombre"

    return "neutral"


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
        path = Path(path)
        cache_dir = _project_root() / "output" / "_pdf_image_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        stat = path.stat()
        suffix = path.suffix.lower()
        keep_alpha = suffix == ".png"
        cache_ext = ".png" if keep_alpha else ".jpg"
        cache_name = f"{path.stem}_{stat.st_size}_{int(stat.st_mtime)}{cache_ext}"
        cache_path = cache_dir / cache_name

        if cache_path.exists() and cache_path.stat().st_size > 0:
            return cache_path

        img = Image.open(path)
        img = ImageOps.exif_transpose(img)

        if keep_alpha and img.mode in ("RGBA", "LA"):
            img.save(cache_path, format="PNG", optimize=True)
        else:
            if img.mode not in ("RGB",):
                img = img.convert("RGB")
            img.save(cache_path, format="JPEG", quality=92, optimize=True)

        return cache_path
    except Exception as exc:
        if _debug_assets():
            print(f"[PDF_DEBUG_ASSETS] No se pudo preparar imagen {path}: {exc}")
        return path


def _pdf_image(pdf: "MapaPDF", path: Path, x: float, y: float, w: float, h: Optional[float] = None) -> None:
    safe_path = _prepared_image_for_pdf(Path(path))
    if _debug_assets():
        print(f"[PDF_DEBUG_ASSETS] Usando imagen: {safe_path}")
    if h is None:
        pdf.image(str(safe_path), x, y, w=w)
    else:
        pdf.image(str(safe_path), x, y, w=w, h=h)


def _pdf_image_cover(pdf: "MapaPDF", path: Path, x: float, y: float, w: float, h: float) -> None:
    """
    Coloca una imagen como fondo tipo cover, sin aplastarla ni deformarla.
    Si la proporcion no coincide exactamente con la pagina, recorta visualmente
    el sobrante como hace Canva/cover en web.
    """
    safe_path = _prepared_image_for_pdf(Path(path))

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
            draw_h = h
            draw_w = h * img_ratio
            draw_x = x - (draw_w - w) / 2
            draw_y = y
        else:
            draw_w = w
            draw_h = w / img_ratio
            draw_x = x
            draw_y = y - (draw_h - h) / 2

        if _debug_assets():
            print(f"[PDF_DEBUG_ASSETS] Fondo cover: {safe_path} -> x={draw_x:.2f}, y={draw_y:.2f}, w={draw_w:.2f}, h={draw_h:.2f}")

        pdf.image(str(safe_path), draw_x, draw_y, w=draw_w, h=draw_h)
    except Exception:
        _pdf_image(pdf, safe_path, x, y, w, h)


def _section_image_options(key: str) -> list[Path]:
    folder = _assets_img_dir()

    if not folder.exists():
        return []

    opciones: list[Path] = []

    # IMPORTANTE:
    # No usar glob(f"{key}_*") directamente porque prefijos como
    # "zodiaco" tambien atrapan "zodiaco_chino_1.jpeg".
    # Aqui solo aceptamos archivos con patron exacto:
    # <key>_<numero>.<extension>
    patron = re.compile(rf"^{re.escape(key)}_[0-9]+\.(?:jpeg|jpg|png|webp)$", re.IGNORECASE)

    for candidate in folder.iterdir():
        if candidate.is_file() and patron.match(candidate.name):
            opciones.append(candidate)

    return sorted(opciones)


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
    - Nunca usa fondos de otra seccion.
    - Usa patron exacto <seccion>_<numero> para evitar mezclar zodiaco con zodiaco_chino.
    - Si existen varias imagenes, evita repetir la misma usada en la generacion anterior
      de esa seccion. Esto hace que secciones como herida no caigan siempre en el
      mismo fondo cuando se regenera el PDF varias veces.
    - Para Esencia del Alma usa el prefijo especial esencia_alma_fondo_*.
    """
    folder = _assets_img_dir()

    if not folder.exists():
        return None

    lookup_key = "esencia_alma_fondo" if key == "esencia_alma" else key
    opciones = _section_image_options(lookup_key)

    if not opciones:
        return None

    if len(opciones) == 1:
        return opciones[0]

    state = _load_rotation_state()
    last_name = state.get(lookup_key, "")

    disponibles = [img for img in opciones if img.name != last_name]
    if not disponibles:
        disponibles = opciones

    # Random fuerte por generacion: no depende del pedido_id, por eso el mismo JSON
    # puede producir un PDF visualmente distinto sin gastar OpenAI.
    rng = random.SystemRandom()
    elegido = rng.choice(disponibles)

    state[lookup_key] = elegido.name
    _save_rotation_state(state)

    return elegido


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
    try:
        pdf.set_alpha(alpha)
        pdf.set_fill_color(*color)
        pdf.rect(0, 0, PAGE_W, PAGE_H, "F")
        pdf.set_alpha(1)
    except Exception:
        pass


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
    """
    Dibuja una caja redondeada con transparencia real.

    Usa primero local_context(fill_opacity/stroke_opacity), que es la via mas
    fiable en fpdf2. Si la version instalada no lo soporta, cae a set_alpha.
    """
    fill_alpha = max(0.0, min(1.0, float(fill_alpha)))
    border_alpha = max(0.0, min(1.0, float(border_alpha)))

    def _rounded(style: str) -> None:
        try:
            pdf.rounded_rect(x, y, w, h, radius, style)
        except Exception:
            pdf.rect(x, y, w, h, style)

    try:
        with pdf.local_context(fill_opacity=fill_alpha, stroke_opacity=border_alpha):
            pdf.set_fill_color(*fill)
            pdf.set_draw_color(*border)
            pdf.set_line_width(line_width)
            _rounded("DF")
        return
    except Exception:
        pass

    try:
        pdf.set_alpha(fill_alpha)
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(*fill)
        pdf.set_line_width(0.01)
        _rounded("F")

        pdf.set_alpha(border_alpha)
        pdf.set_draw_color(*border)
        pdf.set_line_width(line_width)
        _rounded("D")

        pdf.set_alpha(1)
    except Exception:
        try:
            pdf.set_alpha(1)
        except Exception:
            pass
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(*border)
        pdf.set_line_width(line_width)
        _rounded("DF")


def _draw_page_border(pdf: "MapaPDF", key: str) -> None:
    _bg, _cream, gold, _accent = _palette(key)

    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.30)
    pdf.rect(8, 8, PAGE_W - 16, PAGE_H - 16)

    pdf.set_line_width(0.10)
    pdf.rect(13, 13, PAGE_W - 26, PAGE_H - 26)


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
            _pdf_image_cover(pdf, img, 0, 0, PAGE_W, PAGE_H)
            bg, _cream, _gold, _accent = _palette(key)
            _draw_overlay(pdf, bg, overlay)
        except Exception as exc:
            if _debug_assets():
                print(f"[PDF_DEBUG_ASSETS] Fallo cargando fondo {img}: {exc}")
            _draw_gradient_bg(pdf, key)
    else:
        if _debug_assets():
            print(f"[PDF_DEBUG_ASSETS] No hay fondo para seccion: {key} en {_assets_img_dir()}")
        _draw_gradient_bg(pdf, key)

    if draw_border:
        _draw_page_border(pdf, key)


def _draw_logo_if_exists(pdf: "MapaPDF", x: float, y: float, w: float) -> None:
    # Logo oficial solicitado: app/assets/imagenes/logo.png
    # Mantiene alternativas para no romper instalaciones anteriores.
    logo = _find_image_by_names(["logo", "Logo", "LOGO", "el_nombre_que_me_habita", "sello"])

    if logo:
        try:
            _pdf_image(pdf, logo, x, y, w=w)
        except Exception:
            pass


def _line_height(font_size: float) -> float:
    # Un poco mas de aire entre lineas para que no parezca contrato.
    return font_size * 0.47


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
        lines = _estimate_lines(pdf, text, width - 14, size)
        needed = lines * _line_height(size) + 14

        if needed <= height:
            return size

        size -= 0.15

    return minimum


def _draw_soft_panel(
    pdf: "MapaPDF",
    x: float,
    y: float,
    w: float,
    h: float,
    key: str,
    alpha: float = 0.50,
) -> None:
    _bg, _cream, gold, accent = _palette(key)

    # Fondo azul oscuro / casi negro, 50% transparente o mas, como solicitado.
    # No usamos blanco ni crema para el cuerpo de texto.
    fill = (10, 17, 34)
    border = tuple(int(gold[i] * 0.86 + accent[i] * 0.14) for i in range(3))

    _draw_rounded_transparent_rect(
        pdf,
        x,
        y,
        w,
        h,
        8,
        fill,
        border,
        fill_alpha=alpha,
        border_alpha=0.82,
        line_width=0.32,
    )


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
    _draw_soft_panel(pdf, x, y, w, h, key)

    pdf.set_xy(x + 7, y + 7)
    pdf.set_font(pdf.font_body, "", font_size)
    pdf.set_text_color(252, 244, 222)

    paragraphs = [
        _clean_text(p)
        for p in re.split(r"\n\s*\n", _clean_text(text, keep_breaks=True))
        if _clean_text(p)
    ]

    if not paragraphs:
        return

    line_h = _line_height(font_size)

    for idx, paragraph in enumerate(paragraphs):
        if idx > 0:
            pdf.ln(2.0)
        pdf.set_x(x + 7)
        pdf.multi_cell(w - 14, line_h, _safe(paragraph), align="J")


def _section_combined_text(sec: dict[str, str]) -> str:
    p1 = _clean_text(sec.get("primera_lectura"))
    p2 = _clean_text(sec.get("profundizacion"))
    p3 = _clean_text(sec.get("integracion"))

    return "\n\n".join(part for part in (p1, p2, p3) if part)


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

        self.title_font_options: list[tuple[str, str]] = [("Times", "B")]
        self.subtitle_font_options: list[tuple[str, str]] = [("Times", "I")]
        self.name_font_options: list[tuple[str, str]] = [("Times", "I")]
        self._font_choice_cache: dict[str, tuple[str, str]] = {}
        self._font_rng = random.Random(f"{time.time_ns()}-{random.random()}")

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

        # Titulos editoriales premium: sobrios, misticos y legibles.
        if self._try_font("CinzelPDF", "", "Cinzel-VariableFont_wght.ttf"):
            title_options.append(("CinzelPDF", ""))
            self.font_title = "CinzelPDF"

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
            self.font_accent = "MerriPDF"
            if self._try_font("MerriPDF", "I", "Merriweather-Italic-VariableFont_opsz,wdth,wght.ttf"):
                subtitle_options.append(("MerriPDF", "I"))
                name_options.append(("MerriPDF", "I"))

        # Letra corrida decorativa: usar solo en subtitulos/nombre, no en parrafos.
        if self._try_font("PlaywriteIE", "", "PlaywriteIE-VariableFont_wght.ttf"):
            self.font_script = "PlaywriteIE"
            subtitle_options.append(("PlaywriteIE", ""))
            name_options.append(("PlaywriteIE", ""))

        # Fuentes limpias para metadatos y apoyo visual.
        if self._try_font("MontserratPDF", "", "Montserrat-VariableFont_wght.ttf"):
            self.font_subtitle = "MontserratPDF"
            if self._try_font("MontserratPDF", "I", "Montserrat-Italic-VariableFont_wght.ttf"):
                subtitle_options.append(("MontserratPDF", "I"))

        if self._try_font("PoppinsPDF", "", "Poppins-Regular.ttf"):
            if self.font_subtitle == "Times":
                self.font_subtitle = "PoppinsPDF"
            self._try_font("PoppinsPDF", "B", "Poppins-SemiBold.ttf")
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
            self._font_choice_cache[cache_key] = self._font_rng.choice(options)
        return self._font_choice_cache[cache_key]

    def title_font_for(self, key: str) -> tuple[str, str]:
        return self._choose_font_once("title", key, self.title_font_options)

    def subtitle_font_for(self, key: str) -> tuple[str, str]:
        return self._choose_font_once("subtitle", key, self.subtitle_font_options)

    def name_font_for(self, key: str) -> tuple[str, str]:
        return self._choose_font_once("name", key, self.name_font_options)

    def footer(self) -> None:
        if self.page_no() <= 1:
            return

        # Footer fuera del marco inferior para que el fondo no sea cortado por la linea del borde.
        # Mantiene legibilidad sin tapar ni cruzar el marco decorativo.
        footer_y = PAGE_H - 7.1
        footer_h = 4.8

        try:
            self.set_alpha(0.72)
            self.set_fill_color(8, 14, 30)
            self.rect(43, footer_y, PAGE_W - 86, footer_h, "F")
            self.set_alpha(1)
        except Exception:
            pass

        self.set_y(footer_y + 0.35)
        self.set_font(self.font_subtitle, "", 6.8)
        self.set_text_color(255, 232, 170)
        self.cell(
            0,
            4.0,
            _safe(f"Mapa del Alma - El nombre que me habita - Pagina {self.page_no()}"),
            align="C",
        )


def _draw_header_block(pdf: MapaPDF, key: str, datos: dict[str, Any]) -> None:
    _bg, _cream, gold, accent = _palette(key)

    title = SECTION_TITLES[key]
    heading = PAGE_HEADINGS.get(key, "")

    nombre = _nombre_completo(datos)
    fecha = _clean_text(datos.get("fecha_nacimiento") or datos.get("fecha") or "")

    # Cabecera azul oscuro/casi negro, semitransparente y redondeada.
    header_fill = (8, 14, 30)
    header_border = tuple(int(gold[i] * 0.88 + accent[i] * 0.12) for i in range(3))

    _draw_rounded_transparent_rect(
        pdf,
        20,
        18,
        PAGE_W - 40,
        50,
        8,
        header_fill,
        header_border,
        fill_alpha=0.68,
        border_alpha=0.90,
        line_width=0.34,
    )

    title_font, title_style = pdf.title_font_for(key)
    subtitle_font, subtitle_style = pdf.subtitle_font_for(key)

    pdf.set_text_color(*gold)
    pdf.set_font(title_font, title_style, 18.2)
    pdf.set_xy(24, 25)
    pdf.cell(PAGE_W - 48, 8, _safe(title).upper(), align="C")

    pdf.set_text_color(255, 250, 232)
    # Subtitulo legible: no usamos fuente corrida aqui porque en pequeno se pierde.
    pdf.set_font(pdf.font_subtitle, "", 11.8)
    pdf.set_xy(25, 37.5)
    pdf.cell(PAGE_W - 50, 6.4, _safe(heading), align="C")

    meta = f"{nombre}"
    if fecha:
        meta = f"{nombre} - {fecha}"

    pdf.set_text_color(255, 238, 198)
    pdf.set_font(pdf.font_subtitle, "", 9.6)
    pdf.set_xy(25, 50)
    pdf.cell(PAGE_W - 50, 6.2, _safe(meta), align="C")

    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.22)
    pdf.line(47, 60, PAGE_W - 47, 60)


def _section_layout(index: int) -> tuple[float, float, float, float]:
    layouts = [
        # Paneles más amplios: permiten letra mayor sin dejar páginas vacías.
        (15, 70, 186, 198),
        (17, 71, 182, 197),
        (14, 72, 188, 196),
        (18, 70, 180, 198),
    ]
    return layouts[(index - 1) % len(layouts)]


def _render_section_page(
    pdf: MapaPDF,
    key: str,
    sec: dict[str, str],
    datos: dict[str, Any],
    index: int,
) -> None:
    pdf.add_page()

    _page_bg(pdf, key, datos, overlay=0.015)
    _draw_header_block(pdf, key, datos)

    combined = _section_combined_text(sec)
    x, y, w, h = _section_layout(index)

    word_count = _count_words(combined)

    # Letra mas grande y nunca microscopica.
    if word_count < 430:
        start_size = 11.0
    elif word_count < 560:
        start_size = 10.1
    elif word_count < 700:
        start_size = 9.2
    else:
        start_size = 8.4

    font_size = _fit_font_for_panel(pdf, combined, w, h - 4, start=start_size, minimum=7.75)

    if _debug_assets():
        print(f"[PDF_DEBUG_ASSETS] {key}: palabras={word_count}, font_size={font_size:.2f}, panel_alpha=0.50_dark")

    _write_panel_text(pdf, combined, x, y, w, h, key, font_size)


def _render_notes_page(pdf: MapaPDF, datos: dict[str, Any]) -> None:
    pdf.add_page()

    # La imagen notas_*.jpeg ya trae el titulo NOTAS y las lineas de escritura.
    # No dibujamos borde exterior porque la imagen ya trae su propio diseno.
    _page_bg(pdf, "notas", datos, overlay=0.006, draw_border=False)


def _cover(pdf: MapaPDF, datos: dict[str, Any]) -> None:
    pdf.add_page()

    _page_bg(pdf, "portada", datos, overlay=0.015)

    nombre = _nombre_completo(datos)
    fecha = _clean_text(datos.get("fecha_nacimiento") or datos.get("fecha") or "")
    sexo = _sexo_normalizado(datos.get("sexo") or datos.get("genero") or datos.get("forma_trato"))

    if sexo == "mujer":
        para = "ella"
    elif sexo == "hombre":
        para = "el"
    else:
        para = "su alma"

    _bg, _cream, gold, accent = _palette("portada")

    cover_fill = (8, 14, 30)
    cover_border = tuple(int(gold[i] * 0.88 + accent[i] * 0.12) for i in range(3))

    _draw_rounded_transparent_rect(
        pdf,
        24,
        62,
        PAGE_W - 48,
        126,
        10,
        cover_fill,
        cover_border,
        fill_alpha=0.66,
        border_alpha=0.90,
        line_width=0.34,
    )

    cover_subtitle_font, cover_subtitle_style = pdf.subtitle_font_for("portada_marca")
    cover_title_font, cover_title_style = pdf.title_font_for("portada_titulo")
    cover_name_font, cover_name_style = pdf.name_font_for("portada_nombre")

    pdf.set_text_color(*gold)
    pdf.set_font(pdf.font_subtitle, "", 11.4)
    pdf.set_xy(0, 75)
    pdf.cell(PAGE_W, 7, _safe("EL NOMBRE QUE ME HABITA"), align="C")

    pdf.set_text_color(252, 244, 222)
    pdf.set_font(cover_title_font, cover_title_style, 35)
    pdf.set_xy(25, 96)
    pdf.cell(PAGE_W - 50, 15, _safe("MAPA"), align="C")

    pdf.set_xy(25, 115)
    pdf.cell(PAGE_W - 50, 15, _safe("DEL ALMA"), align="C")

    pdf.set_draw_color(*gold)
    pdf.set_line_width(0.34)
    pdf.line(50, 140, PAGE_W - 50, 140)

    pdf.set_text_color(245, 226, 184)
    pdf.set_font(cover_name_font, cover_name_style, 15)
    pdf.set_xy(25, 150)
    pdf.cell(PAGE_W - 50, 10, _safe(nombre), align="C")

    pdf.set_font(pdf.font_subtitle, "", 9.6)
    pdf.set_text_color(255, 238, 198)

    if fecha:
        pdf.set_xy(30, 166)
        pdf.cell(PAGE_W - 60, 5.8, _safe(f"Fecha de nacimiento: {fecha}"), align="C")

    pdf.set_xy(30, 176)
    pdf.cell(PAGE_W - 60, 5.8, _safe(f"Lectura simbolica personalizada para {para}"), align="C")

    _draw_logo_if_exists(pdf, PAGE_W - 46, PAGE_H - 43, 29)


def _back_cover(pdf: MapaPDF, datos: dict[str, Any]) -> None:
    pdf.add_page()

    _page_bg(pdf, "contraportada", datos, overlay=0.018, draw_border=False)

    nombre = _nombre_completo(datos)
    _bg, _cream, gold, accent = _palette("contraportada")

    back_fill = (8, 14, 30)
    back_border = tuple(int(gold[i] * 0.88 + accent[i] * 0.12) for i in range(3))

    _draw_rounded_transparent_rect(
        pdf,
        23,
        35,
        PAGE_W - 46,
        202,
        10,
        back_fill,
        back_border,
        fill_alpha=0.66,
        border_alpha=0.90,
        line_width=0.34,
    )

    back_title_font, back_title_style = pdf.title_font_for("contraportada_titulo")
    back_subtitle_font, back_subtitle_style = pdf.subtitle_font_for("contraportada_subtitulo")

    pdf.set_text_color(*gold)
    pdf.set_font(back_title_font, back_title_style, 21.5)
    pdf.set_xy(28, 51)
    pdf.cell(PAGE_W - 56, 12, _safe("TU MAPA ESTA COMPLETO"), align="C")

    pdf.set_font(back_subtitle_font, back_subtitle_style, 9.5)
    pdf.set_text_color(252, 244, 222)
    pdf.set_xy(36, 73)
    pdf.multi_cell(
        PAGE_W - 72,
        5.2,
        _safe(
            f"{nombre}, este libro fue creado como una lectura simbolica para recordar tu nombre, "
            "tu energia y la fuerza que puedes elegir encarnar."
        ),
        align="C",
    )

    items = [
        "21 lecturas interiores personalizadas",
        "Nombre, linaje, esencia y energia",
        "Zodiaco occidental y zodiaco chino",
        "Numerologia, animal totem, angel y piedra",
        "Dones, sombras, herida, proposito y vinculos",
        "Dinero, ritual, afirmaciones y mensaje final",
        "Esencia del Alma y pagina de notas",
    ]

    x, y, w, h = 34, 108, PAGE_W - 68, 88

    _draw_soft_panel(pdf, x, y, w, h, "contraportada", alpha=0.50)

    pdf.set_text_color(*gold)
    pdf.set_font(pdf.font_subtitle, "B" if pdf.font_subtitle == "Times" else "", 8.5)
    pdf.set_xy(x + 8, y + 9)
    pdf.cell(w - 16, 6, _safe("ESTE LIBRO INCLUYE"), align="C")

    pdf.set_font(pdf.font_body, "", 8.2)
    pdf.set_text_color(252, 244, 222)

    current_y = y + 26

    for item in items:
        pdf.set_xy(x + 14, current_y)
        pdf.cell(w - 28, 6.7, _safe(f"- {item}"), align="L")
        current_y += 7.0

    _draw_logo_if_exists(pdf, PAGE_W - 48, PAGE_H - 47, 32)

    pdf.set_font(pdf.font_subtitle, "", 9.2)
    pdf.set_text_color(255, 232, 170)
    pdf.set_xy(35, 247)
    pdf.cell(PAGE_W - 70, 6, _safe("El nombre que me habita"), align="C")


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

    secciones = _extraer_contenido_openai(datos_pedido)

    faltantes = [key for key in SECTION_ORDER if key not in secciones]
    if faltantes:
        raise RuntimeError(f"Faltan secciones obligatorias para generar el PDF: {faltantes}")

    pdf = MapaPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_title("Mapa del Alma")
    pdf.set_author("El nombre que me habita")

    _cover(pdf, datos_pedido)

    for index, key in enumerate(SECTION_ORDER, start=1):
        _render_section_page(pdf, key, secciones[key], datos_pedido, index)

    _render_notes_page(pdf, datos_pedido)

    _back_cover(pdf, datos_pedido)

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