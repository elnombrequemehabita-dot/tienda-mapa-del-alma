"""
Acceso a SQLite: creación de tablas, migraciones suaves y helpers de pedidos.

La ruta del archivo .sqlite viene de app.config["DATABASE"] (carpeta instance/).
Las columnas `estado`, `pdf_path`, `pdf_url`, `error_message`, `updated_at` se añaden
automáticamente si tu base de datos era de una versión anterior.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from flask import current_app, g

from app.order_states import ESTADO_COMPLETADO, ESTADO_PENDIENTE_PAGO

RESENA_ESTADO_PENDIENTE = "pendiente"
RESENA_ESTADO_APROBADA = "aprobada"
RESENA_ESTADO_RECHAZADA = "rechazada"


class _Unset:
    """Marcador interno: «no modificar este campo en el UPDATE»."""


UNSET: Any = _Unset()


def codigo_confirmacion_pedido(order_id: int) -> str:
    """
    Código legible y estable para rastrear un pedido en cliente/admin/PDF.
    """
    return f"MAPA-{int(order_id):06d}"


def get_db() -> sqlite3.Connection:
    """
    Devuelve una conexión a la base de datos reutilizada durante la petición HTTP.

    Flask guarda la conexión en g.db y la cierra al terminar la petición.
    """
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_e=None) -> None:
    """Cierra la conexión al finalizar la petición."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def utc_now_iso() -> str:
    """Marca de tiempo ISO en UTC para created_at / updated_at."""
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    """
    Crea la tabla `pedidos` si no existe (esquema completo actual)
    y aplica migraciones para bases antiguas.
    """
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            nombre TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            email TEXT NOT NULL,
            telefono TEXT,
            notas TEXT,
            fecha_nacimiento TEXT,
            forma_trato TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente_pago',
            pdf_path TEXT,
            pdf_url TEXT,
            error_message TEXT
        );
        """
    )
    db.commit()
    migrate_pedidos_schema()
    migrate_resenas_schema()
    migrate_notificaciones_schema()
    migrate_resenas_pedido_nullable()


def migrate_resenas_schema() -> None:
    """Crea la tabla `resenas` si no existe."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS resenas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER,
            nombre_cliente TEXT NOT NULL,
            email_cliente TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comentario TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            created_at TEXT NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        );
        """
    )
    db.commit()


def migrate_resenas_pedido_nullable() -> None:
    """
    Convierte `pedido_id` en opcional para poder borrar pedidos y conservar reseñas.
    Idempotente: no hace nada si la columna ya admite NULL.
    """
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='resenas'"
    ).fetchone():
        return
    rows = db.execute("PRAGMA table_info(resenas)").fetchall()
    by_name = {r[1]: r for r in rows}
    if "pedido_id" not in by_name:
        return
    if by_name["pedido_id"][3] == 0:
        return
    db.executescript(
        """
        CREATE TABLE resenas_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER,
            nombre_cliente TEXT NOT NULL,
            email_cliente TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comentario TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            created_at TEXT NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        );
        INSERT INTO resenas_new (id, pedido_id, nombre_cliente, email_cliente, rating, comentario, estado, created_at)
        SELECT id, pedido_id, nombre_cliente, email_cliente, rating, comentario, estado, created_at FROM resenas;
        DROP TABLE resenas;
        ALTER TABLE resenas_new RENAME TO resenas;
        """
    )
    db.commit()


def migrate_notificaciones_schema() -> None:
    """Crea la tabla de historial de notificaciones si no existe."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            canal TEXT NOT NULL,
            destinatario TEXT NOT NULL,
            estado TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        );
        """
    )
    db.commit()


def migrate_pedidos_schema() -> None:
    """
    Añade columnas nuevas si la tabla ya existía con el esquema antiguo
    y rellena valores por defecto de forma segura.
    """
    db = get_db()
    rows = db.execute("PRAGMA table_info(pedidos)").fetchall()
    if not rows:
        return
    cols = {r[1] for r in rows}
    alters: list[str] = []
    if "updated_at" not in cols:
        alters.append("ALTER TABLE pedidos ADD COLUMN updated_at TEXT")
    if "estado" not in cols:
        alters.append("ALTER TABLE pedidos ADD COLUMN estado TEXT")
    if "pdf_path" not in cols:
        alters.append("ALTER TABLE pedidos ADD COLUMN pdf_path TEXT")
    if "pdf_url" not in cols:
        alters.append("ALTER TABLE pedidos ADD COLUMN pdf_url TEXT")
    if "error_message" not in cols:
        alters.append("ALTER TABLE pedidos ADD COLUMN error_message TEXT")
    if "apellidos" not in cols:
        alters.append("ALTER TABLE pedidos ADD COLUMN apellidos TEXT DEFAULT ''")
    if "fecha_nacimiento" not in cols:
        alters.append("ALTER TABLE pedidos ADD COLUMN fecha_nacimiento TEXT")
    if "forma_trato" not in cols:
        alters.append("ALTER TABLE pedidos ADD COLUMN forma_trato TEXT")
    for sql in alters:
        db.execute(sql)
    db.commit()

    db.execute(
        """
        UPDATE pedidos
        SET updated_at = created_at
        WHERE updated_at IS NULL OR updated_at = ''
        """
    )
    db.execute(
        """
        UPDATE pedidos
        SET estado = ?
        WHERE estado IS NULL OR estado = ''
        """,
        (ESTADO_PENDIENTE_PAGO,),
    )
    db.execute(
        """
        UPDATE pedidos
        SET apellidos = ''
        WHERE apellidos IS NULL
        """
    )
    db.commit()


def init_app(app) -> None:
    """Registra el cierre de BD y crea / migra tablas."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def insert_pedido(
    *,
    nombre: str,
    apellidos: str,
    email: str,
    fecha_nacimiento: Optional[str],
    forma_trato: Optional[str],
) -> int:
    """
    Inserta un pedido nuevo con estado inicial `pendiente_pago`.

    Las columnas legacy `telefono` y `notas` se dejan en NULL (ya no se usan
    en el formulario público).
    """
    db = get_db()
    now = utc_now_iso()
    cur = db.execute(
        """
        INSERT INTO pedidos (
            created_at, updated_at, nombre, apellidos, email,
            telefono, notas, fecha_nacimiento, forma_trato,
            estado, pdf_path, pdf_url, error_message
        )
        VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, NULL, NULL, NULL)
        """,
        (
            now,
            now,
            nombre.strip(),
            apellidos.strip(),
            email.strip(),
            fecha_nacimiento,
            forma_trato,
            ESTADO_PENDIENTE_PAGO,
        ),
    )
    db.commit()
    return int(cur.lastrowid)


def get_pedido_by_id(order_id: int) -> Optional[sqlite3.Row]:
    """Un pedido por id o None."""
    db = get_db()
    cur = db.execute("SELECT * FROM pedidos WHERE id = ?", (order_id,))
    return cur.fetchone()


def get_pedido_pendiente_por_email(email: str) -> Optional[sqlite3.Row]:
    """
    Último pedido en `pendiente_pago` para un email (comparación sin mayúsculas).

    Útil si el webhook no trae `metadata.pedido_id` pero sí el email del checkout.
    """
    if not email or not str(email).strip():
        return None
    email_norm = str(email).strip().lower()
    db = get_db()
    cur = db.execute(
        """
        SELECT * FROM pedidos
        WHERE lower(trim(email)) = ? AND estado = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (email_norm, ESTADO_PENDIENTE_PAGO),
    )
    return cur.fetchone()


def list_pedidos(limit: int = 200):
    """Lista pedidos del más reciente al más antiguo (panel admin)."""
    db = get_db()
    cur = db.execute(
        """
        SELECT *
        FROM pedidos
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return cur.fetchall()


def list_pedidos_por_estados(estados: tuple[str, ...], limit: int = 300):
    """
    Lista pedidos filtrando por estados concretos.

    Se usa en admin para separar bandeja principal y completados.
    """
    if not estados:
        return []
    db = get_db()
    placeholders = ", ".join("?" for _ in estados)
    sql = f"""
        SELECT *
        FROM pedidos
        WHERE estado IN ({placeholders})
        ORDER BY id DESC
        LIMIT ?
    """
    cur = db.execute(sql, (*estados, limit))
    return cur.fetchall()


def delete_pedido(order_id: int) -> int:
    """Elimina un pedido por id. Devuelve cantidad de filas borradas."""
    migrate_resenas_pedido_nullable()
    db = get_db()
    db.execute("UPDATE resenas SET pedido_id = NULL WHERE pedido_id = ?", (order_id,))
    db.execute("DELETE FROM notificaciones WHERE pedido_id = ?", (order_id,))
    cur = db.execute("DELETE FROM pedidos WHERE id = ?", (order_id,))
    db.commit()
    return int(cur.rowcount)


def delete_all_pedidos_keep_resenas() -> dict[str, int]:
    """
    Borra todos los pedidos y notificaciones; las reseñas permanecen sin `pedido_id`.
    """
    migrate_resenas_pedido_nullable()
    db = get_db()
    db.execute("UPDATE resenas SET pedido_id = NULL WHERE pedido_id IS NOT NULL")
    cur_n = db.execute("DELETE FROM notificaciones")
    cur_p = db.execute("DELETE FROM pedidos")
    db.commit()
    return {"notificaciones": int(cur_n.rowcount), "pedidos": int(cur_p.rowcount)}


def update_pedido_campos(
    order_id: int,
    *,
    estado: Any = UNSET,
    pdf_path: Any = UNSET,
    pdf_url: Any = UNSET,
    error_message: Any = UNSET,
    clear_error: bool = False,
) -> None:
    """
    Actualiza columnas permitidas y siempre toca `updated_at`.

    Usa UNSET para no modificar un campo. `clear_error=True` fuerza
    error_message a NULL (ignora `error_message` en ese caso).
    """
    db = get_db()
    now = utc_now_iso()
    sets: list[str] = ["updated_at = ?"]
    vals: list[Any] = [now]

    if estado is not UNSET:
        sets.append("estado = ?")
        vals.append(estado)

    if clear_error:
        sets.append("error_message = NULL")
    elif error_message is not UNSET:
        sets.append("error_message = ?")
        vals.append(error_message)

    if pdf_path is not UNSET:
        sets.append("pdf_path = ?")
        vals.append(pdf_path)
    if pdf_url is not UNSET:
        sets.append("pdf_url = ?")
        vals.append(pdf_url)

    vals.append(order_id)
    sql = f"UPDATE pedidos SET {', '.join(sets)} WHERE id = ?"
    db.execute(sql, vals)
    db.commit()


def insert_resena(
    *,
    pedido_id: int,
    nombre_cliente: str,
    email_cliente: str,
    rating: int,
    comentario: str,
) -> int:
    """Inserta reseña en estado pendiente. No valida duplicados (hazlo en la ruta)."""
    db = get_db()
    now = utc_now_iso()
    cur = db.execute(
        """
        INSERT INTO resenas (pedido_id, nombre_cliente, email_cliente, rating, comentario, estado, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pedido_id,
            nombre_cliente.strip(),
            email_cliente.strip(),
            int(rating),
            comentario.strip(),
            RESENA_ESTADO_PENDIENTE,
            now,
        ),
    )
    db.commit()
    return int(cur.lastrowid)


def resena_bloquea_nuevo_envio(pedido_id: int) -> bool:
    """True si ya hay reseña pendiente o aprobada para ese pedido."""
    db = get_db()
    cur = db.execute(
        """
        SELECT 1 FROM resenas
        WHERE pedido_id = ? AND estado IN (?, ?)
        LIMIT 1
        """,
        (pedido_id, RESENA_ESTADO_PENDIENTE, RESENA_ESTADO_APROBADA),
    )
    return cur.fetchone() is not None


def get_resena_by_id(resena_id: int) -> Optional[sqlite3.Row]:
    db = get_db()
    cur = db.execute("SELECT * FROM resenas WHERE id = ?", (resena_id,))
    return cur.fetchone()


def list_resenas_admin(limit: int = 200):
    db = get_db()
    cur = db.execute(
        """
        SELECT r.*, p.nombre AS pedido_nombre, p.apellidos AS pedido_apellidos, p.estado AS pedido_estado
        FROM resenas r
        LEFT JOIN pedidos p ON p.id = r.pedido_id
        ORDER BY r.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return cur.fetchall()


def list_resenas_aprobadas(limit: int = 40):
    """Solo aprobadas, para la web pública."""
    db = get_db()
    cur = db.execute(
        """
        SELECT r.*, p.nombre AS pedido_nombre, p.apellidos AS pedido_apellidos
        FROM resenas r
        LEFT JOIN pedidos p ON p.id = r.pedido_id
        WHERE r.estado = ? AND (r.pedido_id IS NULL OR p.estado = ?)
        ORDER BY r.created_at DESC
        LIMIT ?
        """,
        (RESENA_ESTADO_APROBADA, ESTADO_COMPLETADO, limit),
    )
    return cur.fetchall()


def list_resenas_aprobadas_todas():
    """Solo aprobadas (todas), para carrusel en la web pública."""
    db = get_db()
    cur = db.execute(
        """
        SELECT r.*, p.nombre AS pedido_nombre, p.apellidos AS pedido_apellidos
        FROM resenas r
        LEFT JOIN pedidos p ON p.id = r.pedido_id
        WHERE r.estado = ? AND (r.pedido_id IS NULL OR p.estado = ?)
        ORDER BY r.created_at DESC
        """,
        (RESENA_ESTADO_APROBADA, ESTADO_COMPLETADO),
    )
    return cur.fetchall()


def resumen_resenas_aprobadas() -> tuple[int, float]:
    """
    Devuelve (cantidad, promedio) de reseñas aprobadas: pedido completado o sin pedido (historial).

    El promedio es 0.0 si no hay reseñas.
    """
    db = get_db()
    cur = db.execute(
        """
        SELECT COUNT(*), COALESCE(AVG(r.rating), 0.0)
        FROM resenas r
        LEFT JOIN pedidos p ON p.id = r.pedido_id
        WHERE r.estado = ? AND (r.pedido_id IS NULL OR p.estado = ?)
        """,
        (RESENA_ESTADO_APROBADA, ESTADO_COMPLETADO),
    )
    row = cur.fetchone()
    if row is None:
        return 0, 0.0
    try:
        count = int(row[0] or 0)
    except (TypeError, ValueError):
        count = 0
    try:
        avg = float(row[1] or 0.0)
    except (TypeError, ValueError):
        avg = 0.0
    return count, avg


def update_resena_estado(resena_id: int, estado: str) -> int:
    """Devuelve filas actualizadas (0 o 1)."""
    db = get_db()
    cur = db.execute("UPDATE resenas SET estado = ? WHERE id = ?", (estado, resena_id))
    db.commit()
    return int(cur.rowcount)


def delete_resena(resena_id: int) -> int:
    """Elimina una reseña por id. Devuelve filas borradas (0 o 1)."""
    db = get_db()
    cur = db.execute("DELETE FROM resenas WHERE id = ?", (resena_id,))
    db.commit()
    return int(cur.rowcount)


def insert_notificacion(
    *,
    pedido_id: int,
    tipo: str,
    canal: str,
    destinatario: str,
    estado: str,
    error_message: Optional[str] = None,
) -> int:
    """Guarda en historial una notificación enviada o fallida."""
    db = get_db()
    now = utc_now_iso()
    cur = db.execute(
        """
        INSERT INTO notificaciones (pedido_id, tipo, canal, destinatario, estado, error_message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pedido_id,
            str(tipo).strip(),
            str(canal).strip(),
            str(destinatario).strip(),
            str(estado).strip(),
            (error_message or None),
            now,
        ),
    )
    db.commit()
    return int(cur.lastrowid)


def list_notificaciones_pedido(pedido_id: int, limit: int = 200):
    """Historial de notificaciones de un pedido (más nuevas primero)."""
    db = get_db()
    cur = db.execute(
        """
        SELECT *
        FROM notificaciones
        WHERE pedido_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (pedido_id, limit),
    )
    return cur.fetchall()
