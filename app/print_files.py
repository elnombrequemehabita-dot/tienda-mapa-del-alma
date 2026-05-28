from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from pypdf import PdfReader, PdfWriter

Image.MAX_IMAGE_PIXELS = None


DEFAULT_PAGE_WIDTH_IN = 8.5
DEFAULT_PAGE_HEIGHT_IN = 11.0
DEFAULT_DPI = 300
DEFAULT_SPINE_WIDTH_IN = 0.35


def hardcover_interior_output_path(input_pdf: Path, output_pdf: Optional[Path] = None) -> Path:
    source = Path(input_pdf)
    if output_pdf is not None:
        return Path(output_pdf)
    return source.with_name(f"{source.stem}_interior_tapa_dura.pdf")


def hardcover_cover_output_path(input_pdf: Path, output_pdf: Optional[Path] = None) -> Path:
    source = Path(input_pdf)
    if output_pdf is not None:
        return Path(output_pdf)
    return source.with_name(f"{source.stem}_cubierta_tapa_dura.pdf")


def hardcover_cover_parts_output_paths(
    output_dir: str | Path,
    prefix: str,
    *,
    extension: str = "png",
) -> dict[str, Path]:
    base = Path(output_dir)
    ext = "jpg" if extension.lower().lstrip(".") in {"jpg", "jpeg"} else "png"
    return {
        "portada": base / f"{prefix}_portada_8.5x11_300dpi.{ext}",
        "contraportada": base / f"{prefix}_contraportada_8.5x11_300dpi.{ext}",
        "lomo": base / f"{prefix}_lomo_300dpi.{ext}",
    }


def create_hardcover_interior_pdf(input_pdf: str | Path, output_pdf: str | Path | None = None) -> Path:
    """
    Crea el archivo interior para imprenta de tapa dura.

    El PDF generado por la tienda ya es el interior del libro:
    no incluye portada ni contraportada. Esta funcion solo crea una copia
    normalizada para imprenta sin eliminar paginas.
    """
    source = Path(input_pdf)
    if not source.exists():
        raise FileNotFoundError(f"No existe el PDF original: {source}")

    target = hardcover_interior_output_path(source, Path(output_pdf) if output_pdf else None)
    target.parent.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(source))
    if len(reader.pages) < 1:
        raise ValueError("El PDF no contiene paginas.")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(
        {
            "/Title": f"{source.stem} - interior tapa dura",
            "/Producer": "Mapa del Alma print files",
        }
    )

    with open(target, "wb") as f:
        writer.write(f)

    return target


def _cover_fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    source = image.convert("RGB")
    src_w, src_h = source.size

    scale = max(target_w / src_w, target_h / src_h)
    resized_w = int(round(src_w * scale))
    resized_h = int(round(src_h * scale))
    resized = source.resize((resized_w, resized_h), Image.Resampling.LANCZOS)

    left = max(0, (resized_w - target_w) // 2)
    top = max(0, (resized_h - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def _contain_on_blurred_canvas(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    source = image.convert("RGB")
    src_w, src_h = source.size

    background = _cover_fit(source, size).filter(ImageFilter.GaussianBlur(18))

    scale = min(target_w / src_w, target_h / src_h)
    resized_w = int(round(src_w * scale))
    resized_h = int(round(src_h * scale))
    foreground = source.resize((resized_w, resized_h), Image.Resampling.LANCZOS)

    x = (target_w - resized_w) // 2
    y = (target_h - resized_h) // 2
    background.paste(foreground, (x, y))
    return background


def _save_print_image(image: Image.Image, target: Path, dpi: int, image_format: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if image_format.upper() in {"JPG", "JPEG"}:
        image.convert("RGB").save(
            target,
            "JPEG",
            quality=95,
            dpi=(dpi, dpi),
            optimize=False,
            progressive=False,
            subsampling=0,
        )
    else:
        image.convert("RGB").save(target, "PNG", dpi=(dpi, dpi), optimize=True)


def _asset_image_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "assets" / "imagenes" / filename


def _add_cover_logo(image: Image.Image, dpi: int) -> Image.Image:
    logo_path = _asset_image_path("logo.png")
    if not logo_path.exists():
        return image.convert("RGB")

    canvas = image.convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    logo_w = int(round(1.10 * dpi))
    logo.thumbnail((logo_w, logo_w), Image.Resampling.LANCZOS)

    # Misma ubicacion discreta que el PDF original: abajo a la derecha,
    # sin tapar el titulo ni el bloque principal de lectura.
    margin_x = int(round(0.70 * dpi))
    margin_y = int(round(0.58 * dpi))
    x = max(0, canvas.width - logo.width - margin_x)
    y = max(0, canvas.height - logo.height - margin_y)

    alpha = logo.getchannel("A").point(lambda value: int(value * 0.94))
    logo.putalpha(alpha)
    canvas.alpha_composite(logo, (x, y))
    return canvas.convert("RGB")


def _font_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "assets" / "fuentes" / filename


def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = _font_path(filename)
    try:
        return ImageFont.truetype(str(path), size=size)
    except Exception:
        return ImageFont.load_default()


def _rotated_text_image(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    *,
    stroke_width: int = 1,
    stroke_fill: tuple[int, int, int] = (56, 35, 11),
) -> Image.Image:
    measure = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(measure)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = max(1, bbox[2] - bbox[0])
    th = max(1, bbox[3] - bbox[1])
    layer = Image.new("RGBA", (tw + 18, th + 18), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.text(
        (9 - bbox[0], 9 - bbox[1]),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    return layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)


def _paste_centered(canvas: Image.Image, layer: Image.Image, center_y: int) -> None:
    x = max(0, (canvas.width - layer.width) // 2)
    y = max(0, int(center_y - layer.height / 2))
    canvas.paste(layer, (x, y), layer)


def _make_narrow_spine(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    """
    Redibuja un lomo estrecho real para Mixam.

    En lomos de 0.35" no sirve recortar el arte ancho porque corta letras.
    Este diseno usa una composicion limpia azul/dorada y letras apiladas
    grandes para que el titulo siga siendo legible.
    """
    target_w, target_h = size
    canvas = Image.new("RGBA", (target_w, target_h), (4, 12, 30, 255))
    pixels = canvas.load()
    for y in range(target_h):
        t = y / max(1, target_h - 1)
        wave = 1.0 - abs(0.5 - t) * 2.0
        for x in range(target_w):
            glow = max(0.0, 1.0 - abs(x - target_w / 2) / max(1, target_w / 2))
            pixels[x, y] = (
                int(4 + 5 * glow),
                int(13 + 11 * wave + 9 * glow),
                int(32 + 38 * wave + 19 * glow),
                255,
            )

    draw = ImageDraw.Draw(canvas)
    gold = (222, 176, 88, 255)
    soft_gold = (246, 215, 145, 255)
    dark_gold = (61, 39, 13, 255)

    for i in range(90):
        x = 15 + ((i * 37) % max(1, target_w - 30))
        y = 50 + ((i * 211) % max(1, target_h - 100))
        alpha = 80 + ((i * 17) % 90)
        color = (245, 218, 150, alpha)
        if i % 10 == 0:
            draw.line((x - 3, y, x + 3, y), fill=color, width=1)
            draw.line((x, y - 3, x, y + 3), fill=color, width=1)
        else:
            draw.point((x, y), fill=color)

    margin_x = max(7, int(target_w * 0.09))
    draw.rectangle((margin_x, 28, target_w - margin_x - 1, target_h - 29), outline=gold, width=2)
    draw.rectangle((margin_x + 5, 66, target_w - margin_x - 6, target_h - 67), outline=(188, 138, 57, 170), width=1)

    center_x = target_w // 2
    for y in (165, target_h - 165):
        draw.line((center_x, y - 48, center_x, y + 48), fill=(224, 174, 78, 170), width=1)
        draw.line((center_x - 15, y, center_x + 15, y), fill=(224, 174, 78, 170), width=1)
        draw.ellipse((center_x - 5, y - 5, center_x + 5, y + 5), outline=gold, width=1)

    title_font = _load_font("Cinzel-VariableFont_wght.ttf", max(66, int(target_w * 0.78)))
    subtitle_font = _load_font("Cinzel-VariableFont_wght.ttf", max(14, int(target_w * 0.16)))
    small_font = _load_font("Cinzel-VariableFont_wght.ttf", max(11, int(target_w * 0.12)))

    def center_text(text: str, y: float, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, fill: tuple[int, int, int, int], stroke: int = 1) -> None:
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((target_w - tw) / 2 - bbox[0], y - bbox[1]),
            text,
            font=font,
            fill=fill,
            stroke_width=stroke,
            stroke_fill=dark_gold,
        )

    y = int(target_h * 0.17)
    step = max(86, int(target_h * 0.031))
    for group in ("MAPA", "DEL", "ALMA"):
        for char in group:
            center_text(char, y, title_font, soft_gold, 2)
            y += step
        y += int(step * 0.45)

    for line_y, line in zip(
        [int(target_h * 0.582), int(target_h * 0.601), int(target_h * 0.620), int(target_h * 0.639)],
        ["EL", "NOMBRE", "QUE ME", "HABITA"],
    ):
        center_text(line, line_y, subtitle_font, soft_gold, 1)

    moon_y = int(target_h * 0.742)
    draw.ellipse((center_x - 17, moon_y - 17, center_x + 17, moon_y + 17), fill=gold)
    draw.ellipse((center_x - 6, moon_y - 21, center_x + 21, moon_y + 12), fill=(6, 16, 34, 255))

    center_text("MAPA", int(target_h * 0.865), small_font, gold, 0)
    center_text("DEL ALMA", int(target_h * 0.878), small_font, gold, 0)

    for y in (int(target_h * 0.151), int(target_h * 0.557), int(target_h * 0.667), int(target_h * 0.800)):
        draw.line((center_x - 18, y, center_x + 18, y), fill=(224, 174, 78, 150), width=1)
        draw.ellipse((center_x - 2, y - 2, center_x + 2, y + 2), fill=gold)

    return canvas.convert("RGB")


def create_hardcover_cover_parts(
    front_image: str | Path,
    spine_image: str | Path,
    back_image: str | Path,
    output_dir: str | Path,
    *,
    prefix: str = "mapa_alma",
    page_width_in: float = DEFAULT_PAGE_WIDTH_IN,
    page_height_in: float = DEFAULT_PAGE_HEIGHT_IN,
    dpi: int = DEFAULT_DPI,
    spine_width_in: float | None = DEFAULT_SPINE_WIDTH_IN,
    image_format: str = "PNG",
) -> dict[str, Path]:
    """
    Crea piezas separadas para imprentas que piden:
    portada, contraportada y lomo como archivos individuales.
    """
    front_path = Path(front_image)
    spine_path = Path(spine_image)
    back_path = Path(back_image)
    for path in (front_path, spine_path, back_path):
        if not path.exists():
            raise FileNotFoundError(f"No existe imagen de cubierta: {path}")

    is_jpeg = image_format.upper() in {"JPG", "JPEG"}
    paths = hardcover_cover_parts_output_paths(output_dir, prefix, extension="jpg" if is_jpeg else "png")

    panel_size = (int(round(page_width_in * dpi)), int(round(page_height_in * dpi)))
    front = _add_cover_logo(_contain_on_blurred_canvas(Image.open(front_path), panel_size), dpi)
    back = _add_cover_logo(_contain_on_blurred_canvas(Image.open(back_path), panel_size), dpi)

    spine_src = Image.open(spine_path).convert("RGB")
    if spine_width_in is None:
        spine_width_in = max(0.25, page_height_in * (spine_src.width / max(1, spine_src.height)))
    spine_size = (int(round(spine_width_in * dpi)), panel_size[1])
    if spine_width_in <= 0.45:
        spine = _make_narrow_spine(spine_src, spine_size)
    else:
        spine = _cover_fit(spine_src, spine_size)

    _save_print_image(front, paths["portada"], dpi, "JPEG" if is_jpeg else "PNG")
    _save_print_image(back, paths["contraportada"], dpi, "JPEG" if is_jpeg else "PNG")
    _save_print_image(spine, paths["lomo"], dpi, "JPEG" if is_jpeg else "PNG")
    return paths


def create_hardcover_cover_pdf(
    input_pdf: str | Path,
    front_image: str | Path,
    spine_image: str | Path,
    back_image: str | Path,
    output_pdf: str | Path | None = None,
    *,
    page_width_in: float = DEFAULT_PAGE_WIDTH_IN,
    page_height_in: float = DEFAULT_PAGE_HEIGHT_IN,
    dpi: int = DEFAULT_DPI,
    spine_width_in: float | None = DEFAULT_SPINE_WIDTH_IN,
) -> Path:
    """
    Crea la cubierta completa para tapa dura:

    contraportada | lomo | portada

    Importante: el ancho exacto del lomo puede variar segun la imprenta,
    tipo de papel y encuadernacion.
    """
    source = Path(input_pdf)
    if not source.exists():
        raise FileNotFoundError(f"No existe el PDF original: {source}")

    front_path = Path(front_image)
    spine_path = Path(spine_image)
    back_path = Path(back_image)
    for path in (front_path, spine_path, back_path):
        if not path.exists():
            raise FileNotFoundError(f"No existe imagen de cubierta: {path}")

    target = hardcover_cover_output_path(source, Path(output_pdf) if output_pdf else None)
    target.parent.mkdir(parents=True, exist_ok=True)

    front = Image.open(front_path).convert("RGB")
    spine = Image.open(spine_path).convert("RGB")
    back = Image.open(back_path).convert("RGB")

    if spine_width_in is None:
        spine_width_in = max(0.25, page_height_in * (spine.width / max(1, spine.height)))

    panel_w = int(round(page_width_in * dpi))
    panel_h = int(round(page_height_in * dpi))
    spine_w = int(round(spine_width_in * dpi))
    total_w = (panel_w * 2) + spine_w

    canvas = Image.new("RGB", (total_w, panel_h), (8, 14, 30))
    spine_panel = _make_narrow_spine(spine, (spine_w, panel_h)) if spine_width_in <= 0.45 else _cover_fit(spine, (spine_w, panel_h))

    canvas.paste(_add_cover_logo(_cover_fit(back, (panel_w, panel_h)), dpi), (0, 0))
    canvas.paste(spine_panel, (panel_w, 0))
    canvas.paste(_add_cover_logo(_cover_fit(front, (panel_w, panel_h)), dpi), (panel_w + spine_w, 0))

    canvas.save(
        target,
        "PDF",
        resolution=float(dpi),
        quality=95,
        optimize=True,
    )
    return target
