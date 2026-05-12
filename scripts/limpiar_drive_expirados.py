# scripts/limpiar_drive_expirados.py

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app import db as database

try:
    from app.google_drive_oauth import eliminar_archivo_drive_oauth
except Exception:
    eliminar_archivo_drive_oauth = None

try:
    from app.email_service import enviar_email_admin_error
except Exception:
    enviar_email_admin_error = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_dict(row: Any) -> Dict[str, Any]:
    try:
        return dict(row)
    except Exception:
        return {k: row[k] for k in row.keys()}


def _fetchall_dict(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    return [_row_to_dict(r) for r in rows] if rows else []


def _notificar_admin_resumen(resultado: Dict[str, Any]) -> None:
    if enviar_email_admin_error is None:
        return

    if resultado.get("eliminados", 0) <= 0 and resultado.get("fallidos", 0) <= 0:
        return

    lineas = [
        "Resumen de limpieza automática Google Drive 72h.",
        "",
        f"Fecha UTC: {_utc_now().isoformat()}",
        f"Encontrados: {resultado.get('encontrados', 0)}",
        f"Eliminados: {resultado.get('eliminados', 0)}",
        f"Ya no existían en Drive: {resultado.get('ya_no_existian', 0)}",
        f"Fallidos: {resultado.get('fallidos', 0)}",
        "",
        "Pedidos eliminados:",
        ", ".join(map(str, resultado.get("pedidos_eliminados") or [])) or "(ninguno)",
        "",
        "Errores:",
    ]
    for item in resultado.get("errores") or []:
        lineas.append(f"- Pedido #{item.get('pedido_id')}: {item.get('error')}")

    mensaje = "\n".join(lineas)

    try:
        try:
            enviar_email_admin_error("CRON-DRIVE-72H", mensaje)
        except TypeError:
            enviar_email_admin_error(
                asunto="Limpieza Drive 72h - resumen",
                mensaje=mensaje,
            )
    except Exception:
        logger.exception("No se pudo enviar email admin de resumen Drive 72h.")


def _pedidos_expirados(limit: int = 200) -> List[Dict[str, Any]]:
    if hasattr(database, "list_pedidos_drive_expirados"):
        return [_row_to_dict(r) for r in database.list_pedidos_drive_expirados(limit=limit)]

    cur = database.execute(
        """
        SELECT *
        FROM pedidos
        WHERE drive_file_id IS NOT NULL
          AND drive_file_id <> ''
          AND drive_expires_at IS NOT NULL
          AND drive_expires_at < CURRENT_TIMESTAMP
          AND estado IN ('completado', 'pdf_generado', 'enviado')
        ORDER BY drive_expires_at ASC, id ASC
        LIMIT ?
        """,
        (int(limit),),
    )
    return _fetchall_dict(cur)


def _marcar_eliminado(pedido_id: int) -> None:
    if hasattr(database, "marcar_drive_eliminado"):
        database.marcar_drive_eliminado(int(pedido_id))
        return

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
    if hasattr(database, "marcar_drive_delete_error"):
        database.marcar_drive_delete_error(int(pedido_id), error)
        return

    database.update_pedido_campos(
        int(pedido_id),
        drive_status="delete_error",
        drive_delete_error=error[:2000],
    )


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

        except Exception as exc:
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


def main() -> int:
    app = create_app()
    with app.app_context():
        try:
            database.init_db()
        except Exception:
            logger.exception("No se pudo inicializar/verificar DB antes de limpiar Drive.")
            raise

        resultado = limpiar_drive_expirados()
        print(resultado)
        return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
