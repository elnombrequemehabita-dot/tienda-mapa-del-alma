"""
Generador REAL del PDF del Mapa del Alma.

Si no puede generar el documento, debe lanzar una excepción para que
el flujo post-pago marque error.
"""
from __future__ import annotations

import importlib
import os
from typing import Any, Callable


def _load_real_generator() -> Callable[..., Any]:
    """
    Carga la función REAL de generación PDF desde un módulo externo.
    Sin fallback de prueba: si no está configurado o falla la carga, lanza excepción.
    """
    ref = (os.environ.get("MAPA_REAL_PDF_GENERATOR") or "").strip()
    if not ref:
        raise RuntimeError(
            "MAPA_REAL_PDF_GENERATOR no configurado. "
            "Debes definirlo como 'modulo.funcion' (ej: 'mapa_premium_final_global.generar_pdf')."
        )
    if "." not in ref:
        raise RuntimeError("MAPA_REAL_PDF_GENERATOR inválido: usa formato 'modulo.funcion'.")
    module_name, func_name = ref.rsplit(".", 1)
    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"No se pudo importar el módulo real '{module_name}': {exc}") from exc
    fn = getattr(mod, func_name, None)
    if not callable(fn):
        raise RuntimeError(f"La función real '{func_name}' no existe o no es callable en '{module_name}'.")
    return fn


def generate_real_mapa_pdf(
    *,
    pedido_id: int,
    codigo_confirmacion: str,
    nombre: str,
    apellidos: str,
    fecha_nacimiento: str,
    forma_trato: str,
    email: str,
    idioma: str,
) -> bytes:
    """
    Genera el PDF real del pedido usando datos personalizados del cliente.
    """
    nombre_clean = str(nombre or "").strip()
    apellidos_clean = str(apellidos or "").strip()
    email_clean = str(email or "").strip()
    if not nombre_clean:
        raise RuntimeError(f"Pedido #{pedido_id} inválido: falta nombre para generar el PDF real.")
    if not apellidos_clean:
        raise RuntimeError(f"Pedido #{pedido_id} inválido: falta apellidos para generar el PDF real.")
    if not email_clean:
        raise RuntimeError(f"Pedido #{pedido_id} inválido: falta email para generar el PDF real.")
    real_fn = _load_real_generator()
    payload = {
        "pedido_id": int(pedido_id),
        "codigo_confirmacion": str(codigo_confirmacion),
        "nombre": nombre_clean,
        "apellidos": apellidos_clean,
        "fecha_nacimiento": str(fecha_nacimiento or "").strip(),
        "forma_trato": str(forma_trato or "").strip(),
        "email": email_clean,
        "idioma": str(idioma or "").strip() or "es",
    }
    result = real_fn(**payload)
    if isinstance(result, bytes):
        if not result:
            raise RuntimeError("El generador real devolvió bytes vacíos.")
        return result
    raise RuntimeError(
        "El generador real debe devolver bytes del PDF. "
        f"Tipo recibido: {type(result).__name__}"
    )

