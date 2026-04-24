from __future__ import annotations

import importlib
import logging
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _parse_fecha(fecha_nacimiento: str) -> datetime.date:
    raw = str(fecha_nacimiento or "").strip()
    if not raw:
        raise RuntimeError("fecha_nacimiento vacia para motor premium.")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError as exc:
        raise RuntimeError(f"fecha_nacimiento invalida: {raw}") from exc


def _sexo_desde_forma_trato(forma_trato: str) -> str:
    ft = str(forma_trato or "").strip().lower()
    if any(token in ft for token in ("sr", "hombre", "caballero", "masc", "el")):
        return "masculino"
    return "femenino"


def _load_motor_modules():
    engine_dir = Path(__file__).resolve().parent / "mapa_del_alma_v2"
    if not engine_dir.exists():
        raise RuntimeError(f"No existe el motor premium en: {engine_dir}")
    engine_dir_str = str(engine_dir)
    if engine_dir_str not in sys.path:
        sys.path.insert(0, engine_dir_str)
    for module_name in (
        "config",
        "utils",
        "onomastica",
        "logic",
        "narrative_sanitize",
        "narrative_banks_v15",
        "narrative",
        "image_assets",
        "editorial_flowables",
        "firma_universo",
        "pdf_engine",
        "generador_texto",
        "generador_pdf",
    ):
        sys.modules.pop(module_name, None)
    logic = importlib.import_module("logic")
    narrative = importlib.import_module("narrative")
    generador_pdf = importlib.import_module("generador_pdf")
    return logic, narrative, generador_pdf


def generar_mapa_real_pdf(
    *,
    nombre: str,
    apellidos: str,
    fecha_nacimiento: str,
    forma_trato: str,
    email: str,
    pedido_id: int,
) -> bytes:
    logger.info("motor premium iniciado")
    _ = str(email or "").strip()
    fecha = _parse_fecha(fecha_nacimiento)
    sexo = _sexo_desde_forma_trato(forma_trato)

    logic, narrative, generador_pdf = _load_motor_modules()
    profile = logic.build_profile(
        str(nombre or "").strip(),
        fecha,
        apellidos=str(apellidos or "").strip(),
        sexo=sexo,
    )
    book = narrative.build_narrative(profile)

    project_root = Path(__file__).resolve().parent.parent
    output_path = project_root / "output" / f"mapa_alma_{int(pedido_id)}.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_path = Path(generador_pdf.build_pdf(profile, book, output_path=output_path))
    pdf_bytes = final_path.read_bytes()

    logger.info("PDF premium generado")
    logger.info("ruta final: %s", str(final_path))
    logger.info("tamaño del PDF: %s", len(pdf_bytes))
    return pdf_bytes