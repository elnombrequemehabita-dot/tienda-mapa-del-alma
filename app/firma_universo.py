"""
Firma del Universo V9 — ADN visual único por persona.

Semilla determinista (SHA-256 sobre nombre + número maestro + vibración de letras; sin
hash() de Python, que no es estable entre procesos). Patrón único por persona.
Geometría variable: nombre corto → sello minimalista;
nombre largo → sello complejo. El número maestro se integra en anillos y nodos centrales.
"""
from __future__ import annotations

import hashlib
import math
import random
from datetime import date

from config import FONT_DETAIL_POPPINS, FONT_TITLE_FIRE_EARTH, FONT_TITLE_WATER_AIR


def _first_registered_font(candidates: tuple[str, ...]) -> str:
    from reportlab.pdfbase import pdfmetrics  # noqa: PLC0415

    names = set(pdfmetrics.getRegisteredFontNames())
    for cand in candidates:
        if cand in names:
            return cand
    raise RuntimeError(f"No hay fuente registrada disponible entre: {candidates}")


def _letter_vibration_sum(nombre: str) -> int:
    """Suma posiciones A=1…Z=26 y dígitos del nombre (vibración alfabética simple)."""
    s = 0
    for c in nombre.strip().upper():
        if "A" <= c <= "Z":
            s += ord(c) - 64
        elif c.isdigit():
            s += int(c)
    return max(1, s)


def firma_adn_seed(nombre: str, numero_maestro: int, fecha_nacimiento: date | None = None) -> int:
    """
    Semilla estable de 64 bits: ADN = nombre + número maestro + vibración de letras + longitud.
    Opcional: mezcla con fecha de nacimiento para mayor entropía sin colisiones entre gemelos.
    """
    n = nombre.strip()
    lv = _letter_vibration_sum(n)
    payload = f"{n}|{numero_maestro}|{lv}|{len(n)}"
    h = hashlib.sha256(payload.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "big")
    if fecha_nacimiento is not None:
        mix = hashlib.sha256(fecha_nacimiento.isoformat().encode("utf-8")).digest()
        seed ^= int.from_bytes(mix[:8], "big")
    return seed


def dibujar_firma_universo(
    canvas,
    x: float,
    y: float,
    nombre: str,
    numero_maestro: int,
    *,
    size: float = 92.0,
    fecha_nacimiento: date | None = None,
    box_width: float = 420.0,
    leyenda: str | None = None,
) -> float:
    """
    Sello geométrico único: cínculos, radios, estrella/polígono, destellos y anillo de integración
    del número maestro en el centro. Devuelve altura total del bloque (leyenda + sello).

    (x, y) esquina inferior izquierda del bloque en puntos canvas.
    """
    from reportlab.pdfbase import pdfmetrics  # noqa: PLC0415 — solo para medir texto

    seed = firma_adn_seed(nombre, numero_maestro, fecha_nacimiento)
    rnd = random.Random(seed)

    L = len(nombre.strip().replace(" ", ""))
    L = max(1, L)
    lv = _letter_vibration_sum(nombre)
    minimalist = L <= 9
    maximal = L >= 18

    cx = x + box_width / 2.0
    g_r, g_g, g_b = 0.82, 0.68, 0.32

    fs_ley = 9.4 + min(2.2, box_width / 320.0)
    legend_font = _first_registered_font((FONT_DETAIL_POPPINS,))
    max_text_w = max(160.0, box_width - 56.0)
    legend_txt = (
        "Esta es tu Firma del Universo: ADN visual único nacido de tu nombre y tu número maestro."
        if leyenda is None
        else leyenda.strip()
    )
    caption_lines = (
        _split_lines(legend_txt, max_text_w, legend_font, fs_ley) if legend_txt else []
    )
    line_gap = fs_ley + 2.2
    caption_h = len(caption_lines) * line_gap + 10.0

    canvas.saveState()
    canvas.setFont(legend_font, fs_ley)
    canvas.setFillColorRGB(0.88, 0.82, 0.94)
    for i, line in enumerate(caption_lines):
        canvas.drawCentredString(cx, y + i * line_gap, line)

    seal_bottom = y + caption_h
    cy = seal_bottom + size / 2.0

    # —— Complejidad según longitud del nombre ——
    n_circ = 2 + (L // 4) % 4
    if maximal:
        n_circ = min(8, n_circ + 2)
    if minimalist:
        n_circ = max(2, n_circ - 1)

    scale = max(1.0, size / 92.0)
    lw_base = (0.22 + (lv % 25) * 0.016 + (numero_maestro % 7) * 0.014) * min(1.55, scale)
    if minimalist:
        lw_base *= 0.92

    # Círculos concéntricos (grosor y radios variables; trazo más denso = “cuño” más fuerte)
    for i in range(n_circ):
        r = size * (0.12 + i * (0.78 / max(n_circ, 1)))
        w = lw_base + i * (0.055 if maximal else 0.042)
        alpha = 0.58 + (i % 3) * 0.12
        canvas.setStrokeColorRGB(g_r, g_g, g_b, alpha=min(0.95, alpha))
        canvas.setLineWidth(min(3.45, w))
        canvas.circle(cx, cy, r, stroke=1, fill=0)

    # Radios: número y ángulo dependen de vibración y número maestro
    n_ray = 6 + (lv % 14) + (numero_maestro % 9)
    if minimalist:
        n_ray = max(6, n_ray // 2 + 3)
    if maximal:
        n_ray += 6 + rnd.randint(0, 8)

    r_outer = size * (0.38 + (seed % 5) * 0.02)
    r_inner = size * (0.08 + (lv % 5) * 0.015)
    rot = (lv * 0.0174533) % (math.pi / 4) + rnd.uniform(0, math.pi / 12)
    canvas.setStrokeColorRGB(g_r, g_g, g_b, alpha=0.92)
    for k in range(n_ray):
        ang = rot + (k / n_ray) * 2 * math.pi
        lw = lw_base + (k % 4) * 0.09
        canvas.setLineWidth(min(3.15, lw))
        canvas.line(
            cx + r_inner * math.cos(ang),
            cy + r_inner * math.sin(ang),
            cx + r_outer * math.cos(ang),
            cy + r_outer * math.sin(ang),
        )

    # Estrella / polígono irregular (puntas variables)
    n_pts = 5 + (seed % 11)
    if minimalist:
        n_pts = max(4, n_pts // 2 + 2)
    if maximal:
        n_pts += 3 + rnd.randint(0, 4)

    pts = []
    for k in range(n_pts):
        ang = (k / n_pts) * 2 * math.pi + rnd.uniform(-0.1, 0.1) + rot * 0.3
        rr = size * (0.22 + rnd.random() * (0.14 if maximal else 0.1))
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    canvas.setStrokeColorRGB(g_r, g_g, g_b, alpha=0.82)
    canvas.setLineWidth(lw_base + 0.16)
    for k in range(n_pts):
        x1, y1 = pts[k]
        x2, y2 = pts[(k + 1) % n_pts]
        canvas.line(x1, y1, x2, y2)

    # Destellos: más en nombres largos
    n_spark = 8 + (L * 2) % 22
    if maximal:
        n_spark += 20
    if minimalist:
        n_spark = max(6, n_spark // 2)
    canvas.setFillColorRGB(0.95, 0.86, 0.5, alpha=0.42)
    for _ in range(n_spark):
        ang = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(size * 0.18, size * 0.48)
        pr = 0.45 + rnd.uniform(0, 1.1)
        canvas.circle(cx + rr * math.cos(ang), cy + rr * math.sin(ang), pr, stroke=0, fill=1)

    # —— Integración del número maestro en el diseño (no solo texto) ——
    nm = abs(int(numero_maestro)) % 100
    sum_digits = sum(int(d) for d in str(nm)) if nm else 1
    n_nodes = max(3, min(24, sum_digits + (nm % 7) + 3))
    r_ring = size * (0.14 + (lv % 5) * 0.012)
    rot2 = rot + (nm * math.pi / 180.0)
    canvas.setFillColorRGB(g_r, g_g, g_b, alpha=0.55)
    for j in range(n_nodes):
        ang = rot2 + (j / n_nodes) * 2 * math.pi
        px = cx + r_ring * math.cos(ang)
        py = cy + r_ring * math.sin(ang)
        pr = 1.0 + (j % 3) * 0.35
        canvas.circle(px, py, pr, stroke=0, fill=1)

    # Arcos elípticos breves (bbox + grados, ReportLab): refuerzan el número en el centro
    n_arc = 3 + (nm % 9)
    canvas.setStrokeColorRGB(g_r, g_g, g_b, alpha=0.45)
    canvas.setLineWidth(lw_base * 0.9)
    for a in range(n_arc):
        r_a = size * (0.1 + (a % 4) * 0.018)
        start_deg = (a * (360.0 / n_arc) + rot2 * 180.0 / math.pi) % 360.0
        extent_deg = 22.0 + (nm % 18)
        canvas.arc(cx - r_a, cy - r_a, cx + r_a, cy + r_a, start_deg, extent_deg)

    # Texto del número al centro (sobre la geometría integrada)
    num_txt = str(numero_maestro)
    fs_num = 18 + int(scale * 4) if len(num_txt) <= 2 else 13 + int(scale * 2)
    fs_num += 1 if minimalist else 0
    fs_num = min(36, fs_num + (nm % 4) + int(size / 50.0))
    canvas.setFillColorRGB(g_r, g_g, g_b)
    number_font = _first_registered_font((FONT_TITLE_WATER_AIR, FONT_TITLE_FIRE_EARTH))
    canvas.setFont(number_font, fs_num)
    tw = pdfmetrics.stringWidth(num_txt, number_font, fs_num)
    canvas.drawCentredString(cx, cy - fs_num * 0.35, num_txt)
    # subrayado sagrado opcional (línea fina bajo el número)
    canvas.setLineWidth(0.35)
    canvas.line(cx - tw / 2 - 2, cy - fs_num * 0.85, cx + tw / 2 + 2, cy - fs_num * 0.85)

    canvas.restoreState()
    return caption_h + size + 18.0


def _split_lines(text: str, max_width: float, font_name: str, font_size: float) -> list[str]:
    from reportlab.pdfbase import pdfmetrics  # noqa: PLC0415

    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        if pdfmetrics.stringWidth(trial, font_name, font_size) <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def estimate_firma_block_height(
    box_width: float,
    size: float = 92.0,
    leyenda: str | None = None,
) -> float:
    """Altura para Flowable.wrap (misma lógica que dibujar_firma_universo)."""
    txt = (
        "Esta es tu Firma del Universo: ADN visual único nacido de tu nombre y tu número maestro."
        if leyenda is None
        else leyenda.strip()
    )
    fs_ley = 9.4 + min(2.2, box_width / 320.0)
    legend_font = _first_registered_font((FONT_DETAIL_POPPINS,))
    max_text_w = max(160.0, box_width - 56.0)
    caption_lines = _split_lines(txt, max_text_w, legend_font, fs_ley) if txt else []
    line_gap = fs_ley + 2.2
    caption_h = len(caption_lines) * line_gap + 10.0
    return caption_h + size + 18.0
