import logging
from flask import Flask

from app import db as database

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "change-this"

    try:
        database.init_app(app)
        logger.info("Base de datos registrada para inicialización diferida.")
    except Exception as e:
        logger.exception(
            "Error registrando inicialización de base de datos: %s",
            e
        )
        raise

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
