"""
Paquete principal de la aplicación Flask.

Aquí se crea la "fábrica" de la app (create_app) y se registran rutas y la base de datos.
Este patrón facilita pruebas y despliegue.
"""
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, redirect, request
from werkzeug.middleware.proxy_fix import ProxyFix

from app import db as database
from app import email_service
from app.i18n import tr
from app.routes import bp as main_bp
from app.stripe_env import ENV_FILE, load_stripe_from_disk

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_int(name: str, default: int = 0) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def create_app(test_config: Optional[dict] = None) -> Flask:
    """
    Crea y configura la instancia de Flask.

    test_config: diccionario opcional para pruebas automatizadas (sobrescribe rutas/secret).
    """
    # `override=True`: si Windows tiene STRIPE_* vacías, el `.env` del proyecto gana.
    load_dotenv(ENV_FILE, override=True)

    stripe_secret, stripe_public, stripe_webhook = load_stripe_from_disk()

    if stripe_secret:
        os.environ["STRIPE_SECRET_KEY"] = stripe_secret
    if stripe_public:
        os.environ["STRIPE_PUBLIC_KEY"] = stripe_public
    if stripe_webhook:
        os.environ["STRIPE_WEBHOOK_SECRET"] = stripe_webhook

    if not (stripe_secret and stripe_public):
        logger.warning(
            "Stripe checkout deshabilitado: faltan STRIPE_SECRET_KEY o STRIPE_PUBLIC_KEY en %s",
            ENV_FILE,
        )

    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    # Si hay reverse proxy (Nginx/Cloudflare), permite que Flask detecte HTTPS correctamente.
    proxy_hops = _env_int("TRUSTED_PROXY_COUNT", default=0)
    if proxy_hops > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_hops, x_proto=proxy_hops, x_host=proxy_hops, x_prefix=proxy_hops)

    # Carpeta instance/ para la BD SQLite (se crea si no existe)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        # Cambia SECRET_KEY en producción (cadena larga y aleatoria)
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-cambiar-en-produccion"),
        DATABASE=os.path.join(app.instance_path, "tienda.sqlite"),
        # Contraseña del panel admin (mejor definirla en variable de entorno)
        ADMIN_PASSWORD=os.environ.get("FLASK_ADMIN_PASSWORD", "admin123"),
        # Reservado; el aviso al admin por nuevo cobro va por webhook (ver email_service)
        ADMIN_NOTIFY_EMAIL=os.environ.get("ADMIN_NOTIFY_EMAIL", ""),
        MAIL_SERVER=os.environ.get("MAIL_SERVER", ""),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", "587")),
        MAIL_USE_TLS=os.environ.get("MAIL_USE_TLS", "true"),
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD", ""),
        MAIL_DEFAULT_SENDER=os.environ.get(
            "MAIL_DEFAULT_SENDER",
            os.environ.get("MAIL_USERNAME", ""),
        ),
        # Si es "1" o "true", no envía SMTP: solo escribe el cuerpo en el log (pruebas sin credenciales)
        MAIL_LOG_ONLY=os.environ.get("MAIL_LOG_ONLY", ""),
        # Endurecimiento de sesión para despliegue público.
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE=(os.environ.get("SESSION_COOKIE_SAMESITE", "Lax") or "Lax"),
        SESSION_COOKIE_SECURE=_env_bool("SESSION_COOKIE_SECURE", default=False),
        # Stripe (sandbox)
        STRIPE_SECRET_KEY=stripe_secret,
        STRIPE_PUBLIC_KEY=stripe_public,
        STRIPE_WEBHOOK_SECRET=stripe_webhook,
    )

    if test_config is not None:
        app.config.update(test_config)

    @app.after_request
    def _security_headers(resp):
        """
        Cabeceras mínimas recomendadas para despliegue público.
        (CSP deliberadamente permisiva por CDNs de Bootstrap/Google Fonts.)
        """
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "connect-src 'self' "
            "https://api.stripe.com https://r.stripe.com https://m.stripe.network https://q.stripe.com "
            "https://js.stripe.com https://hooks.stripe.com https://checkout.stripe.com; "
            "frame-src https://js.stripe.com https://hooks.stripe.com https://checkout.stripe.com; "
            "base-uri 'self'; "
            "form-action 'self' https://checkout.stripe.com https://hooks.stripe.com;",
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            hsts = (os.environ.get("HSTS_MAX_AGE") or "15552000").strip()  # 180 días por defecto
            if hsts.isdigit() and int(hsts) > 0:
                resp.headers.setdefault("Strict-Transport-Security", f"max-age={int(hsts)}; includeSubDomains")
        return resp

    @app.before_request
    def _force_https_if_configured():
        if not _env_bool("ENFORCE_HTTPS", default=False):
            return None
        if request.is_secure:
            return None
        proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        if proto == "https":
            return None
        target = request.url.replace("http://", "https://", 1)
        return redirect(target, code=301)

    # Inicializar tablas SQLite
    with app.app_context():
        database.init_app(app)

    @app.context_processor
    def inject_i18n_context():
        return {
            "t": tr,
            "support_email": email_service.get_email_sender(),
        }

    # Validaciones de seguridad para producción (no bloquean arranque).
    if app.config.get("SECRET_KEY") == "dev-cambiar-en-produccion":
        logger.warning("SECRET_KEY en valor por defecto; cambia este valor para despliegue público.")
    if app.config.get("ADMIN_PASSWORD") == "admin123":
        logger.warning("FLASK_ADMIN_PASSWORD en valor por defecto; cambia la contraseña del panel admin.")
    if not (os.environ.get("EMAIL_SENDER") or "").strip():
        logger.warning("EMAIL_SENDER no definido en .env; se usará valor por defecto del código.")
    if not (os.environ.get("ADMIN_EMAIL") or "").strip():
        logger.warning("ADMIN_EMAIL no definido en .env; se usará valor por defecto del código.")

    # Rutas públicas y de administración
    app.register_blueprint(main_bp)

    return app


