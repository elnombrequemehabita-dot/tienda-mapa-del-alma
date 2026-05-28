import os
import logging
import threading
import time
from flask import Flask, redirect, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from app import db as database

logger = logging.getLogger(__name__)

_drive_cleanup_lock = threading.Lock()
_drive_cleanup_last_started = 0.0


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _int_env(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


TRANSLATIONS_ES = {
    "site.name": "El Nombre Que Me Habita",
    "footer.product": "Mapa del Alma – El Nombre Que Me Habita",
    "footer.rights": "Todos los derechos reservados.",
    "footer.privacy": "Privacidad",
    "footer.terms": "Condiciones",
    "footer.contact": "Contacto",

    "nav.home": "Inicio",
    "nav.reviews": "Reseñas",
    "nav.cta": "Comprar ahora",
    "nav.order": "Crear mi Mapa",
    "nav.contact": "Contacto",

    "ticker.top": "Mapa del Alma personalizado · Entrega digital por email · Pago seguro con Stripe · Tu historia, escrita solo para ti",
    "ticker.bottom": "Producto digital personalizado · Link de descarga activo por 48 horas · Revisa bien tus datos antes de comprar",

    "index.title": "Mapa del Alma personalizado · El Nombre Que Me Habita",
    "index.hero.price.name": "Mapa del Alma personalizado",
    "index.reviews.title": "Lo que dicen quienes ya lo tienen",
    "index.reviews.lead": "Reseñas verificadas de clientes que ya recibieron su Mapa del Alma.",
    "index.reviews.empty": "Aún no hay reseñas publicadas. En cuanto revisemos las primeras, aparecerán aquí.",
    "index.reviews.verified_order": "Pedido verificado",

    "pedido.title": "Pedido · Mapa del Alma",
    "pedido.header": "Crear mi Mapa del Alma",
    "pedido.intro": "Completa tus datos con cuidado. Tu Mapa del Alma se crea de forma personalizada y se enviará al correo que escribas aquí.",
    "pedido.name": "Tu nombre",
    "pedido.name_placeholder": "Ejemplo: Yanelis",
    "pedido.lastname": "Tus apellidos",
    "pedido.lastname_placeholder": "Ejemplo: León García",
    "pedido.email": "Correo electrónico",
    "pedido.email_placeholder": "tu@correo.com",
    "pedido.email_confirm": "Confirma tu correo electrónico",
    "pedido.email_confirm_placeholder": "Repite tu correo",
    "pedido.birthdate": "Fecha de nacimiento",
    "pedido.optional": "opcional",
    "pedido.birthdate_placeholder": "mm/dd/aaaa",
    "pedido.form_of_address": "¿Cómo deseas que te hablemos en la lectura?",
    "pedido.form_of_address_optional": "opcional",
    "pedido.form_of_address_placeholder": "Selecciona una opción",
    "pedido.confirm_data": "Confirmo que revisé mi nombre, apellidos, fecha de nacimiento y correo. Entiendo que estos datos se usarán para crear mi contenido personalizado.",
    "pedido.confirm_digital": "Acepto que es un producto digital personalizado. Entiendo que el enlace de descarga estará activo por 48 horas y que luego el PDF se eliminará de Google Drive por seguridad y privacidad. Una vez iniciado el proceso de creación, no se realizan cambios, cancelaciones ni reembolsos.",
    "pedido.submit": "Continuar al pago seguro",
    "pedido.back": "Volver al inicio",
    "pedido.terms": "Términos y condiciones",
    "pedido.privacy": "Política de privacidad",
    "pedido.digital_notice": "Producto digital personalizado · Entrega por email · Link activo por 48 horas",
    "pedido.secure_payment": "Pago seguro con Stripe",
    "pedido.required_note": "Los campos obligatorios deben completarse correctamente antes de continuar.",
    "pedido.no_refund_notice": "Por ser una creación personalizada, revisa bien tus datos antes de pagar.",

    "pedido.full_name": "Nombre completo",
    "pedido.apellidos": "Apellidos",
    "pedido.fecha_nacimiento": "Fecha de nacimiento",
    "pedido.forma_trato": "Tratamiento",
    "pedido.acepta": "Confirmo que mis datos están correctos.",
    "pedido.acepta_digital": "Acepto las condiciones del producto digital personalizado.",
    "pedido.cta": "Continuar al pago seguro",
    "pedido.cancel": "Volver al inicio",

    "legal.privacy.title": "Política de privacidad",
    "legal.terms.title": "Condiciones del servicio",
    "legal.contact.title": "Contacto",
}


def _load_project_translations() -> dict:
    merged = dict(TRANSLATIONS_ES)
    try:
        from app import i18n  # type: ignore

        for attr in ("TRANSLATIONS", "translations", "I18N", "MESSAGES"):
            data = getattr(i18n, attr, None)
            if isinstance(data, dict):
                es_data = data.get("es") if hasattr(data, "get") else None
                if isinstance(es_data, dict):
                    for key, value in es_data.items():
                        if isinstance(value, str):
                            merged[str(key)] = value

                for key, value in data.items():
                    if isinstance(value, dict) and "es" in value:
                        merged[str(key)] = str(value["es"])
                    elif isinstance(value, str):
                        merged[str(key)] = value
    except Exception:
        logger.info("No se pudieron cargar traducciones desde app.i18n; usando fallback local.")

    # Estas claves críticas ganan siempre para evitar nav.cta, ticker.top, pedido.header, etc.
    merged.update(TRANSLATIONS_ES)
    return merged


def _install_template_helpers(app: Flask) -> None:
    translations = _load_project_translations()

    def t(key: str, default: str | None = None) -> str:
        if key is None:
            return ""
        key_str = str(key)
        value = translations.get(key_str)
        if value is not None:
            return value
        return default if default is not None else key_str

    app.jinja_env.globals["t"] = t

    @app.context_processor
    def inject_template_helpers():
        support_email = (
            os.getenv("EMAIL_SENDER")
            or os.getenv("ADMIN_EMAIL")
            or "elnombrequemehabita@gmail.com"
        )
        return {
            "t": t,
            "site_name": t("site.name"),
            "product_name": "Mapa del Alma",
            "support_email": support_email,
            "public_base_url": app.config.get("PUBLIC_BASE_URL", ""),
        }


def _install_drive_cleanup_scheduler(app: Flask) -> None:
    cleanup_default = bool((os.getenv("DATABASE_URL") or "").strip())
    if not _bool_env("DRIVE_CLEANUP_ON_REQUEST", cleanup_default):
        return

    interval_seconds = max(300, _int_env("DRIVE_CLEANUP_INTERVAL_SECONDS", 3600))

    @app.before_request
    def _maybe_schedule_drive_cleanup():
        global _drive_cleanup_last_started

        if app.config.get("DISABLE_GOOGLE_DRIVE"):
            return None

        now = time.time()
        if now - _drive_cleanup_last_started < interval_seconds:
            return None

        with _drive_cleanup_lock:
            if now - _drive_cleanup_last_started < interval_seconds:
                return None
            _drive_cleanup_last_started = now

        def _run_cleanup() -> None:
            with app.app_context():
                try:
                    database.init_db()
                    from app.drive_cleanup import limpiar_drive_expirados

                    limpiar_drive_expirados(limit=200, enviar_resumen=True)
                except Exception:
                    logger.exception("Limpieza automática de Drive falló.")

        threading.Thread(target=_run_cleanup, name="drive-cleanup-48h", daemon=True).start()
        return None


def create_app():
    logger.info("Creando la app Flask...")

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    trusted_proxy_count = _int_env("TRUSTED_PROXY_COUNT", 0)
    if trusted_proxy_count > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=trusted_proxy_count,
            x_proto=trusted_proxy_count,
            x_host=trusted_proxy_count,
            x_port=trusted_proxy_count,
            x_prefix=trusted_proxy_count,
        )

    session_cookie_secure = _bool_env("SESSION_COOKIE_SECURE", False)
    app.config.update(
        SESSION_COOKIE_SECURE=session_cookie_secure,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PREFERRED_URL_SCHEME="https" if session_cookie_secure else "http",
        MAX_CONTENT_LENGTH=_int_env("MAX_CONTENT_LENGTH", 1_000_000),
    )

    if _bool_env("ENFORCE_HTTPS", False):
        @app.before_request
        def _redirect_http_to_https():
            if request.is_secure:
                return None
            if request.method not in {"GET", "HEAD"}:
                return None
            url = request.url.replace("http://", "https://", 1)
            return redirect(url, code=301)

    hsts_max_age = _int_env("HSTS_MAX_AGE", 0)
    if session_cookie_secure and hsts_max_age > 0:
        @app.after_request
        def _add_hsts_header(response):
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={hsts_max_age}; includeSubDomains",
            )
            return response

    secret_key = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY")
    if not secret_key:
        if app.debug or _bool_env("ALLOW_DEV_SECRET_KEY", False):
            secret_key = "dev-secret-key-change-me"
            logger.warning("Usando SECRET_KEY de desarrollo. No usar esto en producción.")
        else:
            raise RuntimeError(
                "Falta SECRET_KEY/FLASK_SECRET_KEY. Por seguridad la app no arranca sin clave secreta."
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
        os.path.join(app.instance_path, "tienda.sqlite"),
    )

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        logger.exception("No se pudo crear instance_path.")

    _install_template_helpers(app)

    try:
        database.init_app(app)
        _install_drive_cleanup_scheduler(app)
        logger.info("Base de datos registrada para inicialización diferida.")
    except Exception as e:
        logger.exception("Error registrando inicialización de base de datos: %s", e)
        raise

    try:
        from app.routes import bp as main_bp
        app.register_blueprint(main_bp)
        logger.info("Blueprint principal registrado correctamente: app.routes.bp")
    except Exception as e:
        logger.exception("Error registrando blueprint principal app.routes.bp: %s", e)
        raise



    # Páginas editoriales premium separadas.
    # Esto evita una home demasiado larga y mantiene la navegación siempre a mano.
    @app.route("/que-es")
    def que_es():
        return render_template("que_es.html")

    @app.route("/vista-previa")
    def vista_previa():
        return render_template("vista_previa.html")

    @app.route("/incluye")
    def incluye():
        return render_template("incluye.html")

    @app.route("/preguntas")
    def preguntas():
        return render_template("preguntas.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    logger.info("App Flask creada correctamente. Rutas cargadas: %s", len(app.url_map._rules))

    return app
