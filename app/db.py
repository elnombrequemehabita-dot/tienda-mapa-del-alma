import os
import sqlite3
import logging
import threading
from flask import current_app, g

logger = logging.getLogger(__name__)

_db_init_lock = threading.Lock()


def _database_url():
    return os.getenv("DATABASE_URL")


def _use_postgres():
    return bool(_database_url())


def get_db():
    if "db" in g:
        return g.db

    if _use_postgres():
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(_database_url())
        conn.autocommit = False
        g.db = conn
        return g.db

    db_path = current_app.config.get("DATABASE") or os.path.join(
        current_app.instance_path, "mapa_del_alma.sqlite"
    )
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    g.db = conn
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            logger.exception("Error cerrando conexión de base de datos.")


def execute(sql, params=None):
    db = get_db()
    cur = db.cursor()
    cur.execute(sql, params or ())
    return cur


def commit():
    db = get_db()
    db.commit()


def rollback():
    db = get_db()
    db.rollback()


def init_db():
    """
    Inicialización mínima y segura.
    """

    db = get_db()

    if _use_postgres():
        cur = db.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                apellidos TEXT,
                email TEXT,
                fecha_nacimiento TEXT,
                sexo TEXT,
                producto TEXT,
                estado TEXT DEFAULT 'pendiente_pago',
                stripe_session_id TEXT,
                stripe_payment_intent TEXT,
                pdf_path TEXT,
                drive_file_id TEXT,
                drive_view_link TEXT,
                drive_download_link TEXT,
                error TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pedidos_estado
            ON pedidos (estado);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pedidos_stripe_session_id
            ON pedidos (stripe_session_id);
        """)

        db.commit()
        logger.info("Tablas PostgreSQL verificadas correctamente.")
        return

    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            apellidos TEXT,
            email TEXT,
            fecha_nacimiento TEXT,
            sexo TEXT,
            producto TEXT,
            estado TEXT DEFAULT 'pendiente_pago',
            stripe_session_id TEXT,
            stripe_payment_intent TEXT,
            pdf_path TEXT,
            drive_file_id TEXT,
            drive_view_link TEXT,
            drive_download_link TEXT,
            error TEXT,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_pedidos_estado
        ON pedidos (estado);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_pedidos_stripe_session_id
        ON pedidos (stripe_session_id);
    """)

    db.commit()
    logger.info("Tablas SQLite verificadas correctamente.")


def init_app(app):
    app.teardown_appcontext(close_db)

    app.extensions.setdefault("mapa_del_alma", {})
    app.extensions["mapa_del_alma"].setdefault("db_initialized", False)

    @app.before_request
    def _lazy_init_db():
        state = app.extensions.setdefault("mapa_del_alma", {})

        if state.get("db_initialized"):
            return None

        with _db_init_lock:
            if state.get("db_initialized"):
                return None

            logger.info("Inicializando base de datos en primera petición...")

            try:
                init_db()
                state["db_initialized"] = True
                logger.info("Base de datos inicializada correctamente.")
            except Exception as e:
                logger.exception("Error inicializando base de datos: %s", e)
                raise

        return None
