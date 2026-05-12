# app/order_services.py

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import current_app

from app import db as database
from app.db import get_db
from app.pdf_generator import generar_pdf_desde_tienda
from app.order_states import (
    ESTADO_COMPLETADO,
    ESTADO_ENVIANDO_EMAIL,
    ESTADO_ERROR_ENVIO,
    ESTADO_ERROR_GENERACION,
    ESTADO_GENERANDO_PDF,
    ESTADO_PAGADO,
    ESTADO_PDF_GENERADO,
    ESTADO_PDF_GENERADO_PENDIENTE_DE_LINK,
    ESTADO_PENDIENTE_PAGO,
)

try:
    from app.openai_generator import generar_contenido_mapa
except Exception:
    generar_contenido_mapa = None

try:
    from app.email_service import (
        enviar_email_pedido_completado,
        enviar_email_admin_error,
    )
except Exception:
    enviar_email_pedido_completado = None
    enviar_email_admin_error = None

try:
    from app.google_drive_oauth import (
        subir_pdf_a_drive_oauth,
        eliminar_archivo_drive_oauth,
    )
except Exception:
    subir_pdf_a_drive_oauth = None
    eliminar_archivo_drive_oauth = None


logger = logging.getLogger(__name__)

ESTADO_ERROR = ESTADO_ERROR_GENERACION

DRIVE_EXPIRACION_HORAS = 72
LOCK_STALE_MINUTES = 45


# =========================================================
# VALIDACION FUERTE DE JSON OPENAI PARA PRODUCCION
# =========================================================

SECCIONES_OPENAI_OBLIGATORIAS = [
    "mensaje_alma",
    "origen_nombre",
    "linaje_apellidos",
    "esencia",
    "energia",
    "zodiaco",
    "zodiaco_chino",
    "numerologia",
    "animal_espiritual",
    "angel_guardian",
    "piedra_energetica",
    "dones",
    "sombras",
    "herida",
    "proposito",
    "amor_vinculos",
    "dinero_camino",
    "ritual_personalizado",
    "afirmaciones",
    "mensaje_final",
    "esencia_alma",
]

CAMPOS_OPENAI_OBLIGATORIOS = [
    "primera_lectura",
    "profundizacion",
    "integracion",
]

PREFIJOS_JSON_NO_FINALES = (
    "PARCIAL_",
    "RESCATE_",
    "OK_SECCION_",
    "ERROR_GLOBAL_",
)

TIPOS_JSON_NO_FINALES = (
    "parcial",
    "rescate",
    "error",
)


# =========================================================
# HELPERS
# =========================================================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _db_placeholder() -> str:
    # El proyecto escribe SQL interno con ?. app.db.execute convierte ? -> %s
    # automáticamente cuando DATABASE_URL apunta a PostgreSQL.
    return "?"


def _execute(db, sql: str, params: tuple = ()):  # db se conserva por compatibilidad interna
    return database.execute(sql, params)


def _commit(db):  # db se conserva por compatibilidad interna
    database.commit()


def _rollback(db):  # db se conserva por compatibilidad interna
    database.rollback()


def _fetchone_dict(cursor) -> Optional[Dict[str, Any]]:
    row = cursor.fetchone()
    if row is None:
        return None

    try:
        return dict(row)
    except Exception:
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, row))


def _fetchall_dict(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    if not rows:
        return []

    result = []
    for row in rows:
        try:
            result.append(dict(row))
        except Exception:
            columns = [col[0] for col in cursor.description]
            result.append(dict(zip(columns, row)))
    return result


def _row_to_dict(row: Any) -> Dict[str, Any]:
    try:
        return dict(row)
    except Exception:
        return {k: row[k] for k in row.keys()}


def _column_exists(db, table: str, column: str) -> bool:
    """
    Compatibilidad defensiva para SQLite/PostgreSQL.
    Se mantiene por si alguna ruta antigua llama esta función, pero las
    actualizaciones nuevas pasan por app.db.update_pedido_campos().
    """
    try:
        if str(type(db)).lower().find("psycopg2") >= 0:
            cur = database.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = ? AND column_name = ?
                LIMIT 1
                """,
                (table, column),
            )
            return cur.fetchone() is not None

        cur = db.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = []
        for r in cur.fetchall():
            try:
                cols.append(r["name"])
            except Exception:
                cols.append(r[1])
        return column in cols
    except Exception:
        logger.debug("No se pudo verificar columna %s.%s", table, column, exc_info=True)
        return False


def _safe_update_pedido(order_id: int, campos: Dict[str, Any]) -> None:
    """
    Actualiza pedidos usando app.db como única capa oficial.

    Conserva compatibilidad con nombres antiguos que aparecían en este módulo:
    - updated_at / actualizado_en: app.db ya actualiza actualizado_en automáticamente.
    - error_message: se guarda como error.
    - pdf_url: se guarda como drive_download_link, que es la columna real actual.
    - Campos de Drive/lock se actualizan si existen en db.py corregido.
    """
    if not campos:
        return

    normalizados: Dict[str, Any] = {}
    clear_error = False

    for col, val in campos.items():
        if col in {"updated_at", "actualizado_en"}:
            continue
        if col == "error_message":
            col = "error"
        elif col == "pdf_url":
            col = "drive_download_link"
        elif col == "download_link":
            col = "drive_download_link"

        if col == "error" and val is None:
            clear_error = True
            continue

        normalizados[col] = val

    if not normalizados and not clear_error:
        logger.debug("No hay campos reales para actualizar pedido #%s", order_id)
        return

    database.update_pedido_campos(int(order_id), clear_error=clear_error, **normalizados)



def _database_url_is_postgres() -> bool:
    """Detecta si estamos usando Supabase/PostgreSQL sin depender de funciones privadas de db.py."""
    url = (os.getenv("DATABASE_URL") or "").strip().lower()
    return url.startswith("postgresql://") or url.startswith("postgres://")


def _json_compacto(data: Any) -> str:
    """Serializa JSON de forma segura para guardarlo en DB."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _guardar_contenido_openai_final_db(order_id: int, contenido: Dict[str, Any]) -> None:
    """
    Guarda el JSON FINAL de OpenAI en la tabla pedidos.

    Esto evita depender del disco temporal de Render. Si Render reinicia o haces deploy,
    el retry puede reutilizar contenido_openai desde Supabase y NO volver a gastar OpenAI.

    Requiere columna:
    - PostgreSQL/Supabase: contenido_openai JSONB
    - SQLite/local: contenido_openai TEXT
    """
    try:
        if not isinstance(contenido, dict):
            return

        valido, motivo = _json_openai_final_valido(contenido)
        if not valido:
            logger.warning(
                "No se guarda contenido_openai pedido #%s porque no es final: %s",
                order_id,
                motivo,
            )
            return

        payload = _json_compacto(contenido)

        if _database_url_is_postgres():
            database.execute(
                """
                UPDATE pedidos
                SET contenido_openai = ?::jsonb,
                    actualizado_en = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (payload, int(order_id)),
            )
        else:
            database.execute(
                """
                UPDATE pedidos
                SET contenido_openai = ?,
                    actualizado_en = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (payload, int(order_id)),
            )

        database.commit()
        logger.info("JSON FINAL OpenAI guardado en DB pedido #%s", order_id)

    except Exception:
        # No debe romper el flujo: si falla guardar JSON, todavía puede generar/subir PDF.
        logger.exception("No se pudo guardar contenido_openai en DB pedido #%s", order_id)

def _project_root() -> Path:
    return Path(current_app.root_path).resolve().parent


# =========================================================
# PEDIDOS
# =========================================================

def obtener_pedido(order_id: int) -> Optional[Dict[str, Any]]:
    row = database.get_pedido_by_id(int(order_id))
    if row is None:
        return None
    pedido = _row_to_dict(row)
    # Alias de lectura para funciones antiguas que esperaban pdf_url.
    if not pedido.get("pdf_url"):
        pedido["pdf_url"] = (
            pedido.get("drive_download_link")
            or pedido.get("drive_view_link")
        )
    return pedido


def marcar_estado(order_id: int, estado: str, error: Optional[str] = None) -> None:
    database.update_estado_pedido(
        int(order_id),
        estado,
        error=str(error) if error else None,
    )


def marcar_pedido_pagado(order_id: int) -> None:
    marcar_estado(order_id, ESTADO_PAGADO)


def marcar_completado(order_id: int) -> None:
    marcar_estado(order_id, ESTADO_COMPLETADO)


def marcar_error(order_id: int, error: str) -> None:
    marcar_estado(order_id, ESTADO_ERROR, error)


def _normalizar_pedido_para_pdf(pedido: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(pedido)

    data.setdefault("pedido_id", pedido.get("id"))
    data.setdefault("order_id", pedido.get("id"))

    if "nombre" not in data or not data.get("nombre"):
        data["nombre"] = (
            pedido.get("nombre_cliente")
            or pedido.get("first_name")
            or pedido.get("cliente_nombre")
            or ""
        )

    if "apellidos" not in data or not data.get("apellidos"):
        data["apellidos"] = (
            pedido.get("apellidos_cliente")
            or pedido.get("last_name")
            or pedido.get("cliente_apellidos")
            or ""
        )

    if "fecha_nacimiento" not in data or not data.get("fecha_nacimiento"):
        data["fecha_nacimiento"] = (
            pedido.get("birth_date")
            or pedido.get("fecha")
            or pedido.get("nacimiento")
            or ""
        )

    if "sexo" not in data or not data.get("sexo"):
        data["sexo"] = (
            pedido.get("genero")
            or pedido.get("gender")
            or ""
        )

    return data


# =========================================================
# REUTILIZACION DE JSON OPENAI
# =========================================================

def _extraer_secciones_openai(data: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return None

    secciones = (
        data.get("secciones")
        or data.get("secciones_editoriales")
        or data.get("contenido_openai")
    )

    if isinstance(secciones, dict):
        return secciones

    # Compatibilidad defensiva: algunos contenidos antiguos podían venir
    # directamente como diccionario de secciones.
    if any(k in data for k in SECCIONES_OPENAI_OBLIGATORIAS):
        return data

    return None


def _json_openai_final_valido(data: Any) -> tuple[bool, str]:
    """
    Regla de producción:
    - Solo se reutiliza JSON FINAL completo.
    - Nunca se reutiliza PARCIAL, RESCATE, OK_SECCION ni ERROR_GLOBAL.
    - Si falta una sección o un campo, se llama OpenAI de nuevo.
    """
    if not isinstance(data, dict):
        return False, "JSON no es dict."

    tipo = str(data.get("tipo") or data.get("version") or "").lower()
    if any(palabra in tipo for palabra in TIPOS_JSON_NO_FINALES):
        return False, f"JSON no final por tipo/version: {tipo}"

    if data.get("faltantes"):
        return False, f"JSON declara faltantes: {data.get('faltantes')}"

    secciones = _extraer_secciones_openai(data)
    if not isinstance(secciones, dict) or not secciones:
        return False, "JSON no contiene secciones válidas."

    faltantes: list[str] = []
    campos_invalidos: list[str] = []

    for sec in SECCIONES_OPENAI_OBLIGATORIAS:
        node = secciones.get(sec)
        if not isinstance(node, dict):
            faltantes.append(sec)
            continue

        for campo in CAMPOS_OPENAI_OBLIGATORIOS:
            valor = str(node.get(campo) or "").strip()
            if len(valor) < 40:
                campos_invalidos.append(f"{sec}.{campo}")

    if faltantes:
        return False, "Faltan secciones obligatorias: " + ", ".join(faltantes)

    if campos_invalidos:
        return False, "Campos vacíos/cortos: " + ", ".join(campos_invalidos[:8])

    return True, "ok"


def _path_json_openai_permitido(path: Path) -> tuple[bool, str]:
    nombre = path.name

    if nombre.startswith(PREFIJOS_JSON_NO_FINALES):
        return False, f"Archivo no final por prefijo: {nombre}"

    if nombre.upper().startswith("PARCIAL"):
        return False, f"Archivo parcial rechazado: {nombre}"

    return True, "ok"


def _cargar_json_si_existe(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists() or not path.is_file():
            return None

        permitido, motivo_path = _path_json_openai_permitido(path)
        if not permitido:
            logger.warning(
                "JSON OpenAI ignorado para producción: %s (%s)",
                path,
                motivo_path,
            )
            return None

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        valido, motivo = _json_openai_final_valido(data)
        if valido:
            logger.info("JSON OpenAI FINAL reutilizado desde: %s", path)
            return data

        logger.warning(
            "JSON OpenAI ignorado porque no está completo: %s (%s)",
            path,
            motivo,
        )

    except Exception:
        logger.exception("No se pudo leer/validar JSON existente: %s", path)

    return None


def _buscar_json_openai_guardado(order_id: int, pedido: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Busca contenido OpenAI ya guardado para NO gastar saldo otra vez.

    Protección de producción:
    - Solo reutiliza JSON final completo.
    - Ignora PARCIAL_ / RESCATE_ / OK_SECCION_ / ERROR_GLOBAL_.
    - Si falta una sección obligatoria, NO lo usa y permite llamar OpenAI.
    """

    posibles_columnas = [
        "contenido_openai",
        "openai_json",
        "json_openai",
        "contenido_json",
        "json_guardado",
    ]

    for col in posibles_columnas:
        value = pedido.get(col)

        if not value:
            continue

        if isinstance(value, dict):
            valido, motivo = _json_openai_final_valido(value)
            if valido:
                logger.info("Contenido OpenAI FINAL reutilizado desde columna DB: %s", col)
                return value
            logger.warning(
                "Contenido OpenAI en columna %s ignorado porque no está completo: %s",
                col,
                motivo,
            )
            continue

        if isinstance(value, str):
            text = value.strip()

            if not text:
                continue

            if text.startswith("{"):
                try:
                    data = json.loads(text)
                    valido, motivo = _json_openai_final_valido(data)
                    if valido:
                        logger.info("Contenido OpenAI FINAL reutilizado desde JSON DB: %s", col)
                        return data
                    logger.warning(
                        "JSON OpenAI en DB ignorado porque no está completo (%s): %s",
                        col,
                        motivo,
                    )
                except Exception:
                    logger.warning("No se pudo interpretar JSON en columna DB: %s", col)
                continue

            posible_path = Path(text)
            if not posible_path.is_absolute():
                posible_path = _project_root() / posible_path

            data = _cargar_json_si_existe(posible_path)
            if data:
                return data

    root = _project_root()

    posibles_paths = [
        root / "output" / "json_openai" / f"openai_pedido_{order_id}.json",
        root / "output" / "json" / f"pedido_{order_id}.json",
        root / "output" / "json" / f"mapa_alma_{order_id}.json",
        root / "output" / "openai" / f"pedido_{order_id}.json",
        root / "output" / "openai" / f"mapa_alma_{order_id}.json",
        root / "output" / "contenido" / f"pedido_{order_id}.json",
        root / "output" / "contenido_openai" / f"pedido_{order_id}.json",
        root / "output" / f"pedido_{order_id}.json",
        root / "output" / f"mapa_alma_{order_id}.json",
    ]

    for path in posibles_paths:
        data = _cargar_json_si_existe(path)
        if data:
            return data

    output_dir = root / "output"

    try:
        if output_dir.exists():
            patrones = [
                f"*{order_id}*.json",
                f"pedido_{order_id}_*.json",
                f"mapa_alma_{order_id}_*.json",
                f"openai_pedido_{order_id}*.json",
            ]

            candidatos: list[Path] = []
            for patron in patrones:
                candidatos.extend(output_dir.rglob(patron))

            # Prioriza archivos finales conocidos; deja últimos los candidatos dudosos.
            candidatos = sorted(
                set(candidatos),
                key=lambda p: (
                    p.name.startswith(PREFIJOS_JSON_NO_FINALES),
                    -p.stat().st_mtime if p.exists() else 0,
                ),
            )

            for path in candidatos:
                data = _cargar_json_si_existe(path)
                if data:
                    return data
    except Exception:
        logger.exception("Error buscando JSON OpenAI guardado para pedido #%s", order_id)

    return None


def _asegurar_contenido_openai(data_pdf: Dict[str, Any], pedido: Dict[str, Any]) -> Dict[str, Any]:
    """
    Regla de oro:
    - Si ya existe contenido FINAL completo, reutilizar.
    - Si existe JSON guardado FINAL completo, reutilizar.
    - Si existe JSON parcial/corrupto/incompleto, ignorar y llamar OpenAI.
    - Nunca generar PDF con contenido incompleto.
    """

    order_id = int(data_pdf.get("pedido_id") or data_pdf.get("id") or pedido.get("id"))

    if data_pdf.get("contenido_openai"):
        valido, motivo = _json_openai_final_valido(data_pdf.get("contenido_openai"))
        if valido:
            logger.info("Pedido #%s ya trae contenido_openai FINAL. No se llama OpenAI.", order_id)
            _guardar_contenido_openai_final_db(order_id, data_pdf.get("contenido_openai"))
            return data_pdf
        logger.warning(
            "Pedido #%s trae contenido_openai incompleto. Se ignorará y se llamará OpenAI: %s",
            order_id,
            motivo,
        )
        data_pdf.pop("contenido_openai", None)

    if data_pdf.get("secciones"):
        candidato = {"secciones": data_pdf.get("secciones")}
        valido, motivo = _json_openai_final_valido(candidato)
        if valido:
            logger.info("Pedido #%s trae secciones completas. No se llama OpenAI.", order_id)
            data_pdf["contenido_openai"] = candidato
            _guardar_contenido_openai_final_db(order_id, candidato)
            return data_pdf
        logger.warning(
            "Pedido #%s trae secciones incompletas. Se ignorarán y se llamará OpenAI: %s",
            order_id,
            motivo,
        )
        data_pdf.pop("secciones", None)

    contenido_guardado = _buscar_json_openai_guardado(order_id, pedido)

    if contenido_guardado:
        valido, motivo = _json_openai_final_valido(contenido_guardado)
        if not valido:
            # Doble candado. En teoría no debería llegar aquí.
            logger.warning(
                "JSON encontrado para pedido #%s fue rechazado en doble validación: %s",
                order_id,
                motivo,
            )
        else:
            data_pdf["contenido_openai"] = contenido_guardado
            data_pdf["_reutilizado"] = True
            _guardar_contenido_openai_final_db(order_id, contenido_guardado)
            return data_pdf

    if generar_contenido_mapa is None:
        raise RuntimeError(
            "No se pudo importar app.openai_generator.generar_contenido_mapa."
        )

    logger.warning(
        "Pedido #%s NO tiene JSON FINAL completo. Se llamará OpenAI para generar contenido válido.",
        order_id,
    )

    # Fuerza que app.openai_generator no intente reutilizar nada viejo si el pedido
    # venía de un error por contenido incompleto.
    data_pdf["force_regenerate"] = bool(data_pdf.get("force_regenerate") or data_pdf.get("regenerar"))

    contenido = generar_contenido_mapa(data_pdf)

    valido, motivo = _json_openai_final_valido(contenido)
    if not valido:
        raise RuntimeError(
            "OpenAI devolvió contenido incompleto. No se genera PDF malo. "
            f"Motivo: {motivo}"
        )

    _guardar_contenido_openai_final_db(order_id, contenido)

    data_pdf["contenido_openai"] = contenido
    data_pdf["_reutilizado"] = bool(
        isinstance(contenido, dict) and contenido.get("_reutilizado")
    )

    return data_pdf



def _adquirir_lock_procesamiento(order_id: int) -> bool:
    try:
        if hasattr(database, "acquire_processing_lock"):
            return bool(database.acquire_processing_lock(int(order_id), stale_after_minutes=LOCK_STALE_MINUTES))
    except Exception:
        logger.exception("No se pudo adquirir lock de procesamiento pedido #%s", order_id)
        return False

    # Fallback defensivo si db.py viejo sigue cargado.
    try:
        pedido = obtener_pedido(order_id)
        if pedido and int(pedido.get("processing_lock") or 0) == 1:
            return False
        _safe_update_pedido(order_id, {"processing_lock": 1, "processing_started_at": _iso(_utc_now())})
        return True
    except Exception:
        logger.exception("Fallback lock falló pedido #%s", order_id)
        return False


def _liberar_lock_procesamiento(order_id: int) -> None:
    try:
        if hasattr(database, "release_processing_lock"):
            database.release_processing_lock(int(order_id))
            return
        _safe_update_pedido(order_id, {"processing_lock": 0, "processing_started_at": None})
    except Exception:
        logger.exception("No se pudo liberar lock de procesamiento pedido #%s", order_id)


def _marcar_error_pipeline(order_id: int, estado: str, error: Exception | str) -> None:
    mensaje = str(error)[:2000]
    try:
        _safe_update_pedido(
            order_id,
            {
                "estado": estado,
                "error": mensaje,
            },
        )
    except Exception:
        logger.exception("No se pudo marcar error pipeline pedido #%s", order_id)


def _error_drive(mensaje: str) -> RuntimeError:
    return RuntimeError(f"ERROR_DRIVE: {mensaje}")

# =========================================================
# GOOGLE DRIVE
# =========================================================

def _crear_link_local(order_id: int) -> str:
    base_url = (
        current_app.config.get("PUBLIC_BASE_URL")
        or current_app.config.get("BASE_URL")
        or ""
    )

    base_url = str(base_url).rstrip("/")

    if base_url:
        return f"{base_url}/descarga/{order_id}"

    return f"/descarga/{order_id}"


def _subir_pdf_drive_seguro(
    pdf_path: str,
    order_id: int,
) -> Dict[str, Any]:

    if subir_pdf_a_drive_oauth is None:
        raise _error_drive("Google Drive OAuth no disponible. No se puede entregar link real al cliente.")

    archivo = Path(pdf_path)

    if not archivo.exists():
        raise FileNotFoundError(f"No existe el PDF para subir a Drive: {pdf_path}")

    nombre_drive = f"mapa_alma_{order_id}.pdf"

    resultado = subir_pdf_a_drive_oauth(str(archivo), nombre_drive)

    if not isinstance(resultado, dict):
        raise _error_drive(f"Respuesta inválida de Drive: {resultado}")

    file_id = resultado.get("file_id")
    download_link = resultado.get("download_link") or resultado.get("view_link")

    if not file_id or not download_link:
        raise _error_drive(f"Drive no devolvió file_id/download_link: {resultado}")

    logger.info("PDF subido a Drive correctamente. Pedido #%s file_id=%s", order_id, file_id)

    return {
        "file_id": file_id,
        "download_link": download_link,
        "view_link": resultado.get("view_link") or download_link,
        "name": resultado.get("name") or nombre_drive,
    }

def _pdf_local_existente(pedido: Dict[str, Any], order_id: int) -> Optional[Path]:
    posibles = []

    if pedido.get("pdf_path"):
        posibles.append(Path(str(pedido["pdf_path"])))

    posibles.append(_project_root() / "output" / f"mapa_alma_{order_id}.pdf")

    for path in posibles:
        if not path.is_absolute():
            path = _project_root() / path

        if path.exists() and path.is_file():
            return path

    return None


def _drive_link_vigente(pedido: Dict[str, Any]) -> bool:
    drive_file_id = pedido.get("drive_file_id")
    pdf_url = (
        pedido.get("pdf_url")
        or pedido.get("drive_download_link")
        or pedido.get("drive_view_link")
    )
    expires_at = _parse_datetime(pedido.get("drive_expires_at"))

    if not drive_file_id or not pdf_url or not expires_at:
        return False

    return expires_at > _utc_now()


def _guardar_drive_en_db(order_id: int, pdf_path: Path, drive_result: Dict[str, Any]) -> Dict[str, Any]:
    if not drive_result:
        raise _error_drive("No hay resultado de Drive. No se puede guardar entrega.")

    pdf_url = drive_result.get("download_link") or drive_result.get("view_link")
    drive_file_id = drive_result.get("file_id")

    if not drive_file_id or not pdf_url:
        raise _error_drive(f"Drive incompleto. file_id/link faltante: {drive_result}")

    uploaded_at = _utc_now()
    expires_at = uploaded_at + timedelta(hours=DRIVE_EXPIRACION_HORAS)

    _safe_update_pedido(
        order_id,
        {
            "estado": ESTADO_PDF_GENERADO,
            "pdf_path": str(pdf_path),
            "drive_file_id": drive_file_id,
            "drive_view_link": drive_result.get("view_link") or pdf_url,
            "drive_download_link": pdf_url,
            "drive_uploaded_at": _iso(uploaded_at),
            "drive_expires_at": _iso(expires_at),
            "drive_deleted_at": None,
            "drive_status": "active",
            "drive_delete_error": None,
            "error": None,
        },
    )

    return {
        "ok": True,
        "order_id": order_id,
        "pdf_path": str(pdf_path),
        "pdf_url": pdf_url,
        "drive_file_id": drive_file_id,
        "drive_uploaded_at": _iso(uploaded_at),
        "drive_expires_at": _iso(expires_at),
        "drive_usado": True,
    }


# =========================================================
# EMAILS
# =========================================================

def _enviar_email_cliente_seguro(
    pedido: Dict[str, Any],
    pdf_url: str,
) -> None:

    if enviar_email_pedido_completado is None:
        logger.warning(
            "Función enviar_email_pedido_completado no disponible."
        )
        return

    try:
        try:
            enviar_email_pedido_completado(
                pedido,
                pdf_url,
            )
        except TypeError:
            enviar_email_pedido_completado(
                email=(
                    pedido.get("email")
                    or pedido.get("cliente_email")
                    or pedido.get("correo")
                ),
                nombre=(
                    pedido.get("nombre")
                    or pedido.get("nombre_cliente")
                    or pedido.get("cliente_nombre")
                ),
                pdf_url=pdf_url,
                pedido=pedido,
            )

        logger.info(
            "Email enviado correctamente pedido #%s",
            pedido.get("id"),
        )

    except Exception as e:
        logger.exception(
            "Error enviando email cliente pedido #%s: %s",
            pedido.get("id"),
            e,
        )
        raise


def _notificar_admin_error(
    order_id: int,
    error: Exception,
) -> None:

    if enviar_email_admin_error is None:
        logger.warning(
            "No existe enviar_email_admin_error. Error pedido #%s: %s",
            order_id,
            error,
        )
        return

    try:
        try:
            enviar_email_admin_error(
                order_id,
                str(error),
            )
        except TypeError:
            enviar_email_admin_error(
                asunto=f"Error pedido #{order_id}",
                mensaje=str(error),
            )
    except Exception:
        logger.exception("Falló email de error admin.")


# =========================================================
# GENERAR PDF AUTOMATICO
# =========================================================

def generar_pdf_automatico(order_id: int, forzar_regeneracion: bool = False) -> Dict[str, Any]:
    """
    Genera o recupera PDF y SIEMPRE exige Drive real para considerarlo entregable.

    Reglas de producción:
    - PDF local existente + Drive vigente: reutiliza todo.
    - PDF local existente sin Drive vigente: NO llama OpenAI; solo reintenta Drive.
    - Si Drive falla: estado error_envio y NO se completa el pedido.
    - No hay fallback local para cliente.
    """

    pedido = obtener_pedido(order_id)
    if not pedido:
        raise ValueError(f"No existe el pedido #{order_id}")

    pdf_existente = _pdf_local_existente(pedido, order_id)

    if not forzar_regeneracion and pdf_existente and _drive_link_vigente(pedido):
        logger.info("Pedido #%s ya tiene PDF y Drive vigente. No se llama OpenAI.", order_id)
        return {
            "ok": True,
            "order_id": order_id,
            "pdf_path": str(pdf_existente),
            "pdf_url": pedido.get("pdf_url"),
            "drive_file_id": pedido.get("drive_file_id"),
            "drive_expires_at": pedido.get("drive_expires_at"),
            "drive_usado": True,
            "reutilizado": True,
            "sin_openai": True,
        }

    if not forzar_regeneracion and pdf_existente:
        logger.info("Pedido #%s tiene PDF local. Reintentando solo subida Drive.", order_id)
        try:
            drive_result = _subir_pdf_drive_seguro(str(pdf_existente), order_id)
            resultado = _guardar_drive_en_db(order_id, pdf_existente, drive_result)
            resultado["reutilizado"] = True
            resultado["sin_openai"] = True
            return resultado
        except Exception as exc:
            _marcar_error_pipeline(order_id, ESTADO_ERROR_ENVIO, exc)
            _notificar_admin_error(order_id, exc)
            raise

    marcar_estado(order_id, ESTADO_GENERANDO_PDF)

    try:
        logger.info("Generando PDF pedido #%s", order_id)

        data_pdf = _normalizar_pedido_para_pdf(pedido)
        data_pdf = _asegurar_contenido_openai(data_pdf, pedido)

        resultado_pdf = generar_pdf_desde_tienda(data_pdf)

        if isinstance(resultado_pdf, dict):
            pdf_path = (
                resultado_pdf.get("pdf_path")
                or resultado_pdf.get("path")
                or resultado_pdf.get("archivo")
                or resultado_pdf.get("ruta")
            )
        else:
            pdf_path = str(resultado_pdf)

        if not pdf_path:
            raise RuntimeError(f"El generador PDF no devolvió ruta válida: {resultado_pdf}")

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"El PDF generado no existe: {pdf_path}")

        try:
            drive_result = _subir_pdf_drive_seguro(str(pdf_file), order_id)
        except Exception as exc:
            _safe_update_pedido(
                order_id,
                {
                    "estado": ESTADO_ERROR_ENVIO,
                    "pdf_path": str(pdf_file),
                    "drive_status": "upload_error",
                    "error": str(exc)[:2000],
                },
            )
            _notificar_admin_error(order_id, exc)
            raise

        resultado = _guardar_drive_en_db(order_id, pdf_file, drive_result)
        resultado["reutilizado"] = bool(data_pdf.get("_reutilizado"))
        resultado["sin_openai"] = bool(data_pdf.get("_reutilizado"))
        return resultado

    except Exception as e:
        _rollback(get_db())
        if str(e).startswith("ERROR_DRIVE"):
            _marcar_error_pipeline(order_id, ESTADO_ERROR_ENVIO, e)
        else:
            _marcar_error_pipeline(order_id, ESTADO_ERROR_GENERACION, e)
        _notificar_admin_error(order_id, e)
        logger.exception("Error generando/subiendo PDF pedido #%s", order_id)
        raise


# =========================================================
# POST PAGO / STRIPE
# =========================================================

def procesar_post_pago(order_id: int) -> Dict[str, Any]:
    pedido = obtener_pedido(order_id)

    if not pedido:
        raise ValueError(f"No existe el pedido #{order_id}")

    estado = pedido.get("estado")

    if estado == ESTADO_COMPLETADO:
        logger.info("procesar_post_pago omitido: pedido #%s ya está completado.", order_id)
        return {
            "ok": True,
            "omitido": True,
            "order_id": order_id,
            "estado": estado,
            "motivo": "Pedido ya completado",
        }

    estados_validos = {
        ESTADO_PENDIENTE_PAGO,
        ESTADO_PAGADO,
        ESTADO_PDF_GENERADO,
        ESTADO_PDF_GENERADO_PENDIENTE_DE_LINK,
        ESTADO_ERROR_ENVIO,
        ESTADO_ERROR_GENERACION,
    }

    if estado in {ESTADO_GENERANDO_PDF, ESTADO_ENVIANDO_EMAIL}:
        return {
            "ok": False,
            "omitido": True,
            "order_id": order_id,
            "estado": estado,
            "motivo": "Pedido ya está en proceso",
        }

    if estado not in estados_validos:
        logger.warning("procesar_post_pago omitido: pedido #%s estado=%s", order_id, estado)
        return {
            "ok": False,
            "omitido": True,
            "order_id": order_id,
            "estado": estado,
            "motivo": "Estado no procesable",
        }

    if not _adquirir_lock_procesamiento(order_id):
        logger.warning("procesar_post_pago omitido: pedido #%s bloqueado por otro proceso", order_id)
        return {
            "ok": False,
            "omitido": True,
            "order_id": order_id,
            "estado": estado,
            "motivo": "Pedido bloqueado por procesamiento en curso",
        }

    try:
        logger.info("Procesando post-pago pedido #%s", order_id)
        marcar_estado(order_id, ESTADO_PAGADO)

        resultado_pdf = generar_pdf_automatico(order_id)
        pedido_actualizado = obtener_pedido(order_id) or pedido

        pdf_url = resultado_pdf.get("pdf_url") or pedido_actualizado.get("pdf_url")
        drive_file_id = resultado_pdf.get("drive_file_id") or pedido_actualizado.get("drive_file_id")
        drive_expires_at = resultado_pdf.get("drive_expires_at") or pedido_actualizado.get("drive_expires_at")

        if not pdf_url or not drive_file_id or not drive_expires_at:
            raise _error_drive(
                f"Entrega Drive incompleta. pdf_url={bool(pdf_url)} file_id={bool(drive_file_id)} expires={bool(drive_expires_at)}"
            )

        marcar_estado(order_id, ESTADO_ENVIANDO_EMAIL)

        try:
            _enviar_email_cliente_seguro(pedido_actualizado, pdf_url)
        except Exception as exc:
            _marcar_error_pipeline(order_id, ESTADO_ERROR_ENVIO, exc)
            _notificar_admin_error(order_id, exc)
            raise

        _safe_update_pedido(
            order_id,
            {
                "estado": ESTADO_COMPLETADO,
                "error": None,
            },
        )

        logger.info("Pedido #%s completado correctamente.", order_id)

        return {
            "ok": True,
            "order_id": order_id,
            "estado": ESTADO_COMPLETADO,
            "pdf_url": pdf_url,
            "drive_file_id": drive_file_id,
            "drive_expires_at": drive_expires_at,
            "drive_usado": True,
            "sin_openai": resultado_pdf.get("sin_openai"),
            "reutilizado": resultado_pdf.get("reutilizado"),
        }

    except Exception as e:
        _rollback(get_db())
        if str(e).startswith("ERROR_DRIVE"):
            _marcar_error_pipeline(order_id, ESTADO_ERROR_ENVIO, e)
        elif obtener_pedido(order_id) and (obtener_pedido(order_id) or {}).get("pdf_path"):
            _marcar_error_pipeline(order_id, ESTADO_ERROR_ENVIO, e)
        else:
            _marcar_error_pipeline(order_id, ESTADO_ERROR_GENERACION, e)
        _notificar_admin_error(order_id, e)
        logger.exception("Error procesando post pago pedido #%s", order_id)
        raise
    finally:
        _liberar_lock_procesamiento(order_id)


# =========================================================
# REGENERAR PDF
# =========================================================

def regenerar_pdf_pedido(order_id: int, forzar_openai: bool = False) -> Dict[str, Any]:
    """
    Para admin.

    Por defecto NO fuerza OpenAI:
    - si hay PDF existente, reutiliza
    - si hay JSON guardado, reutiliza
    - solo si no hay nada, llama OpenAI

    Si algún día quieres generar texto nuevo de cero:
    regenerar_pdf_pedido(order_id, forzar_openai=True)
    """

    pedido = obtener_pedido(order_id)

    if not pedido:
        raise ValueError(f"No existe el pedido #{order_id}")

    viejo_drive_file_id = pedido.get("drive_file_id")

    if viejo_drive_file_id and eliminar_archivo_drive_oauth:
        try:
            eliminar_archivo_drive_oauth(viejo_drive_file_id)
            logger.info(
                "Archivo Drive anterior eliminado pedido #%s",
                order_id,
            )
        except Exception:
            logger.exception(
                "No se pudo eliminar archivo Drive anterior pedido #%s",
                order_id,
            )

    _safe_update_pedido(
        order_id,
        {
            "drive_file_id": None,
            "drive_view_link": None,
            "drive_download_link": None,
            "drive_expires_at": None,
            "drive_uploaded_at": None,
            "drive_deleted_at": None,
            "drive_status": "none",
            "drive_delete_error": None,
            "estado": ESTADO_PAGADO,
        },
    )

    return generar_pdf_automatico(order_id, forzar_regeneracion=forzar_openai)


# =========================================================
# PEDIDOS ATASCADOS
# =========================================================

def detectar_pedidos_atascados(minutos: int = 30, timeout_minutes: Optional[int] = None) -> List[Dict[str, Any]]:
    if timeout_minutes is not None:
        minutos = int(timeout_minutes)
    limite = _utc_now() - timedelta(minutes=minutos)
    limite_iso = _iso(limite)

    try:
        rows = database.pedidos_atascados_en_estado(
            [ESTADO_GENERANDO_PDF],
            antes_de_iso=limite_iso,
            limit=100,
        )
        pedidos = [_row_to_dict(row) for row in rows]

        logger.info("Pedidos atascados detectados: %s", len(pedidos))
        return pedidos

    except Exception:
        logger.exception("Error detectando pedidos atascados.")
        return []


def resetear_pedido_atascado(order_id: int) -> None:
    marcar_estado(order_id, ESTADO_PAGADO)


def limpiar_pedidos_atascados(minutos: int = 30) -> List[Dict[str, Any]]:
    pedidos = detectar_pedidos_atascados(minutos=minutos)

    for pedido in pedidos:
        pedido_id = pedido.get("id")
        if pedido_id:
            try:
                resetear_pedido_atascado(int(pedido_id))
            except Exception:
                logger.exception(
                    "No se pudo resetear pedido atascado #%s",
                    pedido_id,
                )

    return pedidos


# =========================================================
# REENVIAR NOTIFICACIONES
# =========================================================

def reenviar_notificaciones_pedido(order_id: int) -> Dict[str, Any]:
    pedido = obtener_pedido(order_id)

    if not pedido:
        raise ValueError(f"No existe el pedido #{order_id}")

    if not _drive_link_vigente(pedido):
        raise RuntimeError(
            f"El pedido #{order_id} no tiene un enlace Drive vigente. Usa reintentar post-pago para subir a Drive y enviar."
        )

    pdf_url = (
        pedido.get("pdf_url")
        or pedido.get("drive_download_link")
        or pedido.get("drive_view_link")
    )

    if not pdf_url:
        raise RuntimeError(f"El pedido #{order_id} no tiene link de Drive para reenviar.")

    try:
        _enviar_email_cliente_seguro(pedido, pdf_url)

        logger.info("Notificación reenviada correctamente pedido #%s", order_id)

        return {
            "ok": True,
            "cliente": True,
            "order_id": order_id,
            "pdf_url": pdf_url,
            "mensaje": "Notificación reenviada correctamente.",
        }

    except Exception as e:
        _marcar_error_pipeline(order_id, ESTADO_ERROR_ENVIO, e)
        _notificar_admin_error(order_id, e)
        logger.exception("Error reenviando notificación pedido #%s", order_id)
        raise


def reenviar_email_pedido(order_id: int) -> Dict[str, Any]:
    return reenviar_notificaciones_pedido(order_id)


def enviar_notificaciones_pedido(order_id: int) -> Dict[str, Any]:
    return reenviar_notificaciones_pedido(order_id)


def enviar_link_pedido(order_id: int) -> Dict[str, Any]:
    return reenviar_notificaciones_pedido(order_id)
