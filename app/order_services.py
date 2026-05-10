# app/order_services.py

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import current_app

from app import db as database
from app.db import get_db
from app.pdf_generator import generar_pdf_desde_tienda

try:
    from app.openai_generator import generar_contenido_mapa
except Exception:
    generar_contenido_mapa = None

try:
    from app.email_service import (
        enviar_email_pedido_completado,
        enviar_email_admin_error,
        notify_admin_pago_confirmado,
        notify_customer_pago_confirmado,
    )
except Exception:
    enviar_email_pedido_completado = None
    enviar_email_admin_error = None
    notify_admin_pago_confirmado = None
    notify_customer_pago_confirmado = None

try:
    from app.google_drive_oauth import (
        subir_pdf_a_drive_oauth,
        eliminar_archivo_drive_oauth,
    )
except Exception:
    subir_pdf_a_drive_oauth = None
    eliminar_archivo_drive_oauth = None


logger = logging.getLogger(__name__)

ESTADO_PENDIENTE_PAGO = "pendiente_pago"
ESTADO_PAGADO = "pagado"
ESTADO_GENERANDO_PDF = "generando_pdf"
ESTADO_PDF_GENERADO = "pdf_generado"
ESTADO_COMPLETADO = "completado"
ESTADO_ERROR = "error_generacion"
ESTADO_ERROR_ENVIO = "error_envio"

DRIVE_EXPIRACION_HORAS = 72


# =========================================================
# HELPERS
# =========================================================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _db_placeholder() -> str:
    # El código interno usa ?. app.db convierte ? -> %s en PostgreSQL.
    return "?"


def _execute(db, sql: str, params: tuple = ()):  # db se conserva por compatibilidad
    return database.execute(sql, params)


def _commit(db):  # db se conserva por compatibilidad
    database.commit()


def _rollback(db):  # db se conserva por compatibilidad
    database.rollback()


def _fetchone_dict(cursor) -> Optional[Dict[str, Any]]:
    row = cursor.fetchone()
    if row is None:
        return None

    try:
        return dict(row)
    except Exception:
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, row))


def _fetchall_dict(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    if not rows:
        return []

    result = []
    for row in rows:
        try:
            result.append(dict(row))
        except Exception:
            columns = [col[0] for col in cursor.description]
            result.append(dict(zip(columns, row)))
    return result


def _column_exists(db, table: str, column: str) -> bool:
    """
    Compatibilidad defensiva. Las actualizaciones reales pasan por app.db.
    """
    try:
        cur = database.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = ? AND column_name = ?
            LIMIT 1
            """,
            (table, column),
        )
        if cur.fetchone() is not None:
            return True
    except Exception:
        pass

    try:
        cur = db.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = []
        for r in cur.fetchall():
            try:
                cols.append(r["name"])
            except Exception:
                cols.append(r[1])
        return column in cols
    except Exception:
        return False


def _safe_update_pedido(order_id: int, campos: Dict[str, Any]) -> None:
    """
    Actualiza pedidos usando app.db como capa oficial.

    Mapea nombres antiguos:
    - updated_at / actualizado_en se ignoran porque app.db actualiza actualizado_en.
    - pdf_url / download_link se guardan como drive_download_link.
    - error_message se guarda como error.
    - drive_expires_at se ignora si la base actual no tiene esa columna.
    """
    if not campos:
        return

    normalizados: Dict[str, Any] = {}
    clear_error = False

    for col, val in campos.items():
        if col in {"updated_at", "actualizado_en", "drive_expires_at"}:
            continue
        if col in {"pdf_url", "download_link", "link_pdf"}:
            col = "drive_download_link"
        elif col == "error_message":
            col = "error"

        if col == "error" and val is None:
            clear_error = True
            continue

        normalizados[col] = val

    if not normalizados and not clear_error:
        return

    database.update_pedido_campos(
        int(order_id),
        clear_error=clear_error,
        **normalizados,
    )


def _project_root() -> Path:
    return Path(current_app.root_path).resolve().parent


# =========================================================
# PEDIDOS
# =========================================================

def obtener_pedido(order_id: int) -> Optional[Dict[str, Any]]:
    row = database.get_pedido_by_id(int(order_id))
    if row is None:
        return None

    pedido = dict(row)

    # Alias de lectura para mantener compatibilidad con este módulo.
    if not pedido.get("pdf_url"):
        pedido["pdf_url"] = (
            pedido.get("drive_download_link")
            or pedido.get("drive_view_link")
        )

    if not pedido.get("created_at"):
        pedido["created_at"] = pedido.get("creado_en")

    return pedido


def marcar_estado(order_id: int, estado: str, error: Optional[str] = None) -> None:
    database.update_estado_pedido(
        int(order_id),
        estado,
        error=str(error) if error else None,
    )


def marcar_pedido_pagado(order_id: int) -> None:
    marcar_estado(order_id, ESTADO_PAGADO)


def marcar_completado(order_id: int) -> None:
    marcar_estado(order_id, ESTADO_COMPLETADO)


def marcar_error(order_id: int, error: str) -> None:
    marcar_estado(order_id, ESTADO_ERROR, error)


def _notificar_pago_confirmado_seguro(order_id: int) -> None:
    """
    Avisos inmediatos cuando Stripe confirma pago:
    - admin: pago confirmado
    - cliente: pago recibido y próximos pasos

    Ninguno bloquea la generación de PDF si Brevo/email falla.
    """
    pedido = obtener_pedido(order_id)
    if not pedido:
        return

    if notify_admin_pago_confirmado is not None:
        try:
            notify_admin_pago_confirmado(pedido)
        except Exception:
            logger.exception("No se pudo enviar aviso admin de pago confirmado pedido #%s", order_id)

    if notify_customer_pago_confirmado is not None:
        try:
            notify_customer_pago_confirmado(pedido)
        except Exception:
            logger.exception("No se pudo enviar aviso cliente de pago confirmado pedido #%s", order_id)


def _normalizar_pedido_para_pdf(pedido: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(pedido)

    data.setdefault("pedido_id", pedido.get("id"))
    data.setdefault("order_id", pedido.get("id"))

    if "nombre" not in data or not data.get("nombre"):
        data["nombre"] = (
            pedido.get("nombre_cliente")
            or pedido.get("first_name")
            or pedido.get("cliente_nombre")
            or ""
        )

    if "apellidos" not in data or not data.get("apellidos"):
        data["apellidos"] = (
            pedido.get("apellidos_cliente")
            or pedido.get("last_name")
            or pedido.get("cliente_apellidos")
            or ""
        )

    if "fecha_nacimiento" not in data or not data.get("fecha_nacimiento"):
        data["fecha_nacimiento"] = (
            pedido.get("birth_date")
            or pedido.get("fecha")
            or pedido.get("nacimiento")
            or ""
        )

    if "sexo" not in data or not data.get("sexo"):
        data["sexo"] = (
            pedido.get("genero")
            or pedido.get("gender")
            or ""
        )

    return data


# =========================================================
# REUTILIZACION DE JSON OPENAI
# =========================================================

def _cargar_json_si_existe(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists() or not path.is_file():
            return None

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and data:
            logger.info("JSON OpenAI reutilizado desde: %s", path)
            return data

    except Exception:
        logger.exception("No se pudo leer JSON existente: %s", path)

    return None


def _buscar_json_openai_guardado(order_id: int, pedido: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Busca contenido OpenAI ya guardado para NO gastar saldo otra vez.

    Revisa:
    1. Columnas posibles en DB.
    2. Rutas comunes en output/.
    3. Cualquier JSON relacionado con el pedido_id.
    """

    posibles_columnas = [
        "contenido_openai",
        "openai_json",
        "json_openai",
        "contenido_json",
        "json_guardado",
    ]

    for col in posibles_columnas:
        value = pedido.get(col)

        if not value:
            continue

        if isinstance(value, dict):
            logger.info("Contenido OpenAI reutilizado desde columna DB: %s", col)
            return value

        if isinstance(value, str):
            text = value.strip()

            if not text:
                continue

            if text.startswith("{"):
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and data:
                        logger.info("Contenido OpenAI reutilizado desde JSON DB: %s", col)
                        return data
                except Exception:
                    pass

            posible_path = Path(text)
            if not posible_path.is_absolute():
                posible_path = _project_root() / posible_path

            data = _cargar_json_si_existe(posible_path)
            if data:
                return data

    root = _project_root()

    posibles_paths = [
        root / "output" / "json" / f"pedido_{order_id}.json",
        root / "output" / "json" / f"mapa_alma_{order_id}.json",
        root / "output" / "openai" / f"pedido_{order_id}.json",
        root / "output" / "openai" / f"mapa_alma_{order_id}.json",
        root / "output" / "contenido" / f"pedido_{order_id}.json",
        root / "output" / "contenido_openai" / f"pedido_{order_id}.json",
        root / "output" / f"pedido_{order_id}.json",
        root / "output" / f"mapa_alma_{order_id}.json",
    ]

    for path in posibles_paths:
        data = _cargar_json_si_existe(path)
        if data:
            return data

    output_dir = root / "output"

    try:
        if output_dir.exists():
            patrones = [
                f"*{order_id}*.json",
                f"pedido_{order_id}_*.json",
                f"mapa_alma_{order_id}_*.json",
            ]

            for patron in patrones:
                for path in output_dir.rglob(patron):
                    data = _cargar_json_si_existe(path)
                    if data:
                        return data
    except Exception:
        logger.exception("Error buscando JSON OpenAI guardado para pedido #%s", order_id)

    return None


def _asegurar_contenido_openai(data_pdf: Dict[str, Any], pedido: Dict[str, Any]) -> Dict[str, Any]:
    """
    Regla de oro:
    - Si ya existe contenido, reutilizar.
    - Si existe JSON guardado, reutilizar.
    - Solo si no existe nada, llamar OpenAI.
    """

    order_id = int(data_pdf.get("pedido_id") or data_pdf.get("id") or pedido.get("id"))

    if data_pdf.get("contenido_openai"):
        logger.info("Pedido #%s ya trae contenido_openai. No se llama OpenAI.", order_id)
        return data_pdf

    if data_pdf.get("secciones"):
        logger.info("Pedido #%s trae secciones. No se llama OpenAI.", order_id)
        data_pdf["contenido_openai"] = data_pdf["secciones"]
        return data_pdf

    contenido_guardado = _buscar_json_openai_guardado(order_id, pedido)

    if contenido_guardado:
        data_pdf["contenido_openai"] = contenido_guardado
        data_pdf["_reutilizado"] = True
        return data_pdf

    if generar_contenido_mapa is None:
        raise RuntimeError(
            "No se pudo importar app.openai_generator.generar_contenido_mapa."
        )

    logger.warning(
        "Pedido #%s NO tiene JSON guardado. Se llamará OpenAI UNA sola vez para este pedido.",
        order_id,
    )

    contenido = generar_contenido_mapa(data_pdf)

    if not contenido:
        raise RuntimeError("OpenAI no devolvió contenido válido.")

    data_pdf["contenido_openai"] = contenido
    data_pdf["_reutilizado"] = bool(
        isinstance(contenido, dict) and contenido.get("_reutilizado")
    )

    return data_pdf


# =========================================================
# GOOGLE DRIVE
# =========================================================

def _crear_link_local(order_id: int) -> str:
    base_url = (
        current_app.config.get("PUBLIC_BASE_URL")
        or current_app.config.get("BASE_URL")
        or ""
    )

    base_url = str(base_url).rstrip("/")

    if base_url:
        return f"{base_url}/descarga/{order_id}"

    return f"/descarga/{order_id}"


def _subir_pdf_drive_seguro(
    pdf_path: str,
    order_id: int,
) -> Optional[Dict[str, Any]]:

    if subir_pdf_a_drive_oauth is None:
        logger.warning("Google Drive OAuth no disponible. Se usará link local.")
        return None

    archivo = Path(pdf_path)

    if not archivo.exists():
        raise FileNotFoundError(
            f"No existe el PDF para subir a Drive: {pdf_path}"
        )

    nombre_drive = f"mapa_alma_{order_id}.pdf"

    try:
        resultado = subir_pdf_a_drive_oauth(
            str(archivo),
            nombre_drive,
        )

        if not isinstance(resultado, dict):
            raise RuntimeError(
                f"Respuesta inválida de Drive: {resultado}"
            )

        file_id = resultado.get("file_id")
        download_link = (
            resultado.get("download_link")
            or resultado.get("view_link")
        )

        if not file_id or not download_link:
            raise RuntimeError(
                f"Drive no devolvió file_id/download_link: {resultado}"
            )

        logger.info(
            "PDF subido a Drive correctamente. Pedido #%s file_id=%s",
            order_id,
            file_id,
        )

        return {
            "file_id": file_id,
            "download_link": download_link,
            "view_link": resultado.get("view_link") or download_link,
            "name": resultado.get("name") or nombre_drive,
        }

    except Exception as e:
        logger.exception(
            "Error subiendo PDF a Drive pedido #%s: %s",
            order_id,
            e,
        )
        return None


def _pdf_local_existente(pedido: Dict[str, Any], order_id: int) -> Optional[Path]:
    posibles = []

    if pedido.get("pdf_path"):
        posibles.append(Path(str(pedido["pdf_path"])))

    posibles.append(_project_root() / "output" / f"mapa_alma_{order_id}.pdf")

    for path in posibles:
        if not path.is_absolute():
            path = _project_root() / path

        if path.exists() and path.is_file():
            return path

    return None


def _drive_link_vigente(pedido: Dict[str, Any]) -> bool:
    drive_file_id = pedido.get("drive_file_id")
    pdf_url = (
        pedido.get("drive_download_link")
        or pedido.get("pdf_url")
        or pedido.get("drive_view_link")
    )

    # La base actual no siempre tiene drive_expires_at.
    # Si existe y está vencido, se regenera el enlace; si no existe, se acepta el link.
    expires_at = _parse_datetime(pedido.get("drive_expires_at"))
    if not drive_file_id or not pdf_url:
        return False
    if expires_at is None:
        return True
    return expires_at > _utc_now()


def _guardar_drive_en_db(order_id: int, pdf_path: Path, drive_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    expires_at = _utc_now() + timedelta(hours=DRIVE_EXPIRACION_HORAS)

    if drive_result:
        pdf_url = drive_result["download_link"]
        drive_file_id = drive_result["file_id"]
        drive_expires_at = _iso(expires_at)
    else:
        pdf_url = _crear_link_local(order_id)
        drive_file_id = None
        drive_expires_at = None

    _safe_update_pedido(
        order_id,
        {
            "estado": ESTADO_PDF_GENERADO,
            "pdf_path": str(pdf_path),
            "pdf_url": pdf_url,
            "drive_file_id": drive_file_id,
            "drive_expires_at": drive_expires_at,
            "updated_at": _iso(_utc_now()),
        },
    )

    return {
        "ok": True,
        "order_id": order_id,
        "pdf_path": str(pdf_path),
        "pdf_url": pdf_url,
        "drive_file_id": drive_file_id,
        "drive_expires_at": drive_expires_at,
        "drive_usado": bool(drive_file_id),
    }


# =========================================================
# EMAILS
# =========================================================

def _enviar_email_cliente_seguro(
    pedido: Dict[str, Any],
    pdf_url: str,
) -> None:

    if enviar_email_pedido_completado is None:
        logger.warning(
            "Función enviar_email_pedido_completado no disponible."
        )
        return

    try:
        try:
            enviar_email_pedido_completado(
                pedido,
                pdf_url,
            )
        except TypeError:
            enviar_email_pedido_completado(
                email=(
                    pedido.get("email")
                    or pedido.get("cliente_email")
                    or pedido.get("correo")
                ),
                nombre=(
                    pedido.get("nombre")
                    or pedido.get("nombre_cliente")
                    or pedido.get("cliente_nombre")
                ),
                pdf_url=pdf_url,
                pedido=pedido,
            )

        logger.info(
            "Email enviado correctamente pedido #%s",
            pedido.get("id"),
        )

    except Exception as e:
        logger.exception(
            "Error enviando email cliente pedido #%s: %s",
            pedido.get("id"),
            e,
        )
        raise


def _es_error_openai_credito(error: Exception | str) -> bool:
    texto = str(error or "").lower()
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
    return any(c in texto for c in claves)


def _stage_error_post_pago(error: Exception | str) -> str:
    if _es_error_openai_credito(error):
        return "openai_credito"
    return "generacion_pdf"


def _notificar_admin_error(
    order_id: int,
    error: Exception,
    stage: Optional[str] = None,
) -> None:

    if enviar_email_admin_error is None:
        logger.warning(
            "No existe enviar_email_admin_error. Error pedido #%s: %s",
            order_id,
            error,
        )
        return

    pedido = obtener_pedido(order_id)
    stage_final = stage or _stage_error_post_pago(error)

    try:
        try:
            enviar_email_admin_error(
                int(order_id),
                str(error),
                stage=stage_final,
                pedido=pedido,
            )
        except TypeError:
            enviar_email_admin_error(
                order_id,
                str(error),
            )
    except Exception:
        logger.exception("Falló email de error admin.")


# =========================================================
# GENERAR PDF AUTOMATICO
# =========================================================

def generar_pdf_automatico(order_id: int, forzar_regeneracion: bool = False) -> Dict[str, Any]:
    """
    Flujo seguro y económico:

    CASO 1:
    Si ya existe PDF + Drive vigente:
        NO OpenAI
        NO PDF nuevo
        NO subida nueva
        devuelve lo guardado

    CASO 2:
    Si ya existe PDF local pero falta Drive:
        NO OpenAI
        NO PDF nuevo
        solo sube PDF existente a Drive

    CASO 3:
    Si no existe PDF:
        busca JSON guardado
        si existe, genera PDF sin llamar OpenAI
        si no existe, llama OpenAI una sola vez
    """

    pedido = obtener_pedido(order_id)

    if not pedido:
        raise ValueError(f"No existe el pedido #{order_id}")

    pdf_existente = _pdf_local_existente(pedido, order_id)

    if not forzar_regeneracion and pdf_existente and _drive_link_vigente(pedido):
        logger.info(
            "Pedido #%s ya tiene PDF y Drive vigente. No se llama OpenAI.",
            order_id,
        )
        return {
            "ok": True,
            "order_id": order_id,
            "pdf_path": str(pdf_existente),
            "pdf_url": (pedido.get("drive_download_link") or pedido.get("pdf_url") or pedido.get("drive_view_link")),
            "drive_file_id": pedido.get("drive_file_id"),
            "drive_expires_at": pedido.get("drive_expires_at"),
            "drive_usado": True,
            "reutilizado": True,
            "sin_openai": True,
        }

    if not forzar_regeneracion and pdf_existente:
        logger.info(
            "Pedido #%s ya tiene PDF local. Solo se subirá/reparará Drive. No se llama OpenAI.",
            order_id,
        )

        drive_result = _subir_pdf_drive_seguro(str(pdf_existente), order_id)

        resultado = _guardar_drive_en_db(order_id, pdf_existente, drive_result)
        resultado["reutilizado"] = True
        resultado["sin_openai"] = True
        return resultado

    marcar_estado(order_id, ESTADO_GENERANDO_PDF)

    try:
        logger.info("Generando PDF pedido #%s", order_id)

        data_pdf = _normalizar_pedido_para_pdf(pedido)
        data_pdf = _asegurar_contenido_openai(data_pdf, pedido)

        resultado_pdf = generar_pdf_desde_tienda(data_pdf)

        if isinstance(resultado_pdf, dict):
            pdf_path = (
                resultado_pdf.get("pdf_path")
                or resultado_pdf.get("path")
                or resultado_pdf.get("archivo")
                or resultado_pdf.get("ruta")
            )
        else:
            pdf_path = str(resultado_pdf)

        if not pdf_path:
            raise RuntimeError(
                f"El generador PDF no devolvió ruta válida: {resultado_pdf}"
            )

        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            raise FileNotFoundError(
                f"El PDF generado no existe: {pdf_path}"
            )

        drive_result = _subir_pdf_drive_seguro(str(pdf_file), order_id)
        resultado = _guardar_drive_en_db(order_id, pdf_file, drive_result)
        resultado["reutilizado"] = bool(data_pdf.get("_reutilizado"))
        resultado["sin_openai"] = bool(data_pdf.get("_reutilizado"))

        return resultado

    except Exception as e:
        _rollback(get_db())
        marcar_estado(order_id, ESTADO_ERROR, str(e))
        _notificar_admin_error(order_id, e)

        logger.exception(
            "Error generando PDF pedido #%s",
            order_id,
        )

        raise


# =========================================================
# POST PAGO / STRIPE
# =========================================================

def procesar_post_pago(order_id: int) -> Dict[str, Any]:
    pedido = obtener_pedido(order_id)

    if not pedido:
        raise ValueError(f"No existe el pedido #{order_id}")

    estado = pedido.get("estado")

    estados_validos = {
        ESTADO_PENDIENTE_PAGO,
        ESTADO_PAGADO,
        ESTADO_PDF_GENERADO,
        ESTADO_COMPLETADO,
        ESTADO_ERROR,
        ESTADO_ERROR_ENVIO,
    }

    if estado not in estados_validos:
        logger.warning(
            "procesar_post_pago omitido: pedido #%s estado=%s",
            order_id,
            estado,
        )

        return {
            "ok": False,
            "omitido": True,
            "order_id": order_id,
            "estado": estado,
            "motivo": "Estado no procesable",
        }

    try:
        logger.info("Procesando post-pago pedido #%s", order_id)

        pago_recien_confirmado = estado == ESTADO_PENDIENTE_PAGO

        if estado != ESTADO_COMPLETADO:
            marcar_estado(order_id, ESTADO_PAGADO)

        if pago_recien_confirmado:
            _notificar_pago_confirmado_seguro(order_id)

        resultado_pdf = generar_pdf_automatico(order_id)

        pedido_actualizado = obtener_pedido(order_id) or pedido

        pdf_url = (
            resultado_pdf.get("pdf_url")
            or resultado_pdf.get("drive_download_link")
            or pedido_actualizado.get("drive_download_link")
            or pedido_actualizado.get("pdf_url")
            or pedido_actualizado.get("drive_view_link")
        )

        if not pdf_url:
            raise RuntimeError(f"No existe pdf_url para pedido #{order_id}")

        try:
            _enviar_email_cliente_seguro(
                pedido_actualizado,
                pdf_url,
            )
        except Exception as exc:
            marcar_estado(order_id, ESTADO_ERROR_ENVIO, str(exc))
            _notificar_admin_error(order_id, exc, stage="envio_email")
            raise

        _safe_update_pedido(
            order_id,
            {
                "estado": ESTADO_COMPLETADO,
            },
        )

        logger.info("Pedido #%s completado correctamente.", order_id)

        return {
            "ok": True,
            "order_id": order_id,
            "estado": ESTADO_COMPLETADO,
            "pdf_url": pdf_url,
            "drive_file_id": resultado_pdf.get("drive_file_id"),
            "drive_expires_at": resultado_pdf.get("drive_expires_at"),
            "drive_usado": resultado_pdf.get("drive_usado"),
            "sin_openai": resultado_pdf.get("sin_openai"),
            "reutilizado": resultado_pdf.get("reutilizado"),
        }

    except Exception as e:
        _rollback(get_db())
        pedido_final = obtener_pedido(order_id)
        if not pedido_final or pedido_final.get("estado") != ESTADO_ERROR_ENVIO:
            marcar_estado(order_id, ESTADO_ERROR, str(e))
        _notificar_admin_error(order_id, e)

        logger.exception(
            "Error procesando post pago pedido #%s",
            order_id,
        )

        raise


# =========================================================
# REGENERAR PDF
# =========================================================

def regenerar_pdf_pedido(order_id: int, forzar_openai: bool = False) -> Dict[str, Any]:
    """
    Para admin.

    Por defecto NO fuerza OpenAI:
    - si hay PDF existente, reutiliza
    - si hay JSON guardado, reutiliza
    - solo si no hay nada, llama OpenAI

    Si algún día quieres generar texto nuevo de cero:
    regenerar_pdf_pedido(order_id, forzar_openai=True)
    """

    pedido = obtener_pedido(order_id)

    if not pedido:
        raise ValueError(f"No existe el pedido #{order_id}")

    viejo_drive_file_id = pedido.get("drive_file_id")

    if viejo_drive_file_id and eliminar_archivo_drive_oauth:
        try:
            eliminar_archivo_drive_oauth(viejo_drive_file_id)
            logger.info(
                "Archivo Drive anterior eliminado pedido #%s",
                order_id,
            )
        except Exception:
            logger.exception(
                "No se pudo eliminar archivo Drive anterior pedido #%s",
                order_id,
            )

    _safe_update_pedido(
        order_id,
        {
            "drive_file_id": None,
            "pdf_url": None,
            "drive_expires_at": None,
            "estado": ESTADO_PAGADO,
            "updated_at": _iso(_utc_now()),
        },
    )

    return generar_pdf_automatico(order_id, forzar_regeneracion=forzar_openai)


# =========================================================
# PEDIDOS ATASCADOS
# =========================================================

def detectar_pedidos_atascados(minutos: int = 30, timeout_minutes: Optional[int] = None) -> List[Dict[str, Any]]:
    db = get_db()
    ph = _db_placeholder()

    if timeout_minutes is not None:
        minutos = int(timeout_minutes)

    limite = _utc_now() - timedelta(minutes=minutos)
    limite_iso = _iso(limite)

    try:
        cur = _execute(
            db,
            f"""
            SELECT *
            FROM pedidos
            WHERE estado = {ph}
              AND (
                    actualizado_en IS NULL
                    OR actualizado_en < {ph}
                  )
            ORDER BY id DESC
            """,
            (
                ESTADO_GENERANDO_PDF,
                limite_iso,
            ),
        )

        pedidos = _fetchall_dict(cur)

        logger.info(
            "Pedidos atascados detectados: %s",
            len(pedidos),
        )

        return pedidos

    except Exception:
        logger.exception("Error detectando pedidos atascados.")
        return []


def resetear_pedido_atascado(order_id: int) -> None:
    marcar_estado(order_id, ESTADO_PAGADO)


def limpiar_pedidos_atascados(minutos: int = 30) -> List[Dict[str, Any]]:
    pedidos = detectar_pedidos_atascados(minutos=minutos)

    for pedido in pedidos:
        pedido_id = pedido.get("id")
        if pedido_id:
            try:
                resetear_pedido_atascado(int(pedido_id))
            except Exception:
                logger.exception(
                    "No se pudo resetear pedido atascado #%s",
                    pedido_id,
                )

    return pedidos


# =========================================================
# REENVIAR NOTIFICACIONES
# =========================================================

def reenviar_notificaciones_pedido(order_id: int) -> Dict[str, Any]:
    pedido = obtener_pedido(order_id)

    if not pedido:
        raise ValueError(f"No existe el pedido #{order_id}")

    pdf_url = (
        pedido.get("drive_download_link")
        or pedido.get("pdf_url")
        or pedido.get("drive_view_link")
        or pedido.get("download_link")
        or pedido.get("link_pdf")
    )

    if not pdf_url and pedido.get("pdf_path"):
        pdf_url = _crear_link_local(order_id)

    if not pdf_url:
        raise RuntimeError(
            f"El pedido #{order_id} no tiene pdf_url ni pdf_path para reenviar."
        )

    try:
        _enviar_email_cliente_seguro(
            pedido,
            pdf_url,
        )

        logger.info(
            "Notificación reenviada correctamente pedido #%s",
            order_id,
        )

        return {
            "ok": True,
            "order_id": order_id,
            "pdf_url": pdf_url,
            "mensaje": "Notificación reenviada correctamente.",
        }

    except Exception as e:
        _notificar_admin_error(order_id, e)

        logger.exception(
            "Error reenviando notificación pedido #%s",
            order_id,
        )

        raise


def reenviar_email_pedido(order_id: int) -> Dict[str, Any]:
    return reenviar_notificaciones_pedido(order_id)


def enviar_notificaciones_pedido(order_id: int) -> Dict[str, Any]:
    return reenviar_notificaciones_pedido(order_id)


def enviar_link_pedido(order_id: int) -> Dict[str, Any]:
    return reenviar_notificaciones_pedido(order_id)
