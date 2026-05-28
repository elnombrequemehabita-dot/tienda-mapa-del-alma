import os
import sqlite3
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from flask import current_app, g

from app.order_states import ESTADO_PENDIENTE_PAGO

logger = logging.getLogger(__name__)

_db_init_lock = threading.Lock()

RESENA_ESTADO_PENDIENTE = "pendiente"
RESENA_ESTADO_APROBADA = "aprobada"
RESENA_ESTADO_RECHAZADA = "rechazada"

PROMO_INICIO_CODIGO = "inicio_1111"
PROMO_INICIO_LIMITE = 25
PROMO_PRECIO_CENTAVOS = 1111
PRECIO_NORMAL_CENTAVOS = 2222
PROMO_RESERVA_HORAS = 24
TIPO_PRODUCTO_DIGITAL = "digital"
TIPO_PRODUCTO_IMPRESO = "impreso"
TRANSPORTISTAS_ENVIO = ("USPS", "UPS", "FedEx", "DHL", "Otro")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


PRECIO_IMPRESO_CENTAVOS = _env_int("PRECIO_IMPRESO_CENTAVOS", 5555)
PROMO_ESTADOS_NO_CONSUMEN = {
    "error_generacion",
    "error_envio",
    "error_openai",
    "error_json",
    "error_pdf",
    "error_drive",
    "error_email",
    "revision_manual",
    "needs_admin_review",
}


def normalizar_tipo_producto(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {TIPO_PRODUCTO_IMPRESO, "print", "printed", "fisico", "físico", "libro"}:
        return TIPO_PRODUCTO_IMPRESO
    return TIPO_PRODUCTO_DIGITAL


def _bool_from_db(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    raw = str(value).strip().lower()
    return raw in {"1", "true", "t", "yes", "y", "si", "sí", "on"}


def etiqueta_tipo_producto(value: Any) -> str:
    tipo = normalizar_tipo_producto(value)
    if tipo == TIPO_PRODUCTO_IMPRESO:
        return "Libro impreso + PDF digital"
    return "Solo PDF digital"


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


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    text = str(value).strip().replace("Z", "+00:00")
    for candidate in (text, text.replace(" ", "T")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


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
        "tienda.sqlite",
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


def _table_columns(table: str) -> set[str]:
    if _use_postgres():
        rows = _fetchall(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = ?
            """,
            (table,),
        )
        return {str(row["column_name"]) for row in rows}

    rows = _fetchall(f"PRAGMA table_info({table})")
    return {str(row["name"]) for row in rows}


def _copy_column_if_empty(table: str, target: str, source: str) -> None:
    columns = _table_columns(table)
    if target not in columns or source not in columns:
        return
    _execute(
        f"UPDATE {table} SET {target} = {source} "
        f"WHERE ({target} IS NULL OR {target} = '') "
        f"AND ({source} IS NOT NULL AND {source} != '')"
    )


def _migrate_pedido_aliases() -> None:
    _copy_column_if_empty("pedidos", "drive_download_link", "pdf_url")
    _copy_column_if_empty("pedidos", "drive_view_link", "pdf_url")
    _copy_column_if_empty("pedidos", "error", "error_message")
    _copy_column_if_empty("pedidos", "actualizado_en", "updated_at")
    _copy_column_if_empty("pedidos", "creado_en", "created_at")

    columns = _table_columns("pedidos")
    if "estado" in columns and "error" in columns:
        _execute("UPDATE pedidos SET error = NULL WHERE estado = 'completado'")
    if "precio_centavos" in columns:
        _execute(
            "UPDATE pedidos SET precio_centavos = ? "
            "WHERE precio_centavos IS NULL OR precio_centavos = 0",
            (PRECIO_NORMAL_CENTAVOS,),
        )
    if "idioma" in columns:
        _execute("UPDATE pedidos SET idioma = 'es' WHERE idioma IS NULL OR idioma = ''")
    if "tipo_producto" in columns:
        _execute(
            "UPDATE pedidos SET tipo_producto = ? "
            "WHERE tipo_producto IS NULL OR tipo_producto = ''",
            (TIPO_PRODUCTO_DIGITAL,),
        )
    if "es_regalo" in columns:
        _execute("UPDATE pedidos SET es_regalo = 0 WHERE es_regalo IS NULL")


def _migrate_resena_aliases() -> None:
    columns = _table_columns("resenas")
    if "creado_en" in columns and "created_at" in columns:
        _copy_column_if_empty("resenas", "creado_en", "created_at")
    if "actualizado_en" in columns and "updated_at" in columns:
        _copy_column_if_empty("resenas", "actualizado_en", "updated_at")
    if "actualizado_en" in columns:
        fallback_parts = ["actualizado_en"]
        if "creado_en" in columns:
            fallback_parts.append("creado_en")
        if "created_at" in columns:
            fallback_parts.append("created_at")
        fallback_parts.append("CURRENT_TIMESTAMP")
        _execute(
            f"UPDATE resenas SET actualizado_en = COALESCE({', '.join(fallback_parts)}) "
            "WHERE actualizado_en IS NULL OR actualizado_en = ''"
        )


def _pedido_dict(row):
    if row is None:
        return None
    data = dict(row)
    data["created_at"] = data.get("created_at") or data.get("creado_en")
    data["updated_at"] = data.get("actualizado_en") or data.get("updated_at")
    data["pdf_url"] = data.get("drive_download_link") or data.get("drive_view_link") or data.get("pdf_url")
    data["precio_centavos"] = data.get("precio_centavos") or PRECIO_NORMAL_CENTAVOS
    data["idioma"] = data.get("idioma") or "es"
    data["tipo_producto"] = normalizar_tipo_producto(data.get("tipo_producto"))
    data["tipo_producto_label"] = etiqueta_tipo_producto(data.get("tipo_producto"))
    data["es_regalo"] = _bool_from_db(data.get("es_regalo"))
    data["dedicatoria"] = data.get("dedicatoria") or ""
    data["tracking_number"] = data.get("tracking_number") or ""
    data["shipping_carrier"] = data.get("shipping_carrier") or ""

    if data.get("estado") == "completado" and not data.get("error"):
        data["error_message"] = None
    else:
        data["error_message"] = data.get("error") or data.get("error_message")

    return data


def _pedidos_list(rows):
    return [_pedido_dict(row) for row in rows]


def _format_usd_centavos(centavos: int) -> str:
    return f"${int(centavos) / 100:.2f}"


def _pedido_ocupa_cupo_promocion(row: Any) -> bool:
    data = dict(row)
    estado = str(data.get("estado") or "").strip().lower()
    if estado in PROMO_ESTADOS_NO_CONSUMEN:
        return False

    if estado != ESTADO_PENDIENTE_PAGO:
        return True

    creado = _parse_datetime(data.get("creado_en") or data.get("created_at"))
    if creado is None:
        return True

    vence = creado + timedelta(hours=PROMO_RESERVA_HORAS)
    return vence >= datetime.now(timezone.utc)


def get_promocion_inicio_estado() -> dict[str, Any]:
    """
    Estado público y de checkout para la promoción de lanzamiento 11:11.

    Los pedidos pendientes reservan un cupo durante 24 horas. Esto evita vender más
    de 25 sesiones promocionales cuando varias personas abren checkout a la vez.
    """
    rows = _fetchall(
        """
        SELECT id, estado, creado_en
        FROM pedidos
        WHERE promocion_codigo = ?
        ORDER BY id ASC
        """,
        (PROMO_INICIO_CODIGO,),
    )
    usados = sum(1 for row in rows if _pedido_ocupa_cupo_promocion(row))
    restantes = max(0, PROMO_INICIO_LIMITE - usados)
    activa = restantes > 0
    precio_actual_centavos = PROMO_PRECIO_CENTAVOS if activa else PRECIO_NORMAL_CENTAVOS
    porcentaje_usado = 0
    if PROMO_INICIO_LIMITE > 0:
        porcentaje_usado = min(100, round((usados / PROMO_INICIO_LIMITE) * 100))

    return {
        "codigo": PROMO_INICIO_CODIGO,
        "limite": PROMO_INICIO_LIMITE,
        "usados": usados,
        "restantes": restantes,
        "activa": activa,
        "reserva_horas": PROMO_RESERVA_HORAS,
        "porcentaje_usado": porcentaje_usado,
        "precio_normal_centavos": PRECIO_NORMAL_CENTAVOS,
        "precio_promo_centavos": PROMO_PRECIO_CENTAVOS,
        "precio_actual_centavos": precio_actual_centavos,
        "precio_normal": _format_usd_centavos(PRECIO_NORMAL_CENTAVOS),
        "precio_promo": _format_usd_centavos(PROMO_PRECIO_CENTAVOS),
        "precio_actual": _format_usd_centavos(precio_actual_centavos),
    }


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
                idioma TEXT DEFAULT 'es',
                producto TEXT DEFAULT 'mapa_alma',
                tipo_producto TEXT DEFAULT 'digital',
                es_regalo BOOLEAN DEFAULT FALSE,
                dedicatoria TEXT,
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
                drive_status TEXT,
                drive_delete_error TEXT,
                contenido_openai JSONB,
                openai_model TEXT,
                openai_input_tokens INTEGER DEFAULT 0,
                openai_output_tokens INTEGER DEFAULT 0,
                openai_total_tokens INTEGER DEFAULT 0,
                openai_estimated_cost_usd NUMERIC DEFAULT 0,
                openai_call_count INTEGER DEFAULT 0,
                json_path TEXT,
                raw_openai_path TEXT,
                last_error_stage TEXT,
                last_error_message TEXT,
                last_error_traceback TEXT,
                generation_status TEXT,
                precio_centavos INTEGER,
                promocion_codigo TEXT,
                promocion_precio_centavos INTEGER,
                processing_lock INTEGER DEFAULT 0,
                processing_started_at TIMESTAMP,
                tracking_number TEXT,
                shipping_carrier TEXT,
                printed_at TIMESTAMP,
                shipped_at TIMESTAMP,
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
            CREATE TABLE IF NOT EXISTS openai_usage_logs (
                id SERIAL PRIMARY KEY,
                order_id INTEGER,
                model TEXT,
                call_type TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                estimated_cost_usd NUMERIC,
                duration_seconds NUMERIC,
                retry_count INTEGER DEFAULT 0,
                sections TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        _add_column_if_missing("pedidos", "idioma", "TEXT DEFAULT 'es'")
        _add_column_if_missing("pedidos", "producto", "TEXT DEFAULT 'mapa_alma'")
        _add_column_if_missing("pedidos", "tipo_producto", "TEXT DEFAULT 'digital'")
        _add_column_if_missing("pedidos", "es_regalo", "BOOLEAN DEFAULT FALSE")
        _add_column_if_missing("pedidos", "dedicatoria", "TEXT")
        _add_column_if_missing("pedidos", "stripe_session_id", "TEXT")
        _add_column_if_missing("pedidos", "stripe_payment_intent", "TEXT")
        _add_column_if_missing("pedidos", "pdf_path", "TEXT")
        _add_column_if_missing("pedidos", "drive_file_id", "TEXT")
        _add_column_if_missing("pedidos", "drive_view_link", "TEXT")
        _add_column_if_missing("pedidos", "drive_download_link", "TEXT")
        _add_column_if_missing("pedidos", "drive_uploaded_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "drive_expires_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "drive_deleted_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "drive_status", "TEXT")
        _add_column_if_missing("pedidos", "drive_delete_error", "TEXT")
        _add_column_if_missing("pedidos", "contenido_openai", "TEXT", "JSONB")
        _add_column_if_missing("pedidos", "openai_model", "TEXT")
        _add_column_if_missing("pedidos", "openai_input_tokens", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "openai_output_tokens", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "openai_total_tokens", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "openai_estimated_cost_usd", "NUMERIC DEFAULT 0")
        _add_column_if_missing("pedidos", "openai_call_count", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "json_path", "TEXT")
        _add_column_if_missing("pedidos", "raw_openai_path", "TEXT")
        _add_column_if_missing("pedidos", "last_error_stage", "TEXT")
        _add_column_if_missing("pedidos", "last_error_message", "TEXT")
        _add_column_if_missing("pedidos", "last_error_traceback", "TEXT")
        _add_column_if_missing("pedidos", "generation_status", "TEXT")
        _add_column_if_missing("pedidos", "precio_centavos", "INTEGER")
        _add_column_if_missing("pedidos", "promocion_codigo", "TEXT")
        _add_column_if_missing("pedidos", "promocion_precio_centavos", "INTEGER")
        _add_column_if_missing("pedidos", "processing_lock", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "processing_started_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "tracking_number", "TEXT")
        _add_column_if_missing("pedidos", "shipping_carrier", "TEXT")
        _add_column_if_missing("pedidos", "printed_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "shipped_at", "TIMESTAMP")
        _add_column_if_missing("pedidos", "error", "TEXT")
        _add_column_if_missing("pedidos", "actualizado_en", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column_if_missing("resenas", "creado_en", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column_if_missing("resenas", "actualizado_en", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column_if_missing("openai_usage_logs", "duration_seconds", "NUMERIC")
        _add_column_if_missing("openai_usage_logs", "retry_count", "INTEGER DEFAULT 0")
        _add_column_if_missing("openai_usage_logs", "sections", "TEXT")

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
                idioma TEXT DEFAULT 'es',
                producto TEXT DEFAULT 'mapa_alma',
                tipo_producto TEXT DEFAULT 'digital',
                es_regalo INTEGER DEFAULT 0,
                dedicatoria TEXT,
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
                drive_status TEXT,
                drive_delete_error TEXT,
                contenido_openai TEXT,
                openai_model TEXT,
                openai_input_tokens INTEGER DEFAULT 0,
                openai_output_tokens INTEGER DEFAULT 0,
                openai_total_tokens INTEGER DEFAULT 0,
                openai_estimated_cost_usd REAL DEFAULT 0,
                openai_call_count INTEGER DEFAULT 0,
                json_path TEXT,
                raw_openai_path TEXT,
                last_error_stage TEXT,
                last_error_message TEXT,
                last_error_traceback TEXT,
                generation_status TEXT,
                precio_centavos INTEGER,
                promocion_codigo TEXT,
                promocion_precio_centavos INTEGER,
                processing_lock INTEGER DEFAULT 0,
                processing_started_at TEXT,
                tracking_number TEXT,
                shipping_carrier TEXT,
                printed_at TEXT,
                shipped_at TEXT,
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
            CREATE TABLE IF NOT EXISTS openai_usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                model TEXT,
                call_type TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                estimated_cost_usd REAL,
                duration_seconds REAL,
                retry_count INTEGER DEFAULT 0,
                sections TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        _add_column_if_missing("pedidos", "idioma", "TEXT DEFAULT 'es'")
        _add_column_if_missing("pedidos", "producto", "TEXT DEFAULT 'mapa_alma'")
        _add_column_if_missing("pedidos", "tipo_producto", "TEXT DEFAULT 'digital'")
        _add_column_if_missing("pedidos", "es_regalo", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "dedicatoria", "TEXT")
        _add_column_if_missing("pedidos", "stripe_session_id", "TEXT")
        _add_column_if_missing("pedidos", "stripe_payment_intent", "TEXT")
        _add_column_if_missing("pedidos", "pdf_path", "TEXT")
        _add_column_if_missing("pedidos", "drive_file_id", "TEXT")
        _add_column_if_missing("pedidos", "drive_view_link", "TEXT")
        _add_column_if_missing("pedidos", "drive_download_link", "TEXT")
        _add_column_if_missing("pedidos", "drive_uploaded_at", "TEXT")
        _add_column_if_missing("pedidos", "drive_expires_at", "TEXT")
        _add_column_if_missing("pedidos", "drive_deleted_at", "TEXT")
        _add_column_if_missing("pedidos", "drive_status", "TEXT")
        _add_column_if_missing("pedidos", "drive_delete_error", "TEXT")
        _add_column_if_missing("pedidos", "contenido_openai", "TEXT")
        _add_column_if_missing("pedidos", "openai_model", "TEXT")
        _add_column_if_missing("pedidos", "openai_input_tokens", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "openai_output_tokens", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "openai_total_tokens", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "openai_estimated_cost_usd", "REAL DEFAULT 0")
        _add_column_if_missing("pedidos", "openai_call_count", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "json_path", "TEXT")
        _add_column_if_missing("pedidos", "raw_openai_path", "TEXT")
        _add_column_if_missing("pedidos", "last_error_stage", "TEXT")
        _add_column_if_missing("pedidos", "last_error_message", "TEXT")
        _add_column_if_missing("pedidos", "last_error_traceback", "TEXT")
        _add_column_if_missing("pedidos", "generation_status", "TEXT")
        _add_column_if_missing("pedidos", "precio_centavos", "INTEGER")
        _add_column_if_missing("pedidos", "promocion_codigo", "TEXT")
        _add_column_if_missing("pedidos", "promocion_precio_centavos", "INTEGER")
        _add_column_if_missing("pedidos", "processing_lock", "INTEGER DEFAULT 0")
        _add_column_if_missing("pedidos", "processing_started_at", "TEXT")
        _add_column_if_missing("pedidos", "tracking_number", "TEXT")
        _add_column_if_missing("pedidos", "shipping_carrier", "TEXT")
        _add_column_if_missing("pedidos", "printed_at", "TEXT")
        _add_column_if_missing("pedidos", "shipped_at", "TEXT")
        _add_column_if_missing("pedidos", "error", "TEXT")
        _add_column_if_missing("pedidos", "creado_en", "TEXT")
        _add_column_if_missing("pedidos", "actualizado_en", "TEXT")
        _add_column_if_missing("resenas", "creado_en", "TEXT")
        _add_column_if_missing("resenas", "actualizado_en", "TEXT")
        _add_column_if_missing("openai_usage_logs", "duration_seconds", "REAL")
        _add_column_if_missing("openai_usage_logs", "retry_count", "INTEGER DEFAULT 0")
        _add_column_if_missing("openai_usage_logs", "sections", "TEXT")

    _migrate_pedido_aliases()
    _migrate_resena_aliases()

    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos (estado)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_email ON pedidos (email)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_stripe_session_id ON pedidos (stripe_session_id)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_promocion_codigo ON pedidos (promocion_codigo)")
    _execute("CREATE INDEX IF NOT EXISTS idx_pedidos_tipo_producto ON pedidos (tipo_producto)")
    _execute("CREATE INDEX IF NOT EXISTS idx_resenas_estado ON resenas (estado)")
    _execute("CREATE INDEX IF NOT EXISTS idx_resenas_pedido_id ON resenas (pedido_id)")
    _execute("CREATE INDEX IF NOT EXISTS idx_notificaciones_pedido_id ON notificaciones (pedido_id)")
    _execute("CREATE INDEX IF NOT EXISTS idx_openai_usage_logs_order_id ON openai_usage_logs (order_id)")

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
    idioma: str = "es",
    producto: str = "mapa_alma",
    tipo_producto: str = TIPO_PRODUCTO_DIGITAL,
    es_regalo: bool = False,
    dedicatoria: Optional[str] = None,
    estado: str = ESTADO_PENDIENTE_PAGO,
    precio_centavos: Optional[int] = None,
    promocion_codigo: Optional[str] = None,
    promocion_precio_centavos: Optional[int] = None,
) -> int:
    sql = """
        INSERT INTO pedidos (
            nombre, apellidos, email, fecha_nacimiento, sexo, forma_trato, idioma,
            producto, tipo_producto, es_regalo, dedicatoria, estado,
            precio_centavos, promocion_codigo, promocion_precio_centavos,
            creado_en, actualizado_en
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
    if _use_postgres():
        sql += " RETURNING id"

    cur = _execute(
        sql,
        (
            nombre,
            apellidos,
            email,
            fecha_nacimiento,
            sexo,
            forma_trato,
            idioma or "es",
            producto,
            normalizar_tipo_producto(tipo_producto),
            1 if es_regalo else 0,
            dedicatoria,
            estado,
            precio_centavos if precio_centavos is not None else PRECIO_NORMAL_CENTAVOS,
            promocion_codigo,
            promocion_precio_centavos,
        ),
    )
    pedido_id = _last_insert_id(cur)
    _commit()
    return pedido_id


def get_pedido_by_id(pedido_id: int):
    return _pedido_dict(_fetchone("SELECT * FROM pedidos WHERE id = ?", (int(pedido_id),)))


def get_pedido_pendiente_por_email(email: str):
    return _pedido_dict(_fetchone(
        """
        SELECT *
        FROM pedidos
        WHERE lower(email) = lower(?)
          AND estado = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (email, ESTADO_PENDIENTE_PAGO),
    ))


def list_pedidos_por_estados(estados: Iterable[str], limit: int = 500):
    estados = tuple(estados)
    if not estados:
        return []

    placeholders = ",".join(["?"] * len(estados))
    return _pedidos_list(_fetchall(
        f"""
        SELECT *
        FROM pedidos
        WHERE estado IN ({placeholders})
        ORDER BY id DESC
        LIMIT ?
        """,
        (*estados, int(limit)),
    ))


def list_pedidos(limit: int = 500):
    return _pedidos_list(_fetchall(
        "SELECT * FROM pedidos ORDER BY id DESC LIMIT ?",
        (int(limit),),
    ))


def list_pedidos_impresos(limit: int = 500):
    return _pedidos_list(_fetchall(
        """
        SELECT *
        FROM pedidos
        WHERE tipo_producto = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (TIPO_PRODUCTO_IMPRESO, int(limit)),
    ))


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
        "idioma",
        "producto",
        "tipo_producto",
        "es_regalo",
        "dedicatoria",
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
        "contenido_openai",
        "openai_model",
        "openai_input_tokens",
        "openai_output_tokens",
        "openai_total_tokens",
        "openai_estimated_cost_usd",
        "openai_call_count",
        "json_path",
        "raw_openai_path",
        "last_error_stage",
        "last_error_message",
        "last_error_traceback",
        "generation_status",
        "precio_centavos",
        "promocion_codigo",
        "promocion_precio_centavos",
        "processing_lock",
        "processing_started_at",
        "tracking_number",
        "shipping_carrier",
        "printed_at",
        "shipped_at",
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


def acquire_processing_lock(pedido_id: int, stale_after_minutes: int = 45) -> bool:
    """
    Evita doble procesamiento cuando Stripe webhook, retorno y admin coinciden.
    """
    now = _now_iso()
    stale_cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=int(stale_after_minutes))
    ).isoformat(timespec="seconds")

    cur = _execute(
        """
        UPDATE pedidos
        SET processing_lock = 1,
            processing_started_at = ?,
            actualizado_en = CURRENT_TIMESTAMP
        WHERE id = ?
          AND (
            processing_lock IS NULL
            OR processing_lock = 0
            OR processing_started_at IS NULL
            OR processing_started_at < ?
          )
        """,
        (now, int(pedido_id), stale_cutoff),
    )
    _commit()
    return int(cur.rowcount or 0) > 0


def release_processing_lock(pedido_id: int) -> int:
    cur = _execute(
        """
        UPDATE pedidos
        SET processing_lock = 0,
            processing_started_at = NULL,
            actualizado_en = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (int(pedido_id),),
    )
    _commit()
    return int(cur.rowcount or 0)


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
# OpenAI usage / costos
# ============================================================

def insert_openai_usage_log(
    order_id: int,
    model: str,
    call_type: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost_usd: Optional[float] = None,
    duration_seconds: Optional[float] = None,
    retry_count: int = 0,
    sections: Optional[str] = None,
) -> int:
    sql = """
        INSERT INTO openai_usage_logs (
            order_id, model, call_type, input_tokens, output_tokens,
            total_tokens, estimated_cost_usd, duration_seconds, retry_count,
            sections, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """
    if _use_postgres():
        sql += " RETURNING id"

    cur = _execute(
        sql,
        (
            int(order_id),
            model,
            call_type,
            int(input_tokens or 0),
            int(output_tokens or 0),
            int(total_tokens or 0),
            estimated_cost_usd,
            duration_seconds,
            int(retry_count or 0),
            sections,
        ),
    )
    log_id = _last_insert_id(cur)
    _commit()
    _refresh_openai_usage_totals(order_id)
    return log_id


def _refresh_openai_usage_totals(order_id: int) -> None:
    row = _fetchone(
        """
        SELECT
            COUNT(*) AS call_count,
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(total_tokens), 0) AS total_tokens,
            COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
            COALESCE(SUM(duration_seconds), 0) AS duration_seconds,
            COALESCE(SUM(retry_count), 0) AS retry_count,
            MAX(model) AS model
        FROM openai_usage_logs
        WHERE order_id = ?
        """,
        (int(order_id),),
    )
    if not row:
        return

    update_pedido_campos(
        int(order_id),
        openai_model=row["model"],
        openai_input_tokens=int(row["input_tokens"] or 0),
        openai_output_tokens=int(row["output_tokens"] or 0),
        openai_total_tokens=int(row["total_tokens"] or 0),
        openai_estimated_cost_usd=float(row["estimated_cost_usd"] or 0),
        openai_call_count=int(row["call_count"] or 0),
    )


def get_openai_usage_summary(order_id: int) -> dict[str, Any]:
    row = _fetchone(
        """
        SELECT
            COUNT(*) AS call_count,
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(total_tokens), 0) AS total_tokens,
            COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
            COALESCE(SUM(duration_seconds), 0) AS duration_seconds,
            COALESCE(SUM(retry_count), 0) AS retry_count,
            MAX(model) AS model
        FROM openai_usage_logs
        WHERE order_id = ?
        """,
        (int(order_id),),
    )
    if not row:
        return {
            "call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "duration_seconds": 0.0,
            "retry_count": 0,
            "model": None,
        }
    return {
        "call_count": int(row["call_count"] or 0),
        "input_tokens": int(row["input_tokens"] or 0),
        "output_tokens": int(row["output_tokens"] or 0),
        "total_tokens": int(row["total_tokens"] or 0),
        "estimated_cost_usd": float(row["estimated_cost_usd"] or 0),
        "duration_seconds": float(row["duration_seconds"] or 0),
        "retry_count": int(row["retry_count"] or 0),
        "model": row["model"],
    }


def get_openai_call_count(order_id: int) -> int:
    summary = get_openai_usage_summary(int(order_id))
    return int(summary.get("call_count") or 0)


def list_openai_usage_logs(order_id: int, limit: int = 100):
    return _fetchall(
        """
        SELECT *
        FROM openai_usage_logs
        WHERE order_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(order_id), int(limit)),
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
    columns = _table_columns("resenas")
    fields = ["pedido_id", "nombre_cliente", "email_cliente", "rating", "comentario", "estado"]
    placeholders = ["?", "?", "?", "?", "?", "?"]
    values: list[Any] = [
        int(pedido_id),
        nombre_cliente,
        email_cliente,
        int(rating),
        comentario,
        estado,
    ]

    for timestamp_col in ("creado_en", "actualizado_en", "created_at", "updated_at"):
        if timestamp_col in columns:
            fields.append(timestamp_col)
            placeholders.append("CURRENT_TIMESTAMP")

    sql = f"""
        INSERT INTO resenas (
            {', '.join(fields)}
        )
        VALUES ({', '.join(placeholders)})
    """
    if _use_postgres():
        sql += " RETURNING id"

    cur = _execute(
        sql,
        values,
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
