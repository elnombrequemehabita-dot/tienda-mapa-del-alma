"""
Servicio de correo para notificar nuevos pedidos al administrador.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Optional

from app import db as database

logger = logging.getLogger(__name__)

# Valores por defecto; puedes sobreescribir con EMAIL_SENDER / ADMIN_EMAIL en `.env`
_DEFAULT_SENDER = "elnombrequemehabita@gmail.com"
_DEFAULT_ADMIN = "tyane9818@gmail.com"


def _email_sender() -> str:
    return (os.environ.get("EMAIL_SENDER") or _DEFAULT_SENDER).strip()


def _admin_email() -> str:
    return (os.environ.get("ADMIN_EMAIL") or _DEFAULT_ADMIN).strip()


def get_admin_email() -> str:
    """Email admin efectivo (config o fallback)."""
    return _admin_email()


def get_email_sender() -> str:
    """Email remitente efectivo (config o fallback)."""
    return _email_sender()


SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SUBJECT_CUSTOMER_PDF = "Tu Mapa del Alma esta listo (pedido #{order_id})"


def _codigo_pedido(pedido: Any) -> str:
    return database.codigo_confirmacion_pedido(int(pedido["id"]))


def _codigo_por_order_id(order_id: int) -> str:
    return database.codigo_confirmacion_pedido(int(order_id))


def _build_admin_pago_confirmado_body(
    pedido: Any, stripe_checkout_session_id: Optional[str] = None
) -> str:
    """Cuerpo del aviso al admin cuando Stripe confirma el cobro."""
    lines = [
        "Stripe ha confirmado el pago. El sistema generará el PDF y lo enviará al cliente automáticamente.",
        "",
        f"Pedido: #{pedido['id']}",
        f"Codigo de confirmacion: {_codigo_pedido(pedido)}",
        f"Nombre: {pedido['nombre']} {pedido['apellidos'] or ''}".strip(),
        f"Email del cliente: {pedido['email']}",
        f"Fecha del pedido: {pedido['created_at']}",
        f"Estado en BD (tras marcar pagado): {pedido['estado']}",
    ]
    if stripe_checkout_session_id:
        lines.extend(["", f"Checkout Session (Stripe): {stripe_checkout_session_id}"])
    return "\n".join(lines) + "\n"


def _build_admin_envio_cliente_body(pedido: Any) -> str:
    return (
        "El email de entrega con enlace de descarga se envio correctamente al cliente.\n\n"
        f"Pedido: #{pedido['id']}\n"
        f"Codigo de confirmacion: {_codigo_pedido(pedido)}\n"
        f"Cliente: {pedido['nombre']} {pedido['apellidos'] or ''}\n"
        f"Email cliente: {pedido['email']}\n"
        f"URL PDF: {pedido['pdf_url'] or '(no disponible)'}\n"
        f"Estado actual: {pedido['estado']}\n"
    )


def _build_customer_body(pedido: Any, pdf_url: str, resena_url: str) -> str:
    full_name = f"{pedido['nombre']} {pedido['apellidos'] or ''}".strip()
    lines = [
        f"Hola {pedido['nombre']},",
        "",
        "Tu Mapa del Alma ya esta listo ✨",
        "",
        "Puedes descargarlo aqui:",
        pdf_url,
        "",
        "Cuando lo hayas leido, si quieres, tambien puedes dejar tu comentario y calificacion aqui:",
        resena_url,
        "",
        "Resumen de tu pedido:",
        f"- Pedido: #{pedido['id']}",
        f"- Codigo de confirmacion: {_codigo_pedido(pedido)}",
        f"- Nombre: {full_name}",
        "",
        "Gracias por confiar en El Nombre Que Me Habita 💛",
    ]
    return "\n".join(lines) + "\n"


def _build_customer_html_body(pedido: Any, pdf_url: str, resena_url: str) -> str:
    full_name = f"{pedido['nombre']} {pedido['apellidos'] or ''}".strip()
    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;color:#2f2a36;line-height:1.55;">
  <h2 style="margin:0 0 12px;color:#4b2f5f;">Tu Mapa del Alma esta listo ✨</h2>
  <p style="margin:0 0 14px;">Hola {pedido['nombre']},</p>
  <p style="margin:0 0 12px;">Puedes descargarlo aqui:</p>
  <p style="margin:0 0 16px;"><a href="{pdf_url}">{pdf_url}</a></p>
  <p style="margin:0 0 12px;">Cuando lo hayas leido, si quieres, tambien puedes dejar tu comentario y calificacion aqui:</p>
  <p style="margin:0 0 16px;"><a href="{resena_url}">{resena_url}</a></p>
  <div style="background:#faf7fd;border:1px solid #e7ddf2;border-radius:10px;padding:12px 14px;margin:0 0 16px;">
    <p style="margin:0 0 6px;"><strong>Pedido:</strong> #{pedido['id']}</p>
    <p style="margin:0 0 6px;"><strong>Codigo de confirmacion:</strong> {_codigo_pedido(pedido)}</p>
    <p style="margin:0 0 6px;"><strong>Nombre:</strong> {full_name}</p>
    <p style="margin:0;"><strong>Correo:</strong> {pedido['email']}</p>
  </div>
  <p style="margin:0;">Gracias por confiar en <strong>El Nombre Que Me Habita</strong> 💛</p>
</div>
""".strip()


def _build_admin_error_body(order_id: int, stage: str, error_message: str, pedido: Optional[Any] = None) -> str:
    error_text = (error_message or "").strip()
    lower = error_text.lower()

    causa = "Fallo no clasificado."
    acciones = [
        "Revisar logs de la aplicación para ver el traceback completo.",
        "Reintentar el flujo desde el panel admin cuando el problema esté corregido.",
    ]

    if stage == "generacion_pdf":
        if "estado=" in lower and "se requiere pagado" in lower:
            causa = "Se intentó generar PDF sin que el pedido estuviera en estado pagado."
            acciones = [
                "Confirmar en Stripe que el cobro figure como paid.",
                "Verificar que el webhook checkout.session.completed esté llegando y firmado correctamente.",
                "Asegurar que el pedido pase a estado 'pagado' antes de generar PDF.",
            ]
        elif "no existe el pedido" in lower:
            causa = "El pedido no existe o fue eliminado antes de generar el PDF."
            acciones = [
                "Comprobar si el pedido fue eliminado en admin.",
                "Validar que metadata.pedido_id de Stripe corresponda a un pedido real.",
            ]
        elif "permission" in lower or "acceso denegado" in lower:
            causa = "No hay permisos de escritura en la carpeta de salida del PDF."
            acciones = [
                "Dar permisos de escritura a la carpeta output del proyecto.",
                "Verificar que la ruta del proyecto exista y sea accesible por el proceso.",
            ]
        elif "disk" in lower or "espacio" in lower or "no space" in lower:
            causa = "No hay espacio suficiente en disco para escribir el PDF."
            acciones = [
                "Liberar espacio en disco.",
                "Reintentar la generación desde admin cuando haya espacio disponible.",
            ]
        else:
            causa = "Error durante la generación o guardado del PDF."
            acciones = [
                "Verificar permisos y existencia de la carpeta output.",
                "Revisar el contenido de datos del pedido y reintentar.",
                "Consultar logs para el traceback completo de generación.",
            ]
    elif stage == "envio_email":
        if "email_password no configurado" in lower:
            causa = "No está configurada la contraseña de aplicación para SMTP."
            acciones = [
                "Configurar EMAIL_PASSWORD en .env con la app password de Gmail.",
                "Reiniciar la aplicación para recargar variables de entorno.",
            ]
        elif "authentication" in lower or "535" in lower:
            causa = "SMTP rechazó autenticación del remitente."
            acciones = [
                "Verificar EMAIL_SENDER y EMAIL_PASSWORD.",
                "Comprobar que la cuenta tenga habilitada contraseña de aplicación.",
            ]
        elif "timed out" in lower or "timeout" in lower:
            causa = "Tiempo de espera agotado al conectar al servidor SMTP."
            acciones = [
                "Revisar conexión de red y acceso a smtp.gmail.com:587.",
                "Reintentar envío cuando haya conectividad estable.",
            ]
        else:
            causa = "Error al enviar el email al cliente con enlaces de entrega."
            acciones = [
                "Revisar credenciales SMTP y conectividad de red.",
                "Confirmar que el pedido tenga pdf_url generado en Cloudinary.",
                "Reintentar envío desde admin.",
            ]

    parts = [
        "Se produjo un error en el flujo post-pago del pedido.",
        "",
        f"Pedido: #{order_id}",
        f"Codigo de confirmacion: {_codigo_por_order_id(order_id)}",
        f"Etapa: {stage}",
        f"Causa detectada: {causa}",
        f"Error tecnico: {error_text or '(sin detalle)'}",
        "",
        "Como solucionarlo:",
    ]
    parts.extend([f"- {a}" for a in acciones])
    if pedido is not None:
        parts.extend(
            [
                "",
                f"Cliente: {pedido['nombre']} {pedido['apellidos'] or ''}".strip(),
                f"Email cliente: {pedido['email']}",
                f"Estado actual: {pedido['estado']}",
            ]
        )
    return "\n".join(parts) + "\n"


def _send_message(msg: EmailMessage) -> None:
    email_password = (os.environ.get("EMAIL_PASSWORD") or "").strip()
    if not email_password:
        raise ValueError(
            "EMAIL_PASSWORD no configurado en .env (contraseña de aplicación Gmail del remitente)."
        )
    sender = _email_sender()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(sender, email_password)
        smtp.send_message(msg)


def notify_admin_pago_confirmado(
    pedido: Any, stripe_checkout_session_id: Optional[str] = None
) -> bool:
    """
    Aviso al administrador cuando el pago quedó confirmado (webhook Stripe).

    No lanza excepciones: si falla el SMTP solo se registra en consola.
    """
    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"Pago confirmado - Pedido #{pedido['id']} [{codigo}] - Mapa del Alma"
        msg["From"] = _email_sender()
        msg["To"] = _admin_email()
        msg.set_content(
            _build_admin_pago_confirmado_body(pedido, stripe_checkout_session_id),
            charset="utf-8",
        )
        _send_message(msg)
        logger.info("Aviso admin (pago confirmado) enviado, pedido #%s", pedido["id"])
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo enviar email al admin (pago confirmado): %s", exc, exc_info=False)
        return False


def notify_admin_envio_cliente_ok(pedido: Any) -> bool:
    """
    Segundo aviso al admin: confirma que el PDF ya fue entregado al cliente.
    """
    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"Pedido enviado al cliente - Pedido #{pedido['id']} [{codigo}] - Mapa del Alma"
        msg["From"] = _email_sender()
        msg["To"] = _admin_email()
        msg.set_content(_build_admin_envio_cliente_body(pedido), charset="utf-8")
        _send_message(msg)
        logger.info("Aviso admin (pedido enviado al cliente) enviado, pedido #%s", pedido["id"])
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo enviar email al admin (pedido enviado): %s", exc, exc_info=False)
        return False


def send_customer_pdf_email(pedido: Any, *, pdf_url: str, resena_url: str) -> None:
    """
    Envía al cliente enlaces de descarga y reseña tras pago confirmado.
    """
    pdf_url = str(pdf_url or "").strip()
    resena_url = str(resena_url or "").strip()
    if not pdf_url:
        raise ValueError("No se puede enviar email al cliente sin pdf_url.")
    if not resena_url:
        raise ValueError("No se puede enviar email al cliente sin enlace de reseña.")

    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"{SUBJECT_CUSTOMER_PDF.format(order_id=pedido['id'])} [{codigo}]"
        msg["From"] = _email_sender()
        msg["To"] = pedido["email"]
        msg.set_content(_build_customer_body(pedido, pdf_url=pdf_url, resena_url=resena_url), charset="utf-8")
        msg.add_alternative(
            _build_customer_html_body(pedido, pdf_url=pdf_url, resena_url=resena_url),
            subtype="html",
        )
        _send_message(msg)
        logger.info("Email de entrega enviado al cliente, pedido #%s", pedido["id"])
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo envío email de entrega al cliente (pedido #%s): %s", pedido["id"], exc)
        raise


def notify_admin_error(order_id: int, stage: str, error_message: str, pedido: Optional[Any] = None) -> bool:
    """
    Notificación al admin por fallo en generación de PDF o envío al cliente (post-pago).

    No lanza excepciones si falla el envío SMTP.
    Devuelve True si pudo enviar, False si no.
    """
    try:
        msg = EmailMessage()
        codigo = _codigo_por_order_id(order_id)
        if stage == "generacion_pdf":
            msg["Subject"] = f"URGENTE: pago cobrado pero PDF no generado - Pedido #{order_id} [{codigo}]"
        else:
            msg["Subject"] = f"Error en pedido #{order_id} [{codigo}] - Mapa del Alma"
        msg["From"] = _email_sender()
        msg["To"] = _admin_email()
        msg.set_content(_build_admin_error_body(order_id, stage, error_message, pedido), charset="utf-8")
        _send_message(msg)
        logger.info("Aviso admin (error post-pago) enviado, pedido #%s", order_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo enviar email al admin (error pedido): %s", exc)
        return False
