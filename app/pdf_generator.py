"""
Generador REAL del PDF del Mapa del Alma.

El punto de entrada unico del motor premium es `app.mapa_real`.
Sin fallback de prueba: si falla, se propaga el error.
"""
from __future__ import annotations

from app import mapa_real


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
    _ = str(codigo_confirmacion or "").strip()
    _ = str(idioma or "").strip() or "es"
    result = mapa_real.generar_mapa_real_pdf(
        nombre=nombre_clean,
        apellidos=apellidos_clean,
        fecha_nacimiento=str(fecha_nacimiento or "").strip(),
        forma_trato=str(forma_trato or "").strip(),
        email=email_clean,
        pedido_id=int(pedido_id),
    )
    if not isinstance(result, bytes):
        raise RuntimeError(
            "El generador real debe devolver bytes del PDF. "
            f"Tipo recibido: {type(result).__name__}"
        )
    if not result:
        raise RuntimeError("El generador real devolvio bytes vacios.")
    return result

