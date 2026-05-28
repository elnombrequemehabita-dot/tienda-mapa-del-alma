"""
Servicio de correo para notificar pedidos al administrador y al cliente.

Prioridad de envío:
1. Brevo API si existe BREVO_API_KEY (recomendado en Render).
2. SMTP Gmail solo como fallback local si no existe BREVO_API_KEY.

IMPORTANTE:
- No adjunta PDFs pesados.
- Envía enlaces de descarga.
- Mantiene compatibilidad con order_services.py.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Optional

import requests

from app import db as database
from app.review_token import token_para_pedido

logger = logging.getLogger(__name__)

_DEFAULT_SENDER = "elnombrequemehabita@gmail.com"
_DEFAULT_ADMIN = "tyane9818@gmail.com"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

SUBJECT_CUSTOMER_PAYMENT = "Pago recibido - estamos creando tu Mapa del Alma (pedido #{order_id})"
SUBJECT_CUSTOMER_PDF = "Tu Mapa del Alma esta listo (pedido #{order_id})"


def _email_sender() -> str:
    return (os.environ.get("EMAIL_SENDER") or _DEFAULT_SENDER).strip()


def _admin_email() -> str:
    return (os.environ.get("ADMIN_EMAIL") or _DEFAULT_ADMIN).strip()


def _brevo_api_key() -> str:
    return (os.environ.get("BREVO_API_KEY") or "").strip()


def _usar_brevo() -> bool:
    return bool(_brevo_api_key())


def get_admin_email() -> str:
    return _admin_email()


def get_email_sender() -> str:
    return _email_sender()


def _get(obj: Any, key: str, default: Any = "") -> Any:
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return obj[key]
    except Exception:
        return default


def _codigo_pedido(pedido: Any) -> str:
    return database.codigo_confirmacion_pedido(int(_get(pedido, "id")))


def _codigo_por_order_id(order_id: int) -> str:
    return database.codigo_confirmacion_pedido(int(order_id))


def _nombre_completo(pedido: Any) -> str:
    return f"{_get(pedido, 'nombre')} {_get(pedido, 'apellidos') or ''}".strip()


def _fecha_pedido(pedido: Any) -> str:
    return (
        _get(pedido, "created_at")
        or _get(pedido, "creado_en")
        or _get(pedido, "fecha")
        or ""
    )


def _base_url() -> str:
    return (
        os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("BASE_URL")
        or os.environ.get("RENDER_EXTERNAL_URL")
        or ""
    ).strip().rstrip("/")


def _resena_url(order_id: int) -> str:
    base_url = _base_url()
    # Ruta actual usa token firmado; este fallback se conserva para compatibilidad.
    try:
        secret = os.environ.get("SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY") or ""
        token = token_para_pedido(int(order_id), secret) if secret else str(order_id)
    except Exception:
        token = str(order_id)

    return f"{base_url}/resena/{token}" if base_url else f"/resena/{token}"


def _build_admin_pago_confirmado_body(
    pedido: Any, stripe_checkout_session_id: Optional[str] = None
) -> str:
    lines = [
        "Stripe ha confirmado el pago.",
        "El sistema continuará con la generación del PDF y la entrega al cliente.",
        "",
        f"Pedido interno: #{_get(pedido, 'id')}",
        f"Codigo de confirmacion: {_codigo_pedido(pedido)}",
        f"Nombre: {_nombre_completo(pedido)}",
        f"Email del cliente: {_get(pedido, 'email')}",
        f"Fecha del pedido: {_fecha_pedido(pedido) or '(no disponible)'}",
        f"Estado en BD: {_get(pedido, 'estado')}",
    ]
    if stripe_checkout_session_id:
        lines.extend(["", f"Checkout Session (Stripe): {stripe_checkout_session_id}"])
    return "\n".join(lines) + "\n"


def _build_customer_pago_confirmado_body(pedido: Any) -> str:
    nombre = _get(pedido, "nombre") or "alma bonita"
    codigo = _codigo_pedido(pedido)

    lines = [
        f"Hola {nombre},",
        "",
        "Tu pago fue recibido correctamente ✨",
        "",
        "Ya comenzamos el proceso de creación de tu Mapa del Alma personalizado.",
        "Este no es un archivo automático genérico: se prepara con tus datos para entregarte una lectura cuidada, profunda y diseñada especialmente para ti.",
        "",
        "Próximo paso:",
        "- Cuando tu PDF esté listo, recibirás otro correo con el enlace directo de descarga.",
        "- Revisa también Spam, Promociones o Correo no deseado por si el mensaje llega allí.",
        "- El enlace de descarga estará activo por tiempo limitado según las condiciones de la tienda.",
        "",
        "Resumen de tu pedido:",
        f"- Pedido: {codigo}",
        f"- Nombre: {_nombre_completo(pedido)}",
        f"- Email: {_get(pedido, 'email')}",
        "",
        "Gracias por confiar en El Nombre Que Me Habita 💛",
    ]
    return "\n".join(lines) + "\n"


def _build_customer_pago_confirmado_html(pedido: Any) -> str:
    nombre = _get(pedido, "nombre") or "alma bonita"
    codigo = _codigo_pedido(pedido)
    full_name = _nombre_completo(pedido)

    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;color:#2f2a36;line-height:1.6;">
  <h2 style="margin:0 0 12px;color:#243b7a;">Pago recibido ✨</h2>
  <p style="margin:0 0 14px;">Hola {nombre},</p>
  <p style="margin:0 0 12px;">Tu pago fue recibido correctamente.</p>
  <p style="margin:0 0 12px;">Ya comenzamos el proceso de creación de tu <strong>Mapa del Alma personalizado</strong>.</p>
  <p style="margin:0 0 12px;">Este no es un archivo automático genérico: se prepara con tus datos para entregarte una lectura cuidada, profunda y diseñada especialmente para ti.</p>

  <div style="background:#f5f7ff;border:1px solid #dbe4ff;border-radius:12px;padding:14px 16px;margin:16px 0;">
    <p style="margin:0 0 8px;"><strong>Próximo paso:</strong></p>
    <p style="margin:0 0 6px;">Cuando tu PDF esté listo, recibirás otro correo con el enlace directo de descarga.</p>
    <p style="margin:0;">Revisa también Spam, Promociones o Correo no deseado.</p>
  </div>

  <div style="background:#faf7fd;border:1px solid #e7ddf2;border-radius:10px;padding:12px 14px;margin:0 0 16px;">
    <p style="margin:0 0 6px;"><strong>Pedido:</strong> {codigo}</p>
    <p style="margin:0 0 6px;"><strong>Nombre:</strong> {full_name}</p>
    <p style="margin:0;"><strong>Correo:</strong> {_get(pedido, 'email')}</p>
  </div>

  <p style="margin:0;">Gracias por confiar en <strong>El Nombre Que Me Habita</strong> 💛</p>
</div>
""".strip()


def _build_admin_envio_cliente_body(pedido: Any) -> str:
    pdf_url = (
        _get(pedido, "drive_download_link")
        or _get(pedido, "pdf_url")
        or _get(pedido, "drive_view_link")
        or "(no disponible)"
    )
    return (
        "El email de entrega con enlace de descarga se envió correctamente al cliente.\n\n"
        f"Pedido interno: #{_get(pedido, 'id')}\n"
        f"Codigo de confirmacion: {_codigo_pedido(pedido)}\n"
        f"Cliente: {_nombre_completo(pedido)}\n"
        f"Email cliente: {_get(pedido, 'email')}\n"
        f"URL PDF: {pdf_url}\n"
        f"Estado actual: {_get(pedido, 'estado')}\n"
    )


def _build_admin_pdf_pendiente_link_body(pedido: Any, pdf_path: str) -> str:
    return (
        "El PDF del pedido se generó correctamente, pero no hay proveedor de almacenamiento "
        "activo para crear un enlace de descarga.\n\n"
        f"Pedido interno: #{_get(pedido, 'id')}\n"
        f"Codigo de confirmacion: {_codigo_pedido(pedido)}\n"
        f"Cliente: {_nombre_completo(pedido)}\n"
        f"Email cliente: {_get(pedido, 'email')}\n"
        f"Ruta local del PDF: {pdf_path or '(no disponible)'}\n"
        "Acción requerida: configurar Drive/enlace y reenviar notificaciones.\n"
    )


def _build_admin_impresion_pendiente_body(pedido: Any) -> str:
    dedicatoria = (_get(pedido, "dedicatoria") or "").strip()
    lines = [
        "Nueva orden de libro impreso pendiente de producción.",
        "",
        f"Pedido interno: #{_get(pedido, 'id')}",
        f"Codigo de confirmacion: {_codigo_pedido(pedido)}",
        f"Cliente: {_nombre_completo(pedido)}",
        f"Email cliente: {_get(pedido, 'email')}",
        f"Estado actual: {_get(pedido, 'estado')}",
        f"PDF: {_get(pedido, 'drive_download_link') or _get(pedido, 'pdf_url') or _get(pedido, 'drive_view_link') or '(no disponible)'}",
        f"Es regalo: {'sí' if _get(pedido, 'es_regalo') else 'no'}",
    ]
    if dedicatoria:
        lines.extend(["", "Dedicatoria personalizada:", dedicatoria])
    lines.extend([
        "",
        "Acción requerida: imprimir el PDF, marcar como impreso en admin y registrar tracking cuando se envíe.",
    ])
    return "\n".join(lines) + "\n"


def _build_customer_body(pedido: Any, pdf_url: str, resena_url: str) -> str:
    nombre = _get(pedido, "nombre") or "alma bonita"
    full_name = _nombre_completo(pedido)
    lines = [
        f"Hola {nombre},",
        "",
        "Tu Mapa del Alma ya está listo ✨",
        "",
        "Puedes descargarlo aquí:",
        pdf_url,
        "",
        "Tu experiencia puede ayudar a otras personas a descubrir su propio Mapa del Alma ✨",
        "",
        "Si este libro tocó tu corazón, te hizo reflexionar o te ayudó a conectar contigo misma(o), me haría muy feliz que dejaras tu reseña aquí:",
        resena_url,
        "",
        "Resumen de tu pedido:",
        f"- Pedido: {_codigo_pedido(pedido)}",
        f"- Nombre: {full_name}",
        "",
        "Gracias por confiar en El Nombre Que Me Habita 💛",
    ]
    return "\n".join(lines) + "\n"


def _build_customer_html_body(pedido: Any, pdf_url: str, resena_url: str) -> str:
    nombre = _get(pedido, "nombre") or "alma bonita"
    full_name = _nombre_completo(pedido)
    codigo = _codigo_pedido(pedido)

    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;color:#2f2a36;line-height:1.55;">
  <h2 style="margin:0 0 12px;color:#243b7a;">Tu Mapa del Alma está listo ✨</h2>
  <p style="margin:0 0 14px;">Hola {nombre},</p>
  <p style="margin:0 0 12px;">Puedes descargarlo aquí:</p>
  <p style="margin:0 0 16px;"><a href="{pdf_url}">{pdf_url}</a></p>
  <p style="margin:0 0 12px;">Tu experiencia puede ayudar a otras personas a descubrir su propio Mapa del Alma ✨</p>
  <p style="margin:0 0 12px;">Si este libro tocó tu corazón, te hizo reflexionar o te ayudó a conectar contigo misma(o), me haría muy feliz que dejaras tu reseña aquí:</p>
  <p style="margin:0 0 16px;"><a href="{resena_url}">{resena_url}</a></p>
  <div style="background:#faf7fd;border:1px solid #e7ddf2;border-radius:10px;padding:12px 14px;margin:0 0 16px;">
    <p style="margin:0 0 6px;"><strong>Pedido:</strong> {codigo}</p>
    <p style="margin:0 0 6px;"><strong>Nombre:</strong> {full_name}</p>
    <p style="margin:0;"><strong>Correo:</strong> {_get(pedido, 'email')}</p>
  </div>
  <p style="margin:0;">Gracias por confiar en <strong>El Nombre Que Me Habita</strong> 💛</p>
</div>
""".strip()


def _build_customer_shipping_body(pedido: Any) -> str:
    nombre = _get(pedido, "nombre") or "alma bonita"
    carrier = _get(pedido, "shipping_carrier") or "Transportista"
    tracking = _get(pedido, "tracking_number") or "(no disponible)"
    lines = [
        f"Hola {nombre},",
        "",
        "Tu libro ha sido enviado.",
        "",
        f"Transportista: {carrier}",
        "",
        "Número de seguimiento:",
        str(tracking),
        "",
        "Puedes rastrear tu pedido con ese número en la web oficial del transportista.",
        "",
        "Tu PDF digital ya fue entregado por correo; este aviso corresponde al envío físico de tu libro personalizado.",
        "",
        "Gracias por confiar en Mapa del Alma.",
    ]
    return "\n".join(lines) + "\n"


def _build_customer_shipping_html(pedido: Any) -> str:
    nombre = _get(pedido, "nombre") or "alma bonita"
    carrier = _get(pedido, "shipping_carrier") or "Transportista"
    tracking = _get(pedido, "tracking_number") or "(no disponible)"
    codigo = _codigo_pedido(pedido)
    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;color:#2f2a36;line-height:1.55;">
  <h2 style="margin:0 0 12px;color:#243b7a;">Tu libro ha sido enviado</h2>
  <p style="margin:0 0 14px;">Hola {nombre},</p>
  <p style="margin:0 0 12px;">Tu libro impreso de <strong>Mapa del Alma</strong> ya está en camino.</p>
  <div style="background:#faf7fd;border:1px solid #e7ddf2;border-radius:10px;padding:12px 14px;margin:0 0 16px;">
    <p style="margin:0 0 6px;"><strong>Pedido:</strong> {codigo}</p>
    <p style="margin:0 0 6px;"><strong>Transportista:</strong> {carrier}</p>
    <p style="margin:0;"><strong>Número de seguimiento:</strong> {tracking}</p>
  </div>
  <p style="margin:0 0 12px;">Puedes rastrear tu pedido con ese número en la web oficial del transportista.</p>
  <p style="margin:0;">Gracias por confiar en <strong>Mapa del Alma</strong>.</p>
</div>
""".strip()


def _es_error_openai_credito_texto(texto: str) -> bool:
    lower = (texto or "").lower()
    claves = (
        "insufficient_quota",
        "quota",
        "billing_hard_limit",
        "billing hard limit",
        "exceeded your current quota",
        "you exceeded your current quota",
        "check your plan and billing",
        "credit",
        "credits",
        "saldo",
        "sin saldo",
        "límite de facturación",
        "limite de facturacion",
        "billing",
        "rate limit reached for",
    )
    return any(c in lower for c in claves)


def _build_admin_error_body(order_id: int, stage: str, error_message: str, pedido: Optional[Any] = None) -> str:
    error_text = (error_message or "").strip()
    stage_text = stage or "post_pago"

    if stage_text == "openai_credito" or _es_error_openai_credito_texto(error_text):
        titulo = "OpenAI no pudo generar el contenido por saldo/cuota/limite de facturacion."
        acciones = [
            "Entrar al panel de OpenAI y revisar Billing / Usage.",
            "Recargar saldo o aumentar el limite de presupuesto si aplica.",
            "Cuando el saldo esté activo otra vez, volver al pedido en admin.",
            "Pulsar 'Marcar como pagado' para reintentar el flujo sin cobrar de nuevo.",
            "No crear otro pedido y no pedirle al cliente que pague otra vez.",
        ]
    elif stage_text == "envio_email":
        titulo = "El pedido se cobró, pero falló el envío del email al cliente."
        acciones = [
            "Revisar Brevo API key, sender verificado y Authorized IPs.",
            "Confirmar que el pedido tenga enlace PDF.",
            "Usar 'Reenviar email al cliente' desde el panel admin cuando esté corregido.",
        ]
    elif "pdf" in stage_text:
        titulo = "El pedido se cobró, pero falló la generación del PDF."
        acciones = [
            "Usar 'Reintentar PDF usando JSON existente'.",
            "No regenerar contenido completo si ya existe JSON válido.",
            "Si el JSON está roto, usar primero 'Reparar JSON'.",
        ]
    elif "json" in stage_text:
        titulo = "El pedido se cobró, pero el JSON necesita reparación o secciones faltantes."
        acciones = [
            "Usar 'Reparar JSON' para intentar reparación local primero.",
            "Si faltan secciones, usar 'Completar secciones faltantes'.",
            "No usar 'Regenerar contenido completo con OpenAI' salvo que no haya JSON usable.",
        ]
    elif "drive" in stage_text:
        titulo = "El pedido se cobró y el PDF puede existir, pero falló Google Drive."
        acciones = [
            "Revisar credenciales/permisos de Google Drive.",
            "Usar 'Reintentar PDF usando JSON existente' para subir sin gastar OpenAI.",
            "No regenerar contenido.",
        ]
    else:
        titulo = "Se produjo un error en el flujo post-pago del pedido."
        acciones = [
            "Revisar logs de Render para ver el traceback completo.",
            "Revisar el pedido en el panel admin.",
            "Si el error fue PDF/Drive/email, usar el botón específico para no gastar OpenAI.",
        ]

    parts = [
        titulo,
        "",
        f"Pedido interno: #{order_id}",
        f"Codigo de confirmacion: {_codigo_por_order_id(order_id)}",
        f"Etapa: {stage_text}",
        f"Error tecnico: {error_text or '(sin detalle)'}",
        "",
        "Acciones sugeridas:",
    ]
    parts.extend([f"- {a}" for a in acciones])

    if pedido is not None:
        parts.extend(
            [
                "",
                f"Cliente: {_nombre_completo(pedido)}",
                f"Email cliente: {_get(pedido, 'email')}",
                f"Estado actual: {_get(pedido, 'estado')}",
                f"Llamadas OpenAI: {_get(pedido, 'openai_call_count', 0)}",
                f"Costo estimado OpenAI USD: {_get(pedido, 'openai_estimated_cost_usd', 0)}",
                f"json_path: {_get(pedido, 'json_path') or '(no disponible)'}",
                f"raw_openai_path: {_get(pedido, 'raw_openai_path') or '(no disponible)'}",
                f"generation_status: {_get(pedido, 'generation_status') or '(no disponible)'}",
            ]
        )
    return "\n".join(parts) + "\n"


def _send_message(msg: EmailMessage) -> None:
    """
    Envía usando Brevo API si BREVO_API_KEY existe.
    Fallback SMTP Gmail solo si no existe BREVO_API_KEY.
    """
    if _usar_brevo():
        plain = msg.get_body(preferencelist=("plain",))
        html = msg.get_body(preferencelist=("html",))

        payload: dict[str, Any] = {
            "sender": {
                "name": "El Nombre Que Me Habita",
                "email": _email_sender(),
            },
            "to": [{"email": str(msg["To"]).strip()}],
            "subject": str(msg["Subject"]),
            "textContent": plain.get_content() if plain is not None else "",
        }

        if html is not None:
            payload["htmlContent"] = html.get_content()

        response = requests.post(
            BREVO_API_URL,
            headers={
                "accept": "application/json",
                "api-key": _brevo_api_key(),
                "content-type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        if response.status_code >= 400:
            raise RuntimeError(f"Brevo API error {response.status_code}: {response.text}")

        return

    email_password = (os.environ.get("EMAIL_PASSWORD") or "").strip()
    if not email_password:
        raise ValueError("No existe BREVO_API_KEY y EMAIL_PASSWORD tampoco está configurado.")

    sender = _email_sender()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(sender, email_password)
        smtp.send_message(msg)


def notify_customer_pago_confirmado(pedido: Any) -> bool:
    """
    Primer email al cliente: pago recibido y próximos pasos.
    No lanza excepción para no bloquear el PDF.
    """
    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"{SUBJECT_CUSTOMER_PAYMENT.format(order_id=_get(pedido, 'id'))} [{codigo}]"
        msg["From"] = _email_sender()
        msg["To"] = _get(pedido, "email")
        msg.set_content(_build_customer_pago_confirmado_body(pedido), charset="utf-8")
        msg.add_alternative(_build_customer_pago_confirmado_html(pedido), subtype="html")
        _send_message(msg)
        logger.info("Email cliente (pago confirmado) enviado, pedido #%s", _get(pedido, "id"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo enviar email cliente (pago confirmado): %s", exc, exc_info=False)
        return False


def notify_admin_pago_confirmado(
    pedido: Any, stripe_checkout_session_id: Optional[str] = None
) -> bool:
    """
    Aviso al administrador cuando el pago quedó confirmado.
    No lanza excepciones.
    """
    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"Pago confirmado - Pedido #{_get(pedido, 'id')} [{codigo}] - Mapa del Alma"
        msg["From"] = _email_sender()
        msg["To"] = _admin_email()
        msg.set_content(_build_admin_pago_confirmado_body(pedido, stripe_checkout_session_id), charset="utf-8")
        _send_message(msg)
        logger.info("Aviso admin (pago confirmado) enviado, pedido #%s", _get(pedido, "id"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo enviar email al admin (pago confirmado): %s", exc, exc_info=False)
        return False


def notify_admin_envio_cliente_ok(pedido: Any) -> bool:
    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"Pedido enviado al cliente - Pedido #{_get(pedido, 'id')} [{codigo}] - Mapa del Alma"
        msg["From"] = _email_sender()
        msg["To"] = _admin_email()
        msg.set_content(_build_admin_envio_cliente_body(pedido), charset="utf-8")
        _send_message(msg)
        logger.info("Aviso admin (pedido enviado al cliente) enviado, pedido #%s", _get(pedido, "id"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo enviar email al admin (pedido enviado): %s", exc, exc_info=False)
        return False


def notify_admin_pdf_generado_sin_link(pedido: Any, pdf_path: str) -> bool:
    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"PDF generado sin enlace - Pedido #{_get(pedido, 'id')} [{codigo}] - Mapa del Alma"
        msg["From"] = _email_sender()
        msg["To"] = _admin_email()
        msg.set_content(_build_admin_pdf_pendiente_link_body(pedido, pdf_path), charset="utf-8")
        _send_message(msg)
        logger.info("Aviso admin (PDF generado sin enlace) enviado, pedido #%s", _get(pedido, "id"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo enviar aviso admin (PDF sin enlace): %s", exc, exc_info=False)
        return False


def notify_admin_impresion_pendiente(pedido: Any) -> bool:
    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"Libro impreso pendiente - Pedido #{_get(pedido, 'id')} [{codigo}] - Mapa del Alma"
        msg["From"] = _email_sender()
        msg["To"] = _admin_email()
        msg.set_content(_build_admin_impresion_pendiente_body(pedido), charset="utf-8")
        _send_message(msg)
        logger.info("Aviso admin (impresión pendiente) enviado, pedido #%s", _get(pedido, "id"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo enviar aviso admin (impresión pendiente): %s", exc, exc_info=False)
        return False


def send_customer_pdf_email(pedido: Any, *, pdf_url: str, resena_url: str) -> None:
    pdf_url = str(pdf_url or "").strip()
    resena_url = str(resena_url or "").strip()
    if not pdf_url:
        raise ValueError("No se puede enviar email al cliente sin pdf_url.")
    if not resena_url:
        raise ValueError("No se puede enviar email al cliente sin enlace de reseña.")

    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"{SUBJECT_CUSTOMER_PDF.format(order_id=_get(pedido, 'id'))} [{codigo}]"
        msg["From"] = _email_sender()
        msg["To"] = _get(pedido, "email")
        msg.set_content(_build_customer_body(pedido, pdf_url=pdf_url, resena_url=resena_url), charset="utf-8")
        msg.add_alternative(_build_customer_html_body(pedido, pdf_url=pdf_url, resena_url=resena_url), subtype="html")
        _send_message(msg)
        logger.info("Email de entrega enviado al cliente, pedido #%s", _get(pedido, "id"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo envío email de entrega al cliente (pedido #%s): %s", _get(pedido, "id"), exc)
        raise


def send_customer_shipping_email(pedido: Any) -> None:
    tracking = str(_get(pedido, "tracking_number") or "").strip()
    carrier = str(_get(pedido, "shipping_carrier") or "").strip()
    if not tracking:
        raise ValueError("No se puede enviar tracking sin número de seguimiento.")
    if not carrier:
        raise ValueError("No se puede enviar tracking sin transportista.")

    try:
        msg = EmailMessage()
        codigo = _codigo_pedido(pedido)
        msg["Subject"] = f"Tu libro ha sido enviado - Pedido #{_get(pedido, 'id')} [{codigo}]"
        msg["From"] = _email_sender()
        msg["To"] = _get(pedido, "email")
        msg.set_content(_build_customer_shipping_body(pedido), charset="utf-8")
        msg.add_alternative(_build_customer_shipping_html(pedido), subtype="html")
        _send_message(msg)
        logger.info("Email de tracking enviado al cliente, pedido #%s", _get(pedido, "id"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo envío email tracking cliente (pedido #%s): %s", _get(pedido, "id"), exc)
        raise


def notify_admin_error(order_id: int, stage: str, error_message: str, pedido: Optional[Any] = None) -> bool:
    try:
        msg = EmailMessage()
        codigo = _codigo_por_order_id(order_id)
        error_lower = (error_message or "").lower()
        if stage == "openai_credito" or _es_error_openai_credito_texto(error_lower):
            msg["Subject"] = f"URGENTE: recargar OpenAI - Pedido #{order_id} [{codigo}]"
        elif stage == "generacion_pdf":
            msg["Subject"] = f"URGENTE: pago cobrado pero PDF no generado - Pedido #{order_id} [{codigo}]"
        elif stage == "envio_email":
            msg["Subject"] = f"URGENTE: pago cobrado pero email no enviado - Pedido #{order_id} [{codigo}]"
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


# =========================================================
# COMPATIBILIDAD CON order_services.py
# =========================================================

def enviar_email_pedido_completado(pedido: Any, pdf_url: str) -> bool:
    pdf_url = str(pdf_url or "").strip()
    if not pdf_url:
        raise ValueError("No se puede enviar email de pedido completado sin pdf_url.")

    try:
        order_id = int(_get(pedido, "id"))
    except Exception:
        order_id = int(pedido.get("id"))

    send_customer_pdf_email(
        pedido,
        pdf_url=pdf_url,
        resena_url=_resena_url(order_id),
    )

    try:
        notify_admin_envio_cliente_ok(pedido)
    except Exception:
        logger.exception("No se pudo notificar al admin que el cliente recibió el email.")

    return True


def enviar_email_admin_error(order_id: int, error_message: str, stage: str = "generacion_pdf", pedido: Optional[Any] = None) -> bool:
    return notify_admin_error(
        int(order_id),
        stage,
        str(error_message),
        pedido=pedido,
    )
