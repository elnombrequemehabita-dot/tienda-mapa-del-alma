# scripts/limpiar_drive_expirados.py

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Permite ejecutar este script desde la raíz del proyecto:
# python scripts/limpiar_drive_expirados.py
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.db import get_db

try:
    from app.google_drive_oauth import eliminar_archivo_drive_oauth
except Exception:
    eliminar_archivo_drive_oauth = None


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    text = str(value).strip()

    if not text:
        return None

    try:
        text = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except Exception:
        logger.warning("No se pudo interpretar fecha: %s", value)
        return None


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


def obtener_pedidos_con_drive() -> List[Dict[str, Any]]:
    db = get_db()

    cur = db.execute(
        """
        SELECT id, drive_file_id, pdf_url, drive_expires_at
        FROM pedidos
        WHERE drive_file_id IS NOT NULL
          AND drive_file_id != ''
          AND drive_expires_at IS NOT NULL
          AND drive_expires_at != ''
        ORDER BY id ASC
        """
    )

    return _fetchall_dict(cur)


def limpiar_columnas_drive(order_id: int) -> None:
    db = get_db()

    db.execute(
        """
        UPDATE pedidos
        SET drive_file_id = NULL,
            pdf_url = NULL,
            drive_expires_at = NULL,
            updated_at = ?
        WHERE id = ?
        """,
        (
            _utc_now().isoformat(),
            order_id,
        ),
    )

    db.commit()


def limpiar_drive_expirados() -> Dict[str, Any]:
    if eliminar_archivo_drive_oauth is None:
        raise RuntimeError(
            "No se pudo importar eliminar_archivo_drive_oauth desde app.google_drive_oauth"
        )

    ahora = _utc_now()
    pedidos = obtener_pedidos_con_drive()

    revisados = 0
    expirados = 0
    eliminados = 0
    errores = []

    logger.info("Pedidos con archivo Drive encontrados: %s", len(pedidos))

    for pedido in pedidos:
        revisados += 1

        pedido_id = pedido.get("id")
        drive_file_id = pedido.get("drive_file_id")
        drive_expires_at_raw = pedido.get("drive_expires_at")
        drive_expires_at = _parse_datetime(drive_expires_at_raw)

        if not drive_expires_at:
            logger.warning(
                "Pedido #%s tiene drive_expires_at inválido: %s",
                pedido_id,
                drive_expires_at_raw,
            )
            continue

        if drive_expires_at > ahora:
            logger.info(
                "Pedido #%s todavía no vence. Expira: %s",
                pedido_id,
                drive_expires_at.isoformat(),
            )
            continue

        expirados += 1

        logger.info(
            "Pedido #%s vencido. Eliminando Drive file_id=%s",
            pedido_id,
            drive_file_id,
        )

        try:
            eliminar_archivo_drive_oauth(drive_file_id)
            limpiar_columnas_drive(int(pedido_id))
            eliminados += 1

            logger.info(
                "Pedido #%s limpiado correctamente.",
                pedido_id,
            )

        except Exception as e:
            error_msg = f"Pedido #{pedido_id}: {e}"
            errores.append(error_msg)

            logger.exception(
                "Error limpiando pedido #%s",
                pedido_id,
            )

    resultado = {
        "ok": len(errores) == 0,
        "revisados": revisados,
        "expirados": expirados,
        "eliminados": eliminados,
        "errores": errores,
    }

    logger.info("Resultado limpieza: %s", resultado)

    return resultado


def main() -> None:
    app = create_app()

    with app.app_context():
        resultado = limpiar_drive_expirados()
        print(resultado)


if __name__ == "__main__":
    main()
