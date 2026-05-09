import os
import sqlite3
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from flask import current_app, g

from app.order_states import ESTADO_PENDIENTE_PAGO

logger = logging.getLogger(__name__)

_db_init_lock = threading.Lock()

RESENA_ESTADO_PENDIENTE = "pendiente"
RESENA_ESTADO_APROBADA = "aprobada"
RESENA_ESTADO_RECHAZADA = "rechazada"


# ============================================================
# Conexión
# ============================================================

def _database_url() -> str:
    """
    DATABASE_URL limpia. Render/Supabase usan postgresql://...
    """
    return (os.getenv("DATABASE_URL") or "").strip()


def _use_postgres() -> bool:
    """
    True solo cuando DATABASE_URL apunta a PostgreSQL.
    Evita confundir cualquier valor raro con una conexión Postgres.
    """
    url = _database_url().lower()
    return url.startswith("postgresql://") or url.startswith("postgres://")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    if "db" in g:
        return g.db

    if _use_postgres():
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(
            _database_url(),
            cursor_factory=psycopg2.extras.RealDictCursor,
            connect_timeout=20,
        )
        conn.autocommit = False
        g.db = conn
        return conn

    db_path = current_app.config.get("DATABASE") or os.path.join(
        current_app.instance_path,
        "mapa_del_alma.sqlite",
    )
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    g.db = conn
    return conn


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            logger.exception("Error cerrando conexión de base de datos.")


def _q(sql: str) -> str:
    """
    Adaptador simple de placeholders.
    El código interno usa ?; PostgreSQL necesita %s.

    IMPORTANTE:
    En Render con Supabase/PostgreSQL, psycopg2 NO acepta ?.
    Esta función fuerza la conversión cuando DATABASE_URL es PostgreSQL
    y también cuando la conexión actual ya es psycopg2.
    """
    if _use_postgres():
        return sql.replace("?", "%s")

    try:
        db_obj = g.get("db")
        if db_obj is not None and db_obj.__class__.__module__.startswith("psycopg2"):
            return sql.replace("?", "%s")
    except Exception:
        pass

    return sql


def _execute(sql: str, params: Iterable[Any] | None = None):
    db = get_db()
    cur = db.cursor()
    cur.execute(_q(sql), tuple(params or ()))
    return cur


def _fetchone(sql: str, params: Iterable[Any] | None = None):
    cur = _execute(sql, params)
    return cur.fetchone()


def _fetchall(sql: str, params: Iterable[Any] | None = None):
    cur = _execute(sql, params)
    return cur.fetchall()


def _commit() -> None:
    get_db().commit()


def _rollback() -> None:
    get_db().rollback()


def execute(sql: str, params: Iterable[Any] | None = None):
    return _execute(sql, params)


def commit() -> None:
    _commit()


def rollback() -> None:
    _rollback()


def _last_insert_id(cur) -> int:
    if _use_postgres():
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("No se pudo obtener el ID insertado.")
        return int(row["id"])
    return int(cur.lastrowid)


# ============================================================
# Inicialización / migración ligera
# ============================================================

def _add_column_if_missing_sqlite(table: str, column: str, definition: str) -> None:
    rows = _fetchall(f"PRAGMA table_info({table})")
    existing = {row["name"] for row in rows}
    if column not in existing:
        _execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _add_column_if_missing_postgres(table: str, column: str, definition: str) -> None:
    _execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")


def _add_column_if_missing(table: str, column: str, sqlite_def: str, postgres_def: str | None = None) -> None:
    if _use_postgres():
        _add_column_if_missing_postgres(table, column, postgres_def or sqlite_def)
    else:
        _add_column_if_missing_sqlite(table, column, sqlite_def)


def init_db() -> None:
    """
    Crea/ajusta tablas mínimas necesarias para tienda, admin, reseñas y notificaciones.
    Esta función se ejecuta con lazy init en la primera petición, NO durante el arranque.
    """

    if _use_postgres():
        _execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                apellidos TEXT,
                email TEXT,
                fecha_nacimiento TEXT,
                sexo TEXT,
                forma_trato TEXT,
                producto TEXT DEFAULT 'mapa_alma',
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
            )
        """)

        _execute("""
            CREATE TABLE IF NOT EXISTS notificaciones (
                id SERIAL PRIMARY KEY,
                pedido_id INTEGER,
                tipo TEXT,
                canal TEXT,
                destinatario TEXT,
                estado TEXT,
                error_message TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        _execute("""
            CREATE TABLE IF NOT EXISTS resenas (
                id SERIAL PRIMARY KEY,
                pedido_id INTEGER,
                nombre_cliente TEXT,
                email_cliente TEXT,
                rating INTEGER,
                comentario TEXT,
                estado TEXT DEFAULT 'pendiente',
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migraciones ligeras por si la tabla ya existía incompleta.
        _add_column_if_missing("pedidos", "sexo", "TEXT")
        _add_column_if_missing("pedidos", "forma_trato", "TEXT")
        _add_column_if_missing("pedidos", "producto", "TEXT DEFAULT 'mapa_alma'")
        _add_column_if_missing("pedidos", "stripe_session_id", "TEXT")
        _add_column_if_missing("pedidos", "stripe_payment_intent", "TEXT")
        _add_column_if_missing("pedidos", "pdf_path", "TEXT")
        _add_column_if_missing("pedidos", "drive_file_id", "TEXT")
        _add_column_if_missing("pedidos", "drive_view_link", "TEXT")
        _add_column_if_missing("pedidos", "drive_download_link", "TEXT")
        _add_column_if_missing("pedidos", "error", "TEXT")
        _add_column_if_missing("pedidos", "actualizado_en", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    else:
        _execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                apellidos TEXT,
                email TEXT,
                fecha_nacimiento TEXT,
                sexo TEXT,
                forma_trato TEXT,
                producto TEXT DEFAULT 'mapa_alma',
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
            )
        """)

        _execute("""
            CREATE TABLE IF NOT EXISTS notificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                tipo TEXT,
                canal TEXT,
                destinatario TEXT,
                estado TEXT,
                error_message TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        _execute("""
            CREATE TABLE IF NOT EXISTS resenas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                nombre_cliente TEXT,
                email_cliente TEXT,
                rating INTEGER,
                comentario TEXT,
                estado TEXT DEFAULT 'pendiente',
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        _add_column_if_missing("pedidos", "sexo", "TEXT")
        _add_column_if_missing("pedidos", "forma_trato", "TEXT")
        _add_column_if_missing("pedidos", "producto", "TEXT DEFAULT 'mapa_alma'")
        _add_column_if_missing("pedidos", "stripe_session_id", "TEXT")
        _add_column_if_missing("pedidos", "stripe_payment_intent", "TEXT")
        _add_column_if_missing("pedidos", "pdf_path", "TEXT")
        _add_column_if_missing("pedidos", "drive_file_id", "TEXT")
        _add_column_if_missing("pedidos", "drive_view_link", "TEXT")
        _add_column_if_missing("pedidos", "drive_download_link", "TEXT")
        _add_column_if_missing("pedidos", "error", "TEXT")
        _add_column_if_missing("pedidos", "actualizado_en", "TEXT DEFAULT CURRENT_TIMESTAMP")

    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos (estado)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_email ON pedidos (email)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_stripe_session_id ON pedidos (stripe_session_id)")
    _execute("CREATE INDEX IF NOT EXISTS idx_resenas_estado ON resenas (estado)")
    _execute("CREATE INDEX IF NOT EXISTS idx_resenas_pedido_id ON resenas (pedido_id)")
    _execute("CREATE INDEX IF NOT EXISTS idx_notificaciones_pedido_id ON notificaciones (pedido_id)")

    _commit()
    logger.info("Tablas %s verificadas correctamente.", "PostgreSQL" if _use_postgres() else "SQLite")


def init_app(app) -> None:
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


# ============================================================
# Pedidos
# ============================================================

def insert_pedido(
    nombre: str,
    apellidos: str,
    email: str,
    fecha_nacimiento: Optional[str] = None,
    sexo: Optional[str] = None,
    forma_trato: Optional[str] = None,
    producto: str = "mapa_alma",
    estado: str = ESTADO_PENDIENTE_PAGO,
) -> int:
    sql = """
        INSERT INTO pedidos (
            nombre, apellidos, email, fecha_nacimiento, sexo, forma_trato,
            producto, estado, creado_en, actualizado_en
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
    if _use_postgres():
        sql += " RETURNING id"

    cur = _execute(
        sql,
        (nombre, apellidos, email, fecha_nacimiento, sexo, forma_trato, producto, estado),
    )
    pedido_id = _last_insert_id(cur)
    _commit()
    return pedido_id


def get_pedido_by_id(pedido_id: int):
    return _fetchone("SELECT * FROM pedidos WHERE id = ?", (int(pedido_id),))


def get_pedido_pendiente_por_email(email: str):
    return _fetchone(
        """
        SELECT *
        FROM pedidos
        WHERE lower(email) = lower(?)
          AND estado = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (email, ESTADO_PENDIENTE_PAGO),
    )


def list_pedidos_por_estados(estados: Iterable[str], limit: int = 500):
    estados = tuple(estados)
    if not estados:
        return []

    placeholders = ",".join(["?"] * len(estados))
    return _fetchall(
        f"""
        SELECT *
        FROM pedidos
        WHERE estado IN ({placeholders})
        ORDER BY id DESC
        LIMIT ?
        """,
        (*estados, int(limit)),
    )


def list_pedidos(limit: int = 500):
    return _fetchall(
        "SELECT * FROM pedidos ORDER BY id DESC LIMIT ?",
        (int(limit),),
    )


def update_pedido_campos(
    pedido_id: int,
    clear_error: bool = False,
    **campos: Any,
) -> int:
    allowed = {
        "nombre",
        "apellidos",
        "email",
        "fecha_nacimiento",
        "sexo",
        "forma_trato",
        "producto",
        "estado",
        "stripe_session_id",
        "stripe_payment_intent",
        "pdf_path",
        "drive_file_id",
        "drive_view_link",
        "drive_download_link",
        "error",
    }

    updates: list[str] = []
    values: list[Any] = []

    for key, value in campos.items():
        if key in allowed:
            updates.append(f"{key} = ?")
            values.append(value)

    if clear_error:
        updates.append("error = NULL")

    updates.append("actualizado_en = CURRENT_TIMESTAMP")

    if not updates:
        return 0

    values.append(int(pedido_id))
    cur = _execute(
        f"UPDATE pedidos SET {', '.join(updates)} WHERE id = ?",
        values,
    )
    _commit()
    return int(cur.rowcount or 0)


def update_estado_pedido(pedido_id: int, estado: str, error: Optional[str] = None) -> int:
    return update_pedido_campos(
        pedido_id,
        estado=estado,
        error=error,
        clear_error=(error is None),
    )


def marcar_pedido_pagado(
    pedido_id: int,
    stripe_checkout_session_id: Optional[str] = None,
    stripe_payment_intent: Optional[str] = None,
) -> int:
    return update_pedido_campos(
        pedido_id,
        estado="pagado",
        stripe_session_id=stripe_checkout_session_id,
        stripe_payment_intent=stripe_payment_intent,
        clear_error=True,
    )


def guardar_pdf_pedido(
    pedido_id: int,
    pdf_path: Optional[str] = None,
    drive_file_id: Optional[str] = None,
    drive_view_link: Optional[str] = None,
    drive_download_link: Optional[str] = None,
    estado: str = "pdf_generado",
) -> int:
    return update_pedido_campos(
        pedido_id,
        estado=estado,
        pdf_path=pdf_path,
        drive_file_id=drive_file_id,
        drive_view_link=drive_view_link,
        drive_download_link=drive_download_link,
        clear_error=True,
    )


def delete_pedido(pedido_id: int) -> int:
    _execute("DELETE FROM notificaciones WHERE pedido_id = ?", (int(pedido_id),))
    _execute("DELETE FROM resenas WHERE pedido_id = ?", (int(pedido_id),))
    cur = _execute("DELETE FROM pedidos WHERE id = ?", (int(pedido_id),))
    _commit()
    return int(cur.rowcount or 0)


def codigo_confirmacion_pedido(pedido_id: int) -> str:
    return f"MAPA-{int(pedido_id):06d}"


# ============================================================
# Notificaciones
# ============================================================

def insert_notificacion(
    pedido_id: int,
    tipo: str,
    canal: str,
    destinatario: str,
    estado: str,
    error_message: Optional[str] = None,
) -> int:
    sql = """
        INSERT INTO notificaciones (
            pedido_id, tipo, canal, destinatario, estado, error_message, creado_en
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """
    if _use_postgres():
        sql += " RETURNING id"

    cur = _execute(
        sql,
        (int(pedido_id), tipo, canal, destinatario, estado, error_message),
    )
    nid = _last_insert_id(cur)
    _commit()
    return nid


def list_notificaciones_pedido(pedido_id: int, limit: int = 200):
    return _fetchall(
        """
        SELECT *
        FROM notificaciones
        WHERE pedido_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(pedido_id), int(limit)),
    )


# ============================================================
# Reseñas
# ============================================================

def insert_resena(
    pedido_id: int,
    nombre_cliente: str,
    email_cliente: str,
    rating: int,
    comentario: str,
    estado: str = RESENA_ESTADO_PENDIENTE,
) -> int:
    sql = """
        INSERT INTO resenas (
            pedido_id, nombre_cliente, email_cliente, rating, comentario,
            estado, creado_en, actualizado_en
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
    if _use_postgres():
        sql += " RETURNING id"

    cur = _execute(
        sql,
        (
            int(pedido_id),
            nombre_cliente,
            email_cliente,
            int(rating),
            comentario,
            estado,
        ),
    )
    rid = _last_insert_id(cur)
    _commit()
    return rid


def get_resena_by_id(resena_id: int):
    return _fetchone("SELECT * FROM resenas WHERE id = ?", (int(resena_id),))


def update_resena_estado(resena_id: int, estado: str) -> int:
    cur = _execute(
        """
        UPDATE resenas
        SET estado = ?, actualizado_en = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (estado, int(resena_id)),
    )
    _commit()
    return int(cur.rowcount or 0)


def delete_resena(resena_id: int) -> int:
    cur = _execute("DELETE FROM resenas WHERE id = ?", (int(resena_id),))
    _commit()
    return int(cur.rowcount or 0)


def list_resenas_admin(limit: int = 300):
    return _fetchall(
        """
        SELECT r.*, p.nombre AS pedido_nombre, p.apellidos AS pedido_apellidos, p.email AS pedido_email
        FROM resenas r
        LEFT JOIN pedidos p ON p.id = r.pedido_id
        ORDER BY r.id DESC
        LIMIT ?
        """,
        (int(limit),),
    )


def list_resenas_aprobadas_todas():
    return _fetchall(
        """
        SELECT *
        FROM resenas
        WHERE estado = ?
        ORDER BY id DESC
        """,
        (RESENA_ESTADO_APROBADA,),
    )


def resumen_resenas_aprobadas() -> tuple[int, float]:
    row = _fetchone(
        """
        SELECT COUNT(*) AS total, AVG(rating) AS promedio
        FROM resenas
        WHERE estado = ?
        """,
        (RESENA_ESTADO_APROBADA,),
    )
    if not row:
        return 0, 0.0
    total = row["total"] or 0
    promedio = row["promedio"] or 0.0
    return int(total), float(promedio)


def resena_bloquea_nuevo_envio(pedido_id: int) -> bool:
    row = _fetchone(
        """
        SELECT id
        FROM resenas
        WHERE pedido_id = ?
          AND estado IN (?, ?)
        LIMIT 1
        """,
        (int(pedido_id), RESENA_ESTADO_PENDIENTE, RESENA_ESTADO_APROBADA),
    )
    return row is not None


# ============================================================
# Utilidades para servicios
# ============================================================

def actualizar_estado_si_actual(
    pedido_id: int,
    estado_actual: str,
    estado_nuevo: str,
    error: Optional[str] = None,
) -> int:
    cur = _execute(
        """
        UPDATE pedidos
        SET estado = ?, error = ?, actualizado_en = CURRENT_TIMESTAMP
        WHERE id = ? AND estado = ?
        """,
        (estado_nuevo, error, int(pedido_id), estado_actual),
    )
    _commit()
    return int(cur.rowcount or 0)


def pedidos_atascados_en_estado(estados: Iterable[str], antes_de_iso: Optional[str] = None, limit: int = 100):
    estados = tuple(estados)
    if not estados:
        return []
    placeholders = ",".join(["?"] * len(estados))

    # Comparación simple por timestamp SQL. Si no se pasa fecha, devuelve por estado.
    if antes_de_iso:
        return _fetchall(
            f"""
            SELECT *
            FROM pedidos
            WHERE estado IN ({placeholders})
              AND actualizado_en < ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (*estados, antes_de_iso, int(limit)),
        )

    return _fetchall(
        f"""
        SELECT *
        FROM pedidos
        WHERE estado IN ({placeholders})
        ORDER BY id ASC
        LIMIT ?
        """,
        (*estados, int(limit)),
    )
