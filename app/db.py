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
                drive_uploaded_at TIMESTAMP,
                drive_expires_at TIMESTAMP,
                drive_deleted_at TIMESTAMP,
                drive_status TEXT DEFAULT 'none',
                drive_delete_error TEXT,
                processing_lock INTEGER DEFAULT 0,
                processing_started_at TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
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
        _add_column_if_missing("pedidos", "drive_uploaded_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "drive_expires_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "drive_deleted_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "drive_status", "TEXT DEFAULT 'none'")
        _add_column_if_missing("pedidos", "drive_delete_error", "TEXT")
        _add_column_if_missing("pedidos", "processing_lock", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "processing_started_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "retry_count", "INTEGER DEFAULT 0")
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
                drive_uploaded_at TEXT,
                drive_expires_at TEXT,
                drive_deleted_at TEXT,
                drive_status TEXT DEFAULT 'none',
                drive_delete_error TEXT,
                processing_lock INTEGER DEFAULT 0,
                processing_started_at TEXT,
                retry_count INTEGER DEFAULT 0,
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
        _add_column_if_missing("pedidos", "drive_uploaded_at", "TEXT")
        _add_column_if_missing("pedidos", "drive_expires_at", "TEXT")
        _add_column_if_missing("pedidos", "drive_deleted_at", "TEXT")
        _add_column_if_missing("pedidos", "drive_status", "TEXT DEFAULT 'none'")
        _add_column_if_missing("pedidos", "drive_delete_error", "TEXT")
        _add_column_if_missing("pedidos", "processing_lock", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "processing_started_at", "TEXT")
        _add_column_if_missing("pedidos", "retry_count", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "error", "TEXT")
        _add_column_if_missing("pedidos", "actualizado_en", "TEXT DEFAULT CURRENT_TIMESTAMP")

    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos (estado)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_email ON pedidos (email)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_stripe_session_id ON pedidos (stripe_session_id)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_drive_expires_at ON pedidos (drive_expires_at)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_processing_lock ON pedidos (processing_lock)")
    try:
        _execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pedidos_stripe_session_unique ON pedidos (stripe_session_id) WHERE stripe_session_id IS NOT NULL AND stripe_session_id <> ''")
    except Exception:
        logger.warning("No se pudo crear índice único de stripe_session_id; puede existir duplicado histórico.", exc_info=True)
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
    """
    Actualiza campos permitidos de un pedido.

    Corrección importante:
    - Si clear_error=True, NO se debe añadir también "error = ?" porque
      PostgreSQL rechaza "multiple assignments to same column".
    - Esto evita fallos en el flujo post-pago al marcar estados sin error.
    """
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
        "drive_uploaded_at",
        "drive_expires_at",
        "drive_deleted_at",
        "drive_status",
        "drive_delete_error",
        "processing_lock",
        "processing_started_at",
        "retry_count",
        "error",
    }

    updates: list[str] = []
    values: list[Any] = []
    assigned: set[str] = set()

    for key, value in campos.items():
        if key not in allowed:
            continue

        # Si se pide limpiar el error, evitamos asignarlo dos veces.
        if key == "error" and clear_error:
            continue

        if key in assigned:
            continue

        updates.append(f"{key} = ?")
        values.append(value)
        assigned.add(key)

    if clear_error and "error" not in assigned:
        updates.append("error = NULL")
        assigned.add("error")

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
    campos: dict[str, Any] = {"estado": estado}
    clear_error = error is None

    if error is not None:
        campos["error"] = error

    return update_pedido_campos(
        pedido_id,
        clear_error=clear_error,
        **campos,
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
    """
    Código público de confirmación.

    No expone el ID interno real del pedido.
    """
    numero = (int(pedido_id) * 9301 + 49297) % 900000 + 100000
    return f"ALMA-{numero:06d}"


# ============================================================
# Locks / Drive cleanup helpers
# ============================================================

def acquire_processing_lock(pedido_id: int, stale_after_minutes: int = 45) -> bool:
    """
    Bloqueo simple e idempotente para evitar doble procesamiento del mismo pedido.
    Si un proceso murió y el lock quedó viejo, permite recuperarlo después del tiempo indicado.
    """
    stale_after_minutes = max(5, int(stale_after_minutes or 45))
    if _use_postgres():
        sql = """
            UPDATE pedidos
            SET processing_lock = 1,
                processing_started_at = CURRENT_TIMESTAMP,
                retry_count = COALESCE(retry_count, 0) + 1,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE id = ?
              AND (
                    COALESCE(processing_lock, 0) = 0
                    OR processing_started_at IS NULL
                    OR processing_started_at < (CURRENT_TIMESTAMP - (? * INTERVAL '1 minute'))
                  )
        """
        cur = _execute(sql, (int(pedido_id), stale_after_minutes))
    else:
        sql = """
            UPDATE pedidos
            SET processing_lock = 1,
                processing_started_at = CURRENT_TIMESTAMP,
                retry_count = COALESCE(retry_count, 0) + 1,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE id = ?
              AND (
                    COALESCE(processing_lock, 0) = 0
                    OR processing_started_at IS NULL
                    OR datetime(processing_started_at) < datetime('now', ?)
                  )
        """
        cur = _execute(sql, (int(pedido_id), f"-{stale_after_minutes} minutes"))
    _commit()
    return int(cur.rowcount or 0) == 1


def release_processing_lock(pedido_id: int) -> int:
    return update_pedido_campos(
        int(pedido_id),
        processing_lock=0,
        processing_started_at=None,
    )


def list_pedidos_drive_expirados(limit: int = 200):
    return _fetchall(
        """
        SELECT *
        FROM pedidos
        WHERE drive_file_id IS NOT NULL
          AND drive_file_id <> ''
          AND drive_expires_at IS NOT NULL
          AND drive_status IN ('active', 'uploaded', 'expired', 'delete_error')
          AND estado IN ('completado', 'pdf_generado', 'enviado')
          AND drive_expires_at < CURRENT_TIMESTAMP
        ORDER BY drive_expires_at ASC, id ASC
        LIMIT ?
        """,
        (int(limit),),
    )


def marcar_drive_eliminado(pedido_id: int) -> int:
    return update_pedido_campos(
        int(pedido_id),
        drive_file_id=None,
        drive_view_link=None,
        drive_download_link=None,
        drive_deleted_at=_now_iso(),
        drive_status='deleted',
        drive_delete_error=None,
    )


def marcar_drive_delete_error(pedido_id: int, error: str) -> int:
    return update_pedido_campos(
        int(pedido_id),
        drive_status='delete_error',
        drive_delete_error=str(error)[:2000],
    )


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
