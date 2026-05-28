from __future__ import annotations

import logging
import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()

"""
Punto de entrada para ejecutar la tienda.

Local:
    python run.py

Render/produccion:
    python -m waitress --listen=0.0.0.0:$PORT run:app

Este archivo imprime logs claros de arranque para diagnosticar errores en Render.
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger("run")


def _debug_env() -> None:
    """Imprime informacion segura de entorno sin revelar secretos."""
    logger.info("=== ARRANQUE MAPA DEL ALMA ===")
    logger.info("Python: %s", sys.version)
    logger.info("PORT presente: %s", bool(os.environ.get("PORT")))
    logger.info("FLASK_DEBUG: %s", os.environ.get("FLASK_DEBUG"))
    logger.info("DATABASE_URL presente: %s", bool(os.environ.get("DATABASE_URL")))
    logger.info("OPENAI_API_KEY presente: %s", bool(os.environ.get("OPENAI_API_KEY")))
    logger.info("EMAIL_PASSWORD presente: %s", bool(os.environ.get("EMAIL_PASSWORD")))
    logger.info("PUBLIC_BASE_URL: %s", os.environ.get("PUBLIC_BASE_URL"))
    logger.info("DISABLE_GOOGLE_DRIVE: %s", os.environ.get("DISABLE_GOOGLE_DRIVE"))
    logger.info("SECRET_KEY presente: %s", bool(os.environ.get("SECRET_KEY")))
    logger.info("FLASK_SECRET_KEY presente: %s", bool(os.environ.get("FLASK_SECRET_KEY")))

logger.info("STRIPE_SECRET_KEY presente: %s", bool(os.environ.get("STRIPE_SECRET_KEY")))
logger.info("STRIPE_PUBLIC_KEY presente: %s", bool(os.environ.get("STRIPE_PUBLIC_KEY")))
logger.info("STRIPE_WEBHOOK_SECRET presente: %s", bool(os.environ.get("STRIPE_WEBHOOK_SECRET")))



try:
    _debug_env()

    logger.info("Importando create_app...")
    from app import create_app

    logger.info("Creando app Flask...")
    app = create_app()

    logger.info("App Flask creada correctamente.")
    logger.info("Rutas cargadas: %s", len(app.url_map._rules))

except Exception as exc:  # noqa: BLE001
    logger.error("ERROR CRITICO durante el arranque de la app: %s", exc)
    traceback.print_exc()
    raise


if __name__ == "__main__":
    debug_flag = (os.environ.get("FLASK_DEBUG", "0") or "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    host = (os.environ.get("FLASK_RUN_HOST") or "0.0.0.0").strip()
    port_raw = (os.environ.get("PORT") or os.environ.get("FLASK_RUN_PORT") or "5000").strip()

    try:
        port = int(port_raw)
    except ValueError:
        logger.warning("PORT invalido: %s. Usando 5000.", port_raw)
        port = 5000

    logger.info("Iniciando servidor Flask local en %s:%s", host, port)

    app.run(
        debug=debug_flag,
        use_reloader=False,
        host=host,
        port=port,
    )
