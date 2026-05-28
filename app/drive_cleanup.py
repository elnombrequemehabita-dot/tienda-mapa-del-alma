"""Limpieza de PDFs vencidos en Google Drive."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app import db as database

try:
    from app.google_drive_oauth import eliminar_archivo_drive_oauth
except Exception:
    eliminar_archivo_drive_oauth = None

try:
    from app.email_service import enviar_email_admin_error
except Exception:
    enviar_email_admin_error = None


logger = logging.getLogger(__name__)

ESTADOS_CON_DRIVE_EXPIRABLE = (
    "completado",
    "pdf_entregado",
    "pdf_generado",
    "pdf_generado_pendiente_de_link",
    "pendiente_impresion",
    "impreso",
    "enviado",
    "entregado",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_dict(row: Any) -> Dict[str, Any]:
    try:
        return dict(row)
    except Exception:
        return {k: row[k] for k in row.keys()}


def _fetchall_dict(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    return [_row_to_dict(row) for row in rows] if rows else []


def _pedidos_expirados(limit: int = 200) -> List[Dict[str, Any]]:
    placeholders = ", ".join(["?"] * len(ESTADOS_CON_DRIVE_EXPIRABLE))
    cur = database.execute(
        f"""
        SELECT *
        FROM pedidos
        WHERE drive_file_id IS NOT NULL
          AND drive_file_id <> ''
          AND drive_expires_at IS NOT NULL
          AND drive_expires_at < CURRENT_TIMESTAMP
          AND COALESCE(drive_status, 'active') <> 'deleted'
          AND estado IN ({placeholders})
        ORDER BY drive_expires_at ASC, id ASC
        LIMIT ?
        """,
        (*ESTADOS_CON_DRIVE_EXPIRABLE, int(limit)),
    )
    return _fetchall_dict(cur)


def _marcar_eliminado(pedido_id: int) -> None:
    database.update_pedido_campos(
        int(pedido_id),
        drive_file_id=None,
        drive_view_link=None,
        drive_download_link=None,
        drive_deleted_at=_utc_now().isoformat(),
        drive_status="deleted",
        drive_delete_error=None,
    )


def _marcar_error(pedido_id: int, error: str) -> None:
    database.update_pedido_campos(
        int(pedido_id),
        drive_status="delete_error",
        drive_delete_error=error[:2000],
    )


def _notificar_admin_resumen(resultado: Dict[str, Any]) -> None:
    if enviar_email_admin_error is None:
        return
    if resultado.get("eliminados", 0) <= 0 and resultado.get("fallidos", 0) <= 0:
        return

    lineas = [
        "Resumen de limpieza automática Google Drive 48h.",
        "",
        f"Fecha UTC: {_utc_now().isoformat()}",
        f"Encontrados: {resultado.get('encontrados', 0)}",
        f"Eliminados: {resultado.get('eliminados', 0)}",
        f"Ya no existían en Drive: {resultado.get('ya_no_existian', 0)}",
        f"Fallidos: {resultado.get('fallidos', 0)}",
        "",
        "Pedidos eliminados:",
        ", ".join(map(str, resultado.get("pedidos_eliminados") or [])) or "(ninguno)",
    ]

    errores = resultado.get("errores") or []
    if errores:
        lineas.extend(["", "Errores:"])
        for item in errores:
            lineas.append(f"- Pedido #{item.get('pedido_id')}: {item.get('error')}")

    try:
        enviar_email_admin_error(0, "\n".join(lineas), stage="drive_cleanup")
    except TypeError:
        enviar_email_admin_error(asunto="Limpieza Drive 48h - resumen", mensaje="\n".join(lineas))
    except Exception:
        logger.exception("No se pudo enviar email admin de resumen Drive 48h.")


def limpiar_drive_expirados(limit: int = 200, enviar_resumen: bool = True) -> Dict[str, Any]:
    if eliminar_archivo_drive_oauth is None:
        raise RuntimeError("No se pudo importar eliminar_archivo_drive_oauth desde app.google_drive_oauth")

    pedidos = _pedidos_expirados(limit=limit)
    logger.info("Pedidos con Drive vencido encontrados: %s", len(pedidos))

    resultado: Dict[str, Any] = {
        "ok": True,
        "encontrados": len(pedidos),
        "eliminados": 0,
        "ya_no_existian": 0,
        "fallidos": 0,
        "pedidos_eliminados": [],
        "errores": [],
    }

    for pedido in pedidos:
        pedido_id = int(pedido.get("id"))
        file_id = (pedido.get("drive_file_id") or "").strip()
        if not file_id:
            continue

        logger.info("Eliminando Drive vencido pedido #%s file_id=%s", pedido_id, file_id)
        try:
            delete_result = eliminar_archivo_drive_oauth(file_id)
            if isinstance(delete_result, dict) and delete_result.get("already_missing"):
                resultado["ya_no_existian"] += 1
            else:
                resultado["eliminados"] += 1

            _marcar_eliminado(pedido_id)
            resultado["pedidos_eliminados"].append(pedido_id)
            logger.info("Pedido #%s limpiado correctamente.", pedido_id)
        except Exception as exc:  # noqa: BLE001
            resultado["ok"] = False
            resultado["fallidos"] += 1
            err = str(exc)[:2000]
            resultado["errores"].append({"pedido_id": pedido_id, "file_id": file_id, "error": err})
            _marcar_error(pedido_id, err)
            logger.exception("Error limpiando Drive de pedido #%s", pedido_id)

    if enviar_resumen:
        _notificar_admin_resumen(resultado)

    logger.info("Resumen limpieza Drive: %s", resultado)
    return resultado
