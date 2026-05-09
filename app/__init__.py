import os
import logging
from flask import Flask

from app import db as database

logger = logging.getLogger(__name__)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


_TRANSLATIONS = {
    "footer.product": "Mapa del Alma – El Nombre Que Me Habita",
    "footer.rights": "Todos los derechos reservados.",
    "footer.privacy": "Privacidad",
    "footer.terms": "Condiciones",
    "footer.contact": "Contacto",
    "nav.home": "Inicio",
    "nav.order": "Crear mi Mapa",
    "nav.contact": "Contacto",
    "product.name": "Mapa del Alma",
    "site.name": "El Nombre Que Me Habita",
}


def _install_template_helpers(app: Flask) -> None:
    """
    Registra helpers globales para Jinja.

    Muchos templates usan:
        {{ t('footer.product') }}

    Si no registramos `t`, Flask lanza:
        jinja2.exceptions.UndefinedError: 't' is undefined
    """

    def t(key: str, default: str | None = None) -> str:
        if key is None:
            return ""
        key_str = str(key)
        return _TRANSLATIONS.get(key_str, default if default is not None else key_str)

    app.jinja_env.globals["t"] = t

    @app.context_processor
    def inject_template_helpers():
        return {
            "t": t,
            "site_name": "El Nombre Que Me Habita",
            "product_name": "Mapa del Alma",
            "public_base_url": app.config.get("PUBLIC_BASE_URL", ""),
        }


def create_app():
    logger.info("Creando la app Flask...")

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    secret_key = (
        os.getenv("SECRET_KEY")
        or os.getenv("FLASK_SECRET_KEY")
        or "dev-secret-key-change-me"
    )

    app.config["SECRET_KEY"] = secret_key
    app.config["ADMIN_PASSWORD"] = os.getenv(
        "FLASK_ADMIN_PASSWORD",
        os.getenv("ADMIN_PASSWORD", "")
    )

    app.config["PUBLIC_BASE_URL"] = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

    app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
    app.config["OPENAI_MODEL"] = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    app.config["OPENAI_ENABLE_REAL_ORDERS"] = _bool_env(
        "OPENAI_ENABLE_REAL_ORDERS",
        False,
    )

    app.config["EMAIL_PASSWORD"] = os.getenv("EMAIL_PASSWORD", "")
    app.config["EMAIL_SENDER"] = os.getenv("EMAIL_SENDER", "")
    app.config["ADMIN_EMAIL"] = os.getenv("ADMIN_EMAIL", "")

    app.config["STRIPE_PUBLIC_KEY"] = os.getenv(
        "STRIPE_PUBLIC_KEY",
        os.getenv("STRIPE_PUBLISHABLE_KEY", ""),
    )
    app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY", "")
    app.config["STRIPE_WEBHOOK_SECRET"] = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    app.config["DISABLE_GOOGLE_DRIVE"] = _bool_env("DISABLE_GOOGLE_DRIVE", False)

    app.config["DATABASE"] = os.getenv(
        "SQLITE_DATABASE_PATH",
        os.path.join(app.instance_path, "mapa_del_alma.sqlite"),
    )

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        logger.exception("No se pudo crear instance_path.")

    _install_template_helpers(app)

    # MUY IMPORTANTE:
    # No ejecutar init_db() aquí. La base de datos se inicializa diferida
    # en la primera petición para que Render pueda abrir el puerto rápido.
    try:
        database.init_app(app)
        logger.info("Base de datos registrada para inicialización diferida.")
    except Exception as e:
        logger.exception("Error registrando inicialización de base de datos: %s", e)
        raise

    # Registrar rutas reales de la tienda.
    try:
        from app.routes import bp as main_bp
        app.register_blueprint(main_bp)
        logger.info("Blueprint principal registrado correctamente: app.routes.bp")
    except Exception as e:
        logger.exception("Error registrando blueprint principal app.routes.bp: %s", e)
        raise

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    logger.info("App Flask creada correctamente. Rutas cargadas: %s", len(app.url_map._rules))

    return app
