"""
Rutas HTTP de la tienda: inicio, pedido, gracias y panel admin.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from functools import wraps
from typing import Optional

import stripe
from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    has_app_context,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import db as database
from app import email_service
from app.review_token import pedido_id_desde_token, token_para_pedido
from app.stripe_env import load_stripe_from_disk
from app.formulario_cliente import (
    FORMAS_TRATO_OPCIONES,
    etiqueta_forma_trato,
    normalizar_forma_trato,
)
from app.order_services import (
    detectar_pedidos_atascados,
    procesar_post_pago,
    reenviar_notificaciones_pedido,
)
from app.order_states import (
    ESTADO_COMPLETADO,
    ESTADO_ERROR_GENERACION,
    ESTADO_ERROR_ENVIO,
    ESTADO_ENVIANDO_EMAIL,
    ESTADO_GENERANDO_PDF,
    ESTADO_PAGADO,
    ESTADO_PDF_GENERADO,
    ESTADO_PENDIENTE_PAGO,
    ESTADO_REVISION_MANUAL,
    ORDER_STATES,
    estado_valido,
    etiqueta_estado,
)

bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)

ADMIN_MAIN_STATES = (
    ESTADO_PENDIENTE_PAGO,
    ESTADO_PAGADO,
    ESTADO_GENERANDO_PDF,
    ESTADO_ERROR_GENERACION,
    ESTADO_PDF_GENERADO,
    ESTADO_ENVIANDO_EMAIL,
    ESTADO_ERROR_ENVIO,
    ESTADO_REVISION_MANUAL,
)

DELETABLE_STATES = (
    ESTADO_COMPLETADO,
    ESTADO_ERROR_GENERACION,
    ESTADO_ERROR_ENVIO,
    ESTADO_REVISION_MANUAL,
)


def admin_required(view):
    """Decorador: exige sesión de administrador para ver el panel."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_ok"):
            return redirect(url_for("main.admin_login"))
        return view(*args, **kwargs)

    return wrapped


def _stripe_keys() -> tuple[str, str]:
    """
    Claves Stripe para checkout: `app.config` y, si faltan, relectura del `.env` en disco
    (por si el proceso arrancó sin claves y luego se editó el archivo, o hubo desajuste).
    """
    sk, pk = "", ""
    if has_app_context():
        sk = (current_app.config.get("STRIPE_SECRET_KEY") or "").strip()
        pk = (current_app.config.get("STRIPE_PUBLIC_KEY") or "").strip()
    if not sk:
        sk = (os.environ.get("STRIPE_SECRET_KEY") or "").strip()
    if not pk:
        pk = (
            (os.environ.get("STRIPE_PUBLIC_KEY") or "").strip()
            or (os.environ.get("STRIPE_PUBLISHABLE_KEY") or "").strip()
        )
    if not sk or not pk:
        sk2, pk2, _ = load_stripe_from_disk()
        if not sk:
            sk = sk2
        if not pk:
            pk = pk2
    return sk, pk


def _stripe_config_ok() -> bool:
    sk, pk = _stripe_keys()
    return bool(sk and pk)


def _render_pedido_form(**ctx):
    base = {
        "formas_trato_opciones": FORMAS_TRATO_OPCIONES,
        "forma_trato_selected": "",
        "acepta_prev": False,
        "acepta_digital_prev": False,
    }
    base.update(ctx)
    return render_template("pedido.html", **base)


def _crear_checkout_desde_form():
    nombre = (request.form.get("nombre") or "").strip()
    apellidos = (request.form.get("apellidos") or "").strip()
    email = (request.form.get("email") or "").strip()
    email_confirm = (request.form.get("email_confirm") or "").strip()
    fecha_nacimiento_raw = (request.form.get("fecha_nacimiento") or "").strip()
    forma_raw = request.form.get("forma_trato")
    acepta = request.form.get("acepta")
    acepta_digital = request.form.get("acepta_digital")

    errores = []
    if len(nombre) < 1:
        errores.append("Indica tu nombre.")
    if len(apellidos) < 1:
        errores.append("Indica tus apellidos.")
    if "@" not in email or "." not in email.split("@")[-1]:
        errores.append("Indica un correo electrónico válido.")
    if email.casefold() != email_confirm.casefold():
        errores.append("El correo y la confirmación no coinciden.")
    if not acepta:
        errores.append(
            "Debes marcar la casilla de confirmación de datos y autorización para crear tu contenido personalizado."
        )
    if not acepta_digital:
        errores.append(
            "Debes marcar la casilla que acepta las condiciones del producto digital (sin cambios, cancelaciones ni reembolsos tras iniciar la creación)."
        )

    fecha_nacimiento: Optional[str] = None
    if fecha_nacimiento_raw:
        try:
            datetime.strptime(fecha_nacimiento_raw, "%Y-%m-%d")
            fecha_nacimiento = fecha_nacimiento_raw
        except ValueError:
            errores.append("La fecha de nacimiento no es válida.")

    forma_norm = normalizar_forma_trato(forma_raw)
    if (forma_raw or "").strip() and forma_norm is None:
        errores.append("Selecciona una opción válida para el tratamiento.")

    if errores:
        for e in errores:
            flash(e, "error")
        return _render_pedido_form(
            nombre=nombre,
            apellidos=apellidos,
            email=email,
            email_confirm=email_confirm,
            fecha_nacimiento=fecha_nacimiento_raw,
            forma_trato_selected=forma_norm or "",
            acepta_prev=bool(acepta),
            acepta_digital_prev=bool(acepta_digital),
        )

    nuevo_id = database.insert_pedido(
        nombre=nombre,
        apellidos=apellidos,
        email=email,
        fecha_nacimiento=fecha_nacimiento,
        forma_trato=forma_norm,
    )

    if not _stripe_config_ok():
        flash(
            "Pago aún no configurado (faltan claves Stripe en .env o no se leyeron). "
            "Tu pedido quedó en pendiente de pago. Abre en el navegador (con Flask en modo debug): "
            f"{url_for('main.salud_stripe', _external=True)}",
            "error",
        )
        return redirect(url_for("main.gracias", pedido_id=nuevo_id))

    sk, _pk = _stripe_keys()
    stripe.api_key = sk
    # Stripe sustituye {CHECKOUT_SESSION_ID}; al volver del pago podemos disparar post-pago aquí
    # si el webhook aún no llegó (típico en local sin `stripe listen`).
    success_base = url_for("main.gracias", pedido_id=nuevo_id, _external=True)
    sep = "&" if "?" in success_base else "?"
    success_url = f"{success_base}{sep}session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = url_for("main.pedido", _external=True)

    try:
        # Nombre `checkout_session`: no usar `session` (choca con la sesión de Flask).
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            # Evita crear Customer de Stripe salvo que haga falta (menos “recordar” tarjeta en cuenta Stripe).
            customer_creation="if_required",
            # Solo tarjeta: no activa Link como método explícito (el “guardar para después” suele venir de Link / navegador).
            payment_method_types=["card"],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=email,
            metadata={
                "pedido_id": str(nuevo_id),
                "nombre": nombre,
                "apellidos": apellidos,
                "email": email,
            },
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Mapa del Alma"},
                        "unit_amount": 100,
                    },
                    "quantity": 1,
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        flash(f"No se pudo iniciar el checkout con Stripe: {exc}", "error")
        return _render_pedido_form(
            nombre=nombre,
            apellidos=apellidos,
            email=email,
            email_confirm=email_confirm,
            fecha_nacimiento=fecha_nacimiento_raw,
            forma_trato_selected=forma_norm or "",
            acepta_prev=bool(acepta),
            acepta_digital_prev=bool(acepta_digital),
        )

    return redirect(checkout_session.url, code=303)


@bp.route("/privacidad")
def legal_privacidad():
    """Página básica de privacidad (texto orientativo)."""
    return render_template("legal_privacidad.html")


@bp.route("/condiciones")
def legal_condiciones():
    """Página básica de condiciones (texto orientativo)."""
    return render_template("legal_condiciones.html")


@bp.route("/contacto")
def legal_contacto():
    """Contacto público (usa el email admin configurado)."""
    whatsapp_phone = (os.environ.get("PUBLIC_WHATSAPP_PHONE") or "").strip()
    whatsapp_href = ""
    if whatsapp_phone:
        digits = "".join(ch for ch in whatsapp_phone if ch.isdigit())
        if digits:
            whatsapp_href = f"https://wa.me/{digits}"

    instagram_url = (os.environ.get("PUBLIC_INSTAGRAM_URL") or "").strip()

    return render_template(
        "legal_contacto.html",
        support_email=email_service.get_email_sender(),
        admin_email=email_service.get_admin_email(),
        whatsapp_href=whatsapp_href,
        instagram_url=instagram_url,
    )


@bp.route("/.well-known/security.txt")
def well_known_security_txt():
    """
    Punto de contacto estándar para reportes de seguridad.
    https://securitytxt.org/
    """
    admin_mail = email_service.get_admin_email()
    body = (
        "Contact: mailto:{mail}\n"
        "Preferred-Languages: es\n"
        "Canonical: {canonical}\n"
    ).format(mail=admin_mail, canonical=url_for("main.well_known_security_txt", _external=True))
    return Response(body, mimetype="text/plain; charset=utf-8")


@bp.route("/robots.txt")
def robots_txt():
    """Evita indexar el panel admin en buscadores (orientativo)."""
    lines = [
        "User-agent: *",
        "Disallow: /admin",
        "Disallow: /stripe-webhook",
        "",
    ]
    return Response("\n".join(lines), mimetype="text/plain; charset=utf-8")


@bp.route("/")
def index():
    """Página de inicio con presentación de la tienda y el producto principal."""
    reales_rows = database.list_resenas_aprobadas_todas()
    resenas_reales: list[dict] = []
    for r in reales_rows:
        resenas_reales.append(dict(r))

    resenas_carousel_slides: list[list[dict]] = []
    chunk: list[dict] = []
    for r in resenas_reales:
        chunk.append(r)
        if len(chunk) == 4:
            resenas_carousel_slides.append(chunk)
            chunk = []
    if chunk:
        resenas_carousel_slides.append(chunk)

    resenas_resumen = None
    total_count, avg = database.resumen_resenas_aprobadas()
    if total_count > 0:
        avg_round = round(float(avg) + 1e-9, 1)
        full = int(avg_round)
        frac = avg_round - full
        has_half = frac >= 0.25 and frac < 0.75
        if frac >= 0.75 and full < 5:
            full += 1
            has_half = False
        outline = max(0, 5 - full - (1 if has_half else 0))
        resenas_resumen = {
            "count": int(total_count),
            "avg": avg_round,
            "full": min(5, full),
            "half": bool(has_half),
            "outline": min(5, outline),
        }

    return render_template(
        "index.html",
        resenas_aprobadas=resenas_reales,
        resenas_resumen=resenas_resumen,
        resenas_carousel_slides=resenas_carousel_slides,
    )


@bp.route("/resena/<token>", methods=["GET", "POST"])
def dejar_resena(token: str):
    """
    Formulario público de reseña verificada: enlace firmado + pedido completado + email coincide con el pedido.
    Las reseñas quedan en moderación (pendiente) hasta que el admin apruebe.
    """
    pid = pedido_id_desde_token(token, current_app.secret_key)
    if pid is None:
        flash("El enlace no es válido o ha caducado. Si necesitas ayuda, escríbenos.", "error")
        return redirect(url_for("main.index"))

    pedido = database.get_pedido_by_id(pid)
    if pedido is None:
        abort(404)

    if pedido["estado"] != ESTADO_COMPLETADO:
        flash(
            "Solo pueden dejar reseña los clientes que ya recibieron su Mapa del Alma (pedido completado).",
            "error",
        )
        return redirect(url_for("main.index"))

    ya_bloqueada = database.resena_bloquea_nuevo_envio(pid)

    if request.method == "POST":
        if ya_bloqueada:
            flash("Este pedido ya tiene una reseña enviada o publicada.", "info")
            return redirect(url_for("main.index"))

        nombre = (request.form.get("nombre") or "").strip()
        email = (request.form.get("email") or "").strip()
        comentario = (request.form.get("comentario") or "").strip()
        try:
            rating = int(request.form.get("rating") or "0")
        except ValueError:
            rating = 0

        if len(nombre) < 1:
            flash("Indica tu nombre.", "error")
        elif email.casefold() != (pedido["email"] or "").strip().casefold():
            flash("El correo debe ser el mismo que usaste en el pedido.", "error")
        elif rating < 1 or rating > 5:
            flash("Elige una valoración de 1 a 5 estrellas.", "error")
        elif len(comentario) < 10:
            flash("Escribe un comentario un poco más largo (al menos 10 caracteres).", "error")
        elif len(comentario) > 2000:
            flash("El comentario es demasiado largo (máximo 2000 caracteres).", "error")
        else:
            database.insert_resena(
                pedido_id=pid,
                nombre_cliente=nombre,
                email_cliente=email,
                rating=rating,
                comentario=comentario,
            )
            flash(
                "Gracias. Tu reseña se ha enviado y la revisaremos antes de publicarla en la web.",
                "success",
            )
            return redirect(url_for("main.index"))

    return render_template(
        "resena.html",
        token=token,
        pedido=pedido,
        ya_enviada=ya_bloqueada,
        nombre_default=(pedido["nombre"] or "").strip(),
        email_default=(pedido["email"] or "").strip(),
    )


@bp.route("/pedido", methods=["GET", "POST"])
def pedido():
    """
    Formulario de pedido para "Mapa del Alma".

    GET: muestra el formulario.
    POST: valida, guarda en SQLite y redirige a la página de gracias.
    """
    if request.method == "POST":
        return _crear_checkout_desde_form()
    return _render_pedido_form()


@bp.route("/crear-checkout-session", methods=["POST"])
def crear_checkout_session():
    """
    Crea pedido en estado pendiente_pago y redirige a Stripe Checkout.
    """
    return _crear_checkout_desde_form()


def _sincronizar_post_pago_desde_return_stripe(pedido_id: int, stripe_session_id: str) -> None:
    """
    Si el cliente vuelve de Checkout con ?session_id=..., confirma el pago en la API
    y ejecuta el mismo flujo que el webhook (PDF + emails). Útil si el webhook no llegó (p. ej. local sin `stripe listen`).
    """
    sk, _ = _stripe_keys()
    if not sk or not stripe_session_id:
        return
    stripe.api_key = sk
    try:
        co = stripe.checkout.Session.retrieve(stripe_session_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo leer la sesión de Stripe en return_url: %s", exc)
        flash("No se pudo verificar el pago con Stripe. Si cobraron la tarjeta, conserva el recibo y escríbenos.", "error")
        return

    data = co.to_dict()
    if data.get("payment_status") != "paid":
        return

    meta = (data.get("metadata") or {}).get("pedido_id", "")
    if str(pedido_id) != str(meta):
        return

    row = database.get_pedido_by_id(pedido_id)
    if row is None:
        return

    if row["estado"] == ESTADO_COMPLETADO:
        flash("Tu pedido ya está listo; revisa tu correo (y la carpeta spam) por el PDF.", "info")
        return

    if row["estado"] in (ESTADO_ERROR_ENVIO, ESTADO_ERROR_GENERACION):
        flash(
            "Tu pago fue recibido, pero hubo un problema al generar o enviar el PDF. "
            "Te contactaremos para resolverlo. Si más tarde no ves nuestros correos, revisa también spam/correo no deseado.",
            "error",
        )
        return

    if row["estado"] in (ESTADO_PAGADO, ESTADO_GENERANDO_PDF, ESTADO_PDF_GENERADO, ESTADO_ENVIANDO_EMAIL):
        flash(
            "Pago confirmado. Estamos terminando tu pedido y te avisaremos por correo en breve. "
            "Si no lo encuentras, revisa también spam/correo no deseado.",
            "info",
        )
        return

    if row["estado"] != ESTADO_PENDIENTE_PAGO:
        flash(
            "Tu pedido está registrado y en revisión. Te enviaremos novedades por correo. "
            "Si no lo encuentras, revisa también spam/correo no deseado.",
            "info",
        )
        return

    try:
        procesar_post_pago(pedido_id, stripe_checkout_session_id=stripe_session_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error en post-pago desde return_url: %s", exc)
        flash(
            "El pago consta en Stripe, pero hubo un fallo al generar o enviar el PDF. "
            "Te contactaremos pronto o revisa el panel de administración.",
            "error",
        )
        return

    final = database.get_pedido_by_id(pedido_id)
    if final is None:
        return
    if final["estado"] == ESTADO_COMPLETADO:
        flash(
            "Pago recibido. Te hemos enviado el PDF a tu correo (revisa spam). "
            "Si no llega en unos minutos, escríbenos.",
            "success",
        )
        return
    if final["estado"] in (ESTADO_ERROR_ENVIO, ESTADO_ERROR_GENERACION):
        flash(
            "El pago está confirmado, pero hubo un problema al generar o enviar el PDF. "
            "Revisa tu correo más tarde o contacta con la tienda.",
            "error",
        )
        return
    flash("Pago registrado; estamos finalizando tu pedido.", "info")


def _resolver_pedido_desde_session_id(stripe_session_id: str) -> Optional[int]:
    """
    Intenta resolver `pedido_id` cuando en /gracias viene solo `session_id`.
    """
    sk, _ = _stripe_keys()
    if not sk or not stripe_session_id:
        return None
    stripe.api_key = sk
    try:
        co = stripe.checkout.Session.retrieve(stripe_session_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo resolver pedido desde session_id en /gracias: %s", exc)
        return None
    data = co.to_dict()
    return _resolve_pedido_id_from_checkout_session(data)


def _codigo_confirmacion_visible(pedido_id: Optional[int], stripe_session_id: str) -> str:
    """
    Devuelve siempre un código visible para la pantalla de gracias.
    - Si existe pedido_id: código oficial.
    - Si no: código provisional derivado de session_id.
    - Último fallback: código temporal.
    """
    if pedido_id:
        return database.codigo_confirmacion_pedido(pedido_id)

    token = "".join(ch for ch in str(stripe_session_id).upper() if ch.isalnum())
    if token:
        return f"MAPA-CHK-{token[-8:]}"

    return f"MAPA-PEND-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


@bp.route("/gracias")
def gracias():
    """Página de confirmación tras enviar el pedido o volver de Stripe Checkout."""
    pedido_id = request.args.get("pedido_id", type=int)
    stripe_session_id = (request.args.get("session_id") or "").strip()
    pedido_id_final = pedido_id

    if pedido_id_final is None and stripe_session_id:
        pedido_id_final = _resolver_pedido_desde_session_id(stripe_session_id)

    if pedido_id_final and stripe_session_id:
        _sincronizar_post_pago_desde_return_stripe(pedido_id_final, stripe_session_id)

    codigo_confirmacion = _codigo_confirmacion_visible(pedido_id_final, stripe_session_id)

    return render_template(
        "gracias.html",
        pedido_id=pedido_id_final,
        codigo_confirmacion=codigo_confirmacion,
    )


@bp.route("/salud/stripe")
def salud_stripe():
    """
    Solo desarrollo: indica si Flask ve las claves Stripe (sin exponer valores completos).
    """
    if not current_app.debug:
        abort(404)
    sk, pk = _stripe_keys()
    pref = sk[:10] if len(sk) >= 10 else ("(vacío)" if not sk else sk[:3] + "…")
    return jsonify(
        {
            "checkout_habilitado": bool(sk and pk),
            "tiene_clave_secreta": bool(sk),
            "tiene_clave_publica": bool(pk),
            "prefijo_clave_secreta": pref,
            "nota": "La clave secreta debe empezar por sk_test_ o sk_live_ (no rk_ restringida) para Checkout.",
        }
    )


def _stripe_session_customer_email(session_data: dict) -> str:
    """Email del comprador en Checkout (API Stripe checkout.Session)."""
    email = session_data.get("customer_email") or ""
    details = session_data.get("customer_details")
    if not email and isinstance(details, dict):
        email = details.get("email") or ""
    return str(email).strip()


def _resolve_pedido_id_from_checkout_session(session_data: dict) -> Optional[int]:
    """
    Prioridad: metadata `pedido_id` si el pedido existe; si no, último pendiente por email.
    """
    meta = session_data.get("metadata", {}) or {}
    raw = meta.get("pedido_id", "0")
    try:
        from_meta = int(raw)
    except (TypeError, ValueError):
        from_meta = 0

    if from_meta > 0:
        row = database.get_pedido_by_id(from_meta)
        if row is not None:
            return from_meta

    email = _stripe_session_customer_email(session_data)
    if not email:
        return None
    row = database.get_pedido_pendiente_por_email(email)
    return int(row["id"]) if row is not None else None


@bp.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    """
    Webhook de Stripe: solo con firma válida (`STRIPE_WEBHOOK_SECRET`).
    Si `checkout.session.completed` y pago confirmado, ejecuta `procesar_post_pago`
    (pagado → aviso admin → PDF → email cliente).
    """
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = ""
    if has_app_context():
        webhook_secret = (current_app.config.get("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not webhook_secret:
        webhook_secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()

    if not webhook_secret:
        logger.error("Webhook Stripe rechazado: STRIPE_WEBHOOK_SECRET no configurado.")
        return "webhook secret not configured", 503

    sk, _ = _stripe_keys()
    stripe.api_key = sk

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret,
        )
    except ValueError as exc:
        logger.error("Webhook Stripe payload invalido: %s", exc)
        return "invalid payload", 400
    except stripe.error.SignatureVerificationError as exc:
        logger.error("Webhook Stripe firma invalida: %s", exc)
        return "invalid signature", 400

    try:
        event_type = event["type"]
        session_obj = event["data"]["object"]
    except (TypeError, KeyError):
        return "", 200

    if event_type != "checkout.session.completed":
        return "", 200

    if hasattr(session_obj, "to_dict"):
        session_data = session_obj.to_dict()
    elif isinstance(session_obj, dict):
        session_data = session_obj
    else:
        session_data = {}
    if session_data.get("payment_status") != "paid":
        return "", 200

    try:
        pedido_id = _resolve_pedido_id_from_checkout_session(session_data)
        if pedido_id is None:
            return "", 200
        procesar_post_pago(
            pedido_id,
            stripe_checkout_session_id=session_data.get("id"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Webhook Stripe error en post-pago: %s", exc)

    return "", 200


@bp.route("/admin", methods=["GET", "POST"])
def admin_login():
    """
    Acceso simple al panel: contraseña configurada en FLASK_ADMIN_PASSWORD
    (por defecto en desarrollo: admin123 — cámbiala).
    """
    if request.method == "POST":
        pwd = request.form.get("password") or ""
        if pwd == current_app_password():
            session["admin_ok"] = True
            return redirect(url_for("main.admin_pedidos"))
        flash("Contraseña incorrecta.", "error")
    return render_template("admin/login.html")


def current_app_password():
    """Lee la contraseña admin desde la config de Flask (sin import circular)."""
    from flask import current_app

    return current_app.config.get("ADMIN_PASSWORD", "")


@bp.route("/admin/pedidos")
@admin_required
def admin_pedidos():
    """Bandeja principal: solo pedidos que requieren atención."""
    atascados = detectar_pedidos_atascados(timeout_minutes=20)
    if atascados > 0:
        flash(
            f"Se detectaron {atascados} pedido(s) atascados más de 20 min y se marcaron para revisión manual.",
            "error",
        )
    rows = database.list_pedidos_por_estados(ADMIN_MAIN_STATES)
    return render_template(
        "admin/pedidos.html",
        pedidos=rows,
        order_states=ORDER_STATES,
        etiqueta_estado=etiqueta_estado,
        etiqueta_forma_trato=etiqueta_forma_trato,
        deletable_states=DELETABLE_STATES,
        current_tab="pedidos",
        codigo_confirmacion_pedido=database.codigo_confirmacion_pedido,
    )


@bp.route("/admin/completados")
@admin_required
def admin_completados():
    """Vista separada con pedidos completados."""
    rows = database.list_pedidos_por_estados((ESTADO_COMPLETADO,))
    return render_template(
        "admin/completados.html",
        pedidos=rows,
        etiqueta_forma_trato=etiqueta_forma_trato,
        current_tab="completados",
        codigo_confirmacion_pedido=database.codigo_confirmacion_pedido,
    )


@bp.route("/admin/resenas")
@admin_required
def admin_resenas():
    """Moderación de reseñas: pendientes y historial."""
    rows = database.list_resenas_admin(limit=300)
    return render_template(
        "admin/resenas.html",
        resenas=rows,
        current_tab="resenas",
        RESENA_PENDIENTE=database.RESENA_ESTADO_PENDIENTE,
        RESENA_APROBADA=database.RESENA_ESTADO_APROBADA,
        RESENA_RECHAZADA=database.RESENA_ESTADO_RECHAZADA,
    )


@bp.route("/admin/resenas/<int:resena_id>/aprobar", methods=["POST"])
@admin_required
def admin_resena_aprobar(resena_id: int):
    row = database.get_resena_by_id(resena_id)
    if row is None:
        flash("Reseña no encontrada.", "error")
        return redirect(url_for("main.admin_resenas"))
    n = database.update_resena_estado(resena_id, database.RESENA_ESTADO_APROBADA)
    if n:
        flash(f"Reseña #{resena_id} aprobada y visible en la tienda.", "info")
    return redirect(url_for("main.admin_resenas"))


@bp.route("/admin/resenas/<int:resena_id>/rechazar", methods=["POST"])
@admin_required
def admin_resena_rechazar(resena_id: int):
    row = database.get_resena_by_id(resena_id)
    if row is None:
        flash("Reseña no encontrada.", "error")
        return redirect(url_for("main.admin_resenas"))
    n = database.update_resena_estado(resena_id, database.RESENA_ESTADO_RECHAZADA)
    if n:
        flash(f"Reseña #{resena_id} rechazada.", "info")
    return redirect(url_for("main.admin_resenas"))


@bp.route("/admin/resenas/<int:resena_id>/eliminar", methods=["POST"])
@admin_required
def admin_resena_eliminar(resena_id: int):
    row = database.get_resena_by_id(resena_id)
    if row is None:
        flash("Reseña no encontrada.", "error")
        return redirect(url_for("main.admin_resenas"))
    if row["estado"] != database.RESENA_ESTADO_APROBADA:
        flash("Solo puedes eliminar reseñas ya publicadas (aprobadas).", "error")
        return redirect(url_for("main.admin_resenas"))
    deleted = database.delete_resena(resena_id)
    if deleted:
        flash(f"Reseña #{resena_id} eliminada de la tienda.", "info")
    else:
        flash("No se pudo eliminar la reseña.", "error")
    return redirect(url_for("main.admin_resenas"))


@bp.route("/admin/pedidos/<int:pedido_id>", methods=["GET"])
@admin_required
def admin_pedido_detail(pedido_id: int):
    """Detalle de un pedido y acciones administrativas."""
    pedido = database.get_pedido_by_id(pedido_id)
    if pedido is None:
        flash("Pedido no encontrado.", "error")
        return redirect(url_for("main.admin_pedidos"))
    tab_param = (request.args.get("tab") or "").strip()
    if tab_param in ("pedidos", "completados"):
        current_tab = tab_param
    else:
        current_tab = "completados" if pedido["estado"] == ESTADO_COMPLETADO else "pedidos"
    back_url = url_for("main.admin_completados") if current_tab == "completados" else url_for("main.admin_pedidos")
    back_label = "Volver a completados" if current_tab == "completados" else "Volver a pedidos"
    resena_url = ""
    if pedido["estado"] == ESTADO_COMPLETADO:
        tok = token_para_pedido(pedido_id, current_app.secret_key)
        resena_url = url_for("main.dejar_resena", token=tok, _external=True)
    notificaciones = database.list_notificaciones_pedido(pedido_id, limit=200)
    can_reenviar_notificaciones = "main.admin_pedido_reenviar_notificaciones" in current_app.view_functions
    return render_template(
        "admin/pedido_detail.html",
        pedido=pedido,
        order_states=ORDER_STATES,
        etiqueta_estado=etiqueta_estado,
        etiqueta_forma_trato=etiqueta_forma_trato,
        back_url=back_url,
        back_label=back_label,
        current_tab=current_tab,
        resena_url=resena_url,
        notificaciones=notificaciones,
        can_reenviar_notificaciones=can_reenviar_notificaciones,
        codigo_confirmacion_pedido=database.codigo_confirmacion_pedido,
    )


@bp.route("/admin/pedidos/<int:pedido_id>/eliminar", methods=["POST"])
@admin_required
def admin_pedido_eliminar(pedido_id: int):
    """Elimina pedidos permitidos desde pedidos/completados."""
    pedido = database.get_pedido_by_id(pedido_id)
    tab = (request.form.get("tab") or "").strip()
    destino = "main.admin_completados" if tab == "completados" else "main.admin_pedidos"
    scroll_raw = (request.form.get("scroll_y") or "").strip()
    scroll_qs = scroll_raw if scroll_raw.isdigit() else ""

    def _back():
        if scroll_qs:
            return redirect(url_for(destino, scroll=scroll_qs))
        return redirect(url_for(destino))

    if pedido is None:
        flash("Pedido no encontrado.", "error")
        return _back()
    if pedido["estado"] not in DELETABLE_STATES:
        flash("Solo puedes eliminar pedidos completados, con error o en revisión manual.", "error")
        return _back()
    deleted = database.delete_pedido(pedido_id)
    if deleted:
        flash(f"Pedido #{pedido_id} eliminado correctamente.", "info")
    else:
        flash("No se pudo eliminar el pedido.", "error")
    return _back()


@bp.route("/admin/pedidos/<int:pedido_id>/estado", methods=["POST"])
@admin_required
def admin_pedido_estado(pedido_id: int):
    """Actualiza el estado manualmente desde un desplegable (lista o detalle)."""
    nuevo = (request.form.get("estado") or "").strip()
    if not estado_valido(nuevo):
        flash("Estado no válido.", "error")
        return redirect(admin_redirect_back(pedido_id))

    pedido = database.get_pedido_by_id(pedido_id)
    if pedido is None:
        flash("Pedido no encontrado.", "error")
        return redirect(url_for("main.admin_pedidos"))

    estado_anterior = pedido["estado"]
    database.update_pedido_campos(pedido_id, estado=nuevo, clear_error=False)

    # Si el admin marca manualmente un error, también disparamos aviso al admin
    # para mantener trazabilidad del incidente.
    if nuevo in (ESTADO_ERROR_GENERACION, ESTADO_ERROR_ENVIO) and estado_anterior != nuevo:
        pedido_actualizado = database.get_pedido_by_id(pedido_id)
        stage = "generacion_pdf" if nuevo == ESTADO_ERROR_GENERACION else "envio_email"
        motivo = (
            f"Cambio manual de estado desde admin: {estado_anterior} -> {nuevo}. "
            "Revisa el detalle del pedido para completar el diagnóstico."
        )
        ok = email_service.notify_admin_error(pedido_id, stage, motivo, pedido_actualizado)
        database.insert_notificacion(
            pedido_id=pedido_id,
            tipo=f"admin_error_manual_{stage}",
            canal="email",
            destinatario=email_service.get_admin_email(),
            estado="enviado" if ok else "error",
            error_message=motivo,
        )

    flash(f"Estado actualizado a: {etiqueta_estado(nuevo)}", "info")
    return redirect(admin_redirect_back(pedido_id))


@bp.route("/admin/pedidos/<int:pedido_id>/marcar-pagado", methods=["POST"])
@admin_required
def admin_pedido_marcar_pagado(pedido_id: int):
    """Marca el pedido como pagado (paso previo típico a generar PDF)."""
    if database.get_pedido_by_id(pedido_id) is None:
        flash("Pedido no encontrado.", "error")
        return redirect(url_for("main.admin_pedidos"))
    database.update_pedido_campos(pedido_id, estado=ESTADO_PAGADO, clear_error=True)
    flash("Pedido marcado como pagado.", "info")
    return redirect(url_for("main.admin_pedido_detail", pedido_id=pedido_id))


@bp.route("/admin/pedidos/<int:pedido_id>/marcar-revision-manual", methods=["POST"])
@admin_required
def admin_pedido_marcar_revision_manual(pedido_id: int):
    """Marca el pedido para seguimiento manual (fuera del flujo automático)."""
    if database.get_pedido_by_id(pedido_id) is None:
        flash("Pedido no encontrado.", "error")
        return redirect(url_for("main.admin_pedidos"))
    database.update_pedido_campos(pedido_id, estado=ESTADO_REVISION_MANUAL, clear_error=True)
    flash("Pedido marcado para revisión manual.", "info")
    return redirect(url_for("main.admin_pedido_detail", pedido_id=pedido_id))


@bp.route("/admin/pedidos/<int:pedido_id>/marcar-completado", methods=["POST"])
@admin_required
def admin_pedido_marcar_completado(pedido_id: int):
    """Marca el pedido como completado (cierre manual del caso)."""
    if database.get_pedido_by_id(pedido_id) is None:
        flash("Pedido no encontrado.", "error")
        return redirect(url_for("main.admin_pedidos"))
    database.update_pedido_campos(pedido_id, estado=ESTADO_COMPLETADO, clear_error=True)
    flash("Pedido marcado como completado.", "info")
    return redirect(url_for("main.admin_pedido_detail", pedido_id=pedido_id))


@bp.route("/admin/pedidos/<int:pedido_id>/reenviar-notificaciones", methods=["POST"])
@admin_required
def admin_pedido_reenviar_notificaciones(pedido_id: int):
    """Reenvía notificaciones relevantes según estado actual del pedido."""
    if database.get_pedido_by_id(pedido_id) is None:
        flash("Pedido no encontrado.", "error")
        return redirect(url_for("main.admin_pedidos"))
    try:
        resultados = reenviar_notificaciones_pedido(pedido_id)
    except Exception as exc:  # noqa: BLE001
        flash(f"No se pudieron reenviar notificaciones: {exc}", "error")
        return redirect(url_for("main.admin_pedido_detail", pedido_id=pedido_id))

    if not resultados:
        flash("No hubo notificaciones aplicables para reenviar con el estado actual.", "info")
        return redirect(url_for("main.admin_pedido_detail", pedido_id=pedido_id))

    ok_count = sum(1 for ok in resultados.values() if ok)
    total = len(resultados)
    if ok_count == total:
        flash(f"Reenvío completado ({ok_count}/{total}).", "success")
    else:
        flash(f"Reenvío parcial ({ok_count}/{total}); revisa historial para más detalle.", "error")
    return redirect(url_for("main.admin_pedido_detail", pedido_id=pedido_id))


def admin_redirect_back(pedido_id: int):
    """Tras actualizar estado: vuelve al detalle si la petición venía de ahí."""
    ref = (request.form.get("next") or "").strip()
    if ref == "detail":
        return url_for("main.admin_pedido_detail", pedido_id=pedido_id)
    return url_for("main.admin_pedidos")


@bp.route("/admin/salir")
def admin_logout():
    """Cierra la sesión de administrador."""
    session.pop("admin_ok", None)
    flash("Sesión de administración cerrada.", "info")
    return redirect(url_for("main.admin_login"))
