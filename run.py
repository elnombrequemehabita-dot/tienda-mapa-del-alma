"""
Punto de entrada para ejecutar la tienda en desarrollo.

Uso en PowerShell (desde la carpeta del proyecto):
    python run.py

En producción se recomienda un servidor WSGI (waitress, gunicorn, etc.).
"""
import logging
import os

from app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

app = create_app()

if __name__ == "__main__":
    # Configurable por variables de entorno para desarrollo o producción.
    debug_flag = (os.environ.get("FLASK_DEBUG", "0") or "0").strip().lower() in ("1", "true", "yes", "on")
    host = (os.environ.get("FLASK_RUN_HOST") or "0.0.0.0").strip()
    port_raw = (os.environ.get("PORT") or os.environ.get("FLASK_RUN_PORT") or "5000").strip()
    try:
        port = int(port_raw)
    except ValueError:
        port = 5000

    # use_reloader=False evita reinicios por falsos positivos del watcher en Windows
    app.run(debug=debug_flag, use_reloader=False, host=host, port=port)
