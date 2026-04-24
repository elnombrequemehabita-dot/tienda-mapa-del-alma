"""
Servicios del flujo automático de pedidos:
pago confirmado -> generación de PDF -> subida a Cloudinary -> envío al cliente -> notificaciones.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from flask import current_app, url_for

from app import cloudinary_storage
from app import db as database
from app import email_service
from app import pdf_generator
from app.order_states import (
    ESTADO_COMPLETADO,
    ESTADO_ENVIANDO_EMAIL,
    ESTADO_ERROR_ENVIO,
    ESTADO_ERROR_GENERACION,
    ESTADO_GENERANDO_PDF,
    ESTADO_PAGADO,
    ESTADO_PDF_GENERADO,
    ESTADO_PENDIENTE_PAGO,
    ESTADO_REVISION_MANUAL,
)
from app.review_token import token_para_pedido

logger = logging.getLogger(__name__)
_ATASCO_MARKER = "[AUTO_TIMEOUT_20M]"
_ATASCO_STATES = (
    ESTADO_PENDIENTE_PAGO,
    ESTADO_PAGADO,
    ESTADO_GENERANDO_PDF,
    ESTADO_PDF_GENERADO,
    ESTADO_ENVIANDO_EMAIL,
)


def _log_notif(
    *,
    pedido_id: int,
    tipo: str,
    canal: str,
    destinatario: str,
    ok: bool,
    error_message: str = "",
) -> None:
    database.insert_notificacion(
        pedido_id=pedido_id,
        tipo=tipo,
        canal=canal,
        destinatario=destinatario,
        estado="enviado" if ok else "error",
        error_message=(error_message or None),
    )


def _parse_iso_dt(value: str) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    # fromisoformat no acepta 'Z' puro en algunas versiones
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def detectar_pedidos_atascados(timeout_minutes: int = 20) -> int:
    """
    Detecta pedidos no finalizados atascados más de `timeout_minutes`,
    los pasa a `revision_manual` y avisa al admin una sola vez.
    """
    now = datetime.now(timezone.utc)
    umbral = now - timedelta(minutes=timeout_minutes)
    rows = database.list_pedidos_por_estados(_ATASCO_STATES, limit=500)
    marcados = 0

    for row in rows:
        ts = _parse_iso_dt(str(row["updated_at"] or row["created_at"] or ""))
        if ts is None or ts > umbral:
            continue

        existente = str(row["error_message"] or "")
        if _ATASCO_MARKER in existente:
            continue

        order_id = int(row["id"])
        msg = (
            f"{_ATASCO_MARKER} Pedido sin completar en más de {timeout_minutes} minutos. "
            f"Estado actual: {row['estado']}. Ultima actualización (UTC): {row['updated_at'] or row['created_at']}."
        )
        database.update_pedido_campos(
            order_id,
            estado=ESTADO_REVISION_MANUAL,
            error_message=msg,
        )
        ok = email_service.notify_admin_error(
            order_id,
            "timeout_flujo",
            msg,
            database.get_pedido_by_id(order_id),
        )
        _log_notif(
            pedido_id=order_id,
            tipo="admin_timeout_flujo",
            canal="email",
            destinatario=email_service.get_admin_email(),
            ok=ok,
            error_message=msg,
        )
        marcados += 1

    return marcados


def _pdf_output_paths(order_id: int) -> tuple[str, str]:
    """
    Devuelve (ruta_relativa, ruta_absoluta) en carpeta output del proyecto.
    """
    project_root = os.path.dirname(current_app.root_path)
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mapa_alma_{order_id}.pdf"
    absolute = os.path.join(output_dir, filename)
    relative = f"output/{filename}"
    return relative, absolute


def generar_pdf_automatico(order_id: int) -> str:
    """
    Genera el PDF real personalizado del pedido, lo sube a Cloudinary y devuelve su URL segura.
    """
    pedido = database.get_pedido_by_id(order_id)
    if pedido is None:
        raise ValueError(f"No existe el pedido #{order_id}")
    if pedido["estado"] != ESTADO_PAGADO:
        raise RuntimeError(
            f"No se puede generar PDF para pedido #{order_id} porque estado={pedido['estado']} (se requiere pagado)."
        )

    logger.info("GENERANDO PDF REAL PARA PEDIDO #%s...", order_id)
    database.update_pedido_campos(order_id, estado=ESTADO_GENERANDO_PDF, clear_error=True)
    relative, absolute = _pdf_output_paths(order_id)
    nombre = str(pedido["nombre"] or "").strip()
    apellidos = str(pedido["apellidos"] or "").strip()
    fecha_nacimiento = str(pedido["fecha_nacimiento"] or "").strip()
    forma_trato = str(pedido["forma_trato"] or "").strip()
    idioma = str(pedido["idioma"] or "").strip() if "idioma" in pedido.keys() else "es"
    email = str(pedido["email"] or "").strip()

    pdf_bytes = pdf_generator.generate_real_mapa_pdf(
        pedido_id=int(pedido["id"]),
        codigo_confirmacion=database.codigo_confirmacion_pedido(int(pedido["id"])),
        nombre=nombre,
        apellidos=apellidos,
        fecha_nacimiento=fecha_nacimiento,
        forma_trato=forma_trato,
        email=email,
        idioma=idioma,
    )
    with open(absolute, "wb") as f:
        f.write(pdf_bytes)
    logger.info("PDF REAL GENERADO EN: %s", absolute)

    database.update_pedido_campos(order_id, pdf_path=relative, clear_error=True)
    logger.info("PDF_PATH REAL = %s", relative)
    logger.info("SUBIENDO PDF REAL A CLOUDINARY...")
    pdf_url = cloudinary_storage.upload_pdf(order_id, absolute)
    logger.info("PDF_URL REAL = %s", pdf_url)
    database.update_pedido_campos(
        order_id,
        estado=ESTADO_PDF_GENERADO,
        pdf_url=pdf_url,
        clear_error=True,
    )
    return pdf_url


def _build_resena_url(order_id: int) -> str:
    tok = token_para_pedido(order_id, current_app.secret_key)
    return url_for("main.dejar_resena", token=tok, _external=True)


def enviar_pdf_cliente(order_id: int, pdf_url: str) -> None:
    """
    Envía por email un enlace de descarga y marca pedido completado.
    """
    pedido = database.get_pedido_by_id(order_id)
    if pedido is None:
        raise ValueError(f"No existe el pedido #{order_id}")
    database.update_pedido_campos(order_id, estado=ESTADO_ENVIANDO_EMAIL, clear_error=True)
    pedido = database.get_pedido_by_id(order_id)
    if pedido is None:
        raise ValueError(f"No existe el pedido #{order_id}")
    pdf_path_db = str(pedido["pdf_path"] or "").strip()
    pdf_url_db = str(pedido["pdf_url"] or "").strip()
    if not pdf_path_db:
        raise RuntimeError(f"Pedido #{order_id} sin pdf_path en base de datos.")
    if not pdf_url_db:
        raise RuntimeError(f"Pedido #{order_id} sin pdf_url en base de datos.")
    expected_path = f"output/mapa_alma_{int(order_id)}.pdf"
    if pdf_path_db != expected_path:
        raise RuntimeError(
            f"Pedido #{order_id} con pdf_path inesperado: {pdf_path_db} (esperado: {expected_path})"
        )
    if pdf_url and str(pdf_url).strip() != pdf_url_db:
        logger.warning(
            "pdf_url en memoria difiere de BD para pedido #%s; se usará valor persistido.",
            order_id,
        )
    if not pdf_url_db.startswith("https://res.cloudinary.com/"):
        raise RuntimeError(f"pdf_url inválida para pedido #{order_id}: {pdf_url_db}")
    logger.info("PDF_PATH REAL = %s", pdf_path_db)
    logger.info("PDF_URL REAL = %s", pdf_url_db)
    logger.info("ENVIANDO PDF REAL...")
    resena_url = _build_resena_url(order_id)
    email_service.send_customer_pdf_email(pedido, pdf_url=pdf_url_db, resena_url=resena_url)
    logger.info("PDF REAL ENVIADO POR LINK...")
    _log_notif(
        pedido_id=order_id,
        tipo="cliente_link_descarga_enviado",
        canal="email",
        destinatario=str(pedido["email"]),
        ok=True,
    )
    database.update_pedido_campos(order_id, estado=ESTADO_COMPLETADO, clear_error=True)
    pedido_final = database.get_pedido_by_id(order_id)
    if pedido_final is not None:
        ok_admin = email_service.notify_admin_envio_cliente_ok(pedido_final)
        _log_notif(
            pedido_id=order_id,
            tipo="admin_pedido_enviado_cliente",
            canal="email",
            destinatario=email_service.get_admin_email(),
            ok=ok_admin,
        )


def procesar_post_pago(
    order_id: int, *, stripe_checkout_session_id: str | None = None
) -> None:
    """
    Flujo automático post-pago (invocado desde el webhook Stripe):
    pagado -> notificar admin -> generar_pdf -> enviar_email -> completado.
    Si falla PDF o email al cliente, deja estado de error y notifica al admin del fallo.
    """
    pedido = database.get_pedido_by_id(order_id)
    if pedido is None:
        raise ValueError(f"No existe el pedido #{order_id}")

    # idempotencia básica: no reprocesar completados
    if pedido["estado"] == ESTADO_COMPLETADO:
        return

    if pedido["estado"] != ESTADO_PENDIENTE_PAGO:
        logger.warning(
            "procesar_post_pago omitido: pedido #%s estado=%s (solo se procesa pendiente_pago)",
            order_id,
            pedido["estado"],
        )
        return

    database.update_pedido_campos(order_id, estado=ESTADO_PAGADO, clear_error=True)
    pedido_pagado = database.get_pedido_by_id(order_id)
    if pedido_pagado is not None:
        ok_admin_pago = email_service.notify_admin_pago_confirmado(
            pedido_pagado, stripe_checkout_session_id=stripe_checkout_session_id
        )
        _log_notif(
            pedido_id=order_id,
            tipo="admin_pago_confirmado",
            canal="email",
            destinatario=email_service.get_admin_email(),
            ok=ok_admin_pago,
        )

    try:
        pdf_url = generar_pdf_automatico(order_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo en generación/subida de PDF para pedido #%s: %s", order_id, exc)
        database.update_pedido_campos(order_id, estado=ESTADO_ERROR_GENERACION, error_message=str(exc))
        ok = email_service.notify_admin_error(order_id, "generacion_pdf", str(exc), database.get_pedido_by_id(order_id))
        _log_notif(
            pedido_id=order_id,
            tipo="admin_error_generacion_pdf",
            canal="email",
            destinatario=email_service.get_admin_email(),
            ok=ok,
            error_message=str(exc),
        )
        return

    try:
        database.update_pedido_campos(order_id, pdf_url=pdf_url, clear_error=True)
        enviar_pdf_cliente(order_id, pdf_url)
    except Exception as exc:  # noqa: BLE001
        database.update_pedido_campos(order_id, estado=ESTADO_ERROR_ENVIO, error_message=str(exc))
        ok = email_service.notify_admin_error(order_id, "envio_email", str(exc), database.get_pedido_by_id(order_id))
        _log_notif(
            pedido_id=order_id,
            tipo="admin_error_envio_email",
            canal="email",
            destinatario=email_service.get_admin_email(),
            ok=ok,
            error_message=str(exc),
        )


def reenviar_notificaciones_pedido(order_id: int) -> dict[str, bool]:
    """
    Reenvía notificaciones relevantes según el estado actual del pedido.
    """
    pedido = database.get_pedido_by_id(order_id)
    if pedido is None:
        raise ValueError(f"No existe el pedido #{order_id}")

    resultados: dict[str, bool] = {}
    estado = str(pedido["estado"])

    if estado in (ESTADO_PAGADO, ESTADO_GENERANDO_PDF, ESTADO_PDF_GENERADO, ESTADO_ENVIANDO_EMAIL, ESTADO_COMPLETADO):
        ok_pago = email_service.notify_admin_pago_confirmado(pedido, stripe_checkout_session_id=None)
        _log_notif(
            pedido_id=order_id,
            tipo="admin_pago_confirmado_reenvio",
            canal="email",
            destinatario=email_service.get_admin_email(),
            ok=ok_pago,
        )
        resultados["admin_pago_confirmado"] = ok_pago

    if estado in (ESTADO_ERROR_GENERACION, ESTADO_ERROR_ENVIO, ESTADO_REVISION_MANUAL):
        stage = "generacion_pdf" if estado == ESTADO_ERROR_GENERACION else "envio_email"
        msg = str(pedido["error_message"] or "Reenvio manual de alerta desde admin.")
        ok_err = email_service.notify_admin_error(order_id, stage, msg, pedido)
        _log_notif(
            pedido_id=order_id,
            tipo=f"admin_error_reenvio_{stage}",
            canal="email",
            destinatario=email_service.get_admin_email(),
            ok=ok_err,
            error_message=msg,
        )
        resultados["admin_error"] = ok_err

    pdf_url = str(pedido["pdf_url"] or "").strip()
    if estado == ESTADO_COMPLETADO and pdf_url:
        review_url = _build_resena_url(order_id)

        ok_cliente = False
        error_cliente = ""
        try:
            email_service.send_customer_pdf_email(pedido, pdf_url=pdf_url, resena_url=review_url)
            ok_cliente = True
        except Exception as exc:  # noqa: BLE001
            error_cliente = str(exc)
        _log_notif(
            pedido_id=order_id,
            tipo="cliente_link_descarga_reenvio",
            canal="email",
            destinatario=str(pedido["email"]),
            ok=ok_cliente,
            error_message=error_cliente,
        )
        resultados["cliente_pdf"] = ok_cliente

        ok_admin_envio = email_service.notify_admin_envio_cliente_ok(database.get_pedido_by_id(order_id) or pedido)
        _log_notif(
            pedido_id=order_id,
            tipo="admin_pedido_enviado_cliente_reenvio",
            canal="email",
            destinatario=email_service.get_admin_email(),
            ok=ok_admin_envio,
        )
        resultados["admin_pedido_enviado"] = ok_admin_envio

    return resultados
