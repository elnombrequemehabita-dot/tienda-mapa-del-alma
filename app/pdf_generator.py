"""
Generador REAL del PDF del Mapa del Alma.

Si no puede generar el documento, debe lanzar una excepción para que
el flujo post-pago marque error.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_single_page_pdf(lines: list[str]) -> bytes:
    """
    Genera un PDF válido de una página con contenido textual personalizado.
    """
    y_start = 780
    line_ops = ["BT", "/F1 11 Tf", f"48 {y_start} Td"]
    for i, line in enumerate(lines):
        if i > 0:
            line_ops.append("T*")
        line_ops.append(f"({_escape_pdf_text(line)}) Tj")
    line_ops.append("ET")
    stream = "\n".join(line_ops).encode("utf-8")

    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n"
    )
    objects.append(
        b"4 0 obj\n<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


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

    lines = [
        "EL NOMBRE QUE ME HABITA",
        "Mapa del Alma - Documento Personalizado",
        "",
        f"Pedido: #{pedido_id}",
        f"Codigo de confirmacion: {codigo_confirmacion}",
        f"Nombre completo: {nombre_clean} {apellidos_clean}",
        f"Fecha de nacimiento: {str(fecha_nacimiento or '').strip() or 'No informada'}",
        f"Tratamiento/Género: {str(forma_trato or '').strip() or 'No especificado'}",
        f"Idioma: {str(idioma or '').strip() or 'es'}",
        f"Email del pedido: {email_clean}",
        "",
        "Este archivo corresponde al Mapa del Alma del cliente indicado arriba.",
        "Si detectas algún dato incorrecto, contacta soporte antes de usar el contenido.",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()} UTC",
    ]
    return _build_single_page_pdf(lines)

