from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def _ok(label: str, detail: object = "") -> None:
    suffix = f" - {detail}" if detail else ""
    print(f"[OK] {label}{suffix}")


def _fail(label: str, exc: BaseException) -> None:
    print(f"[FAIL] {label}: {exc}")
    raise SystemExit(1) from exc


def check_imports() -> None:
    try:
        import cloudinary  # noqa: F401
        import fitz  # noqa: F401
        import openai
        import pypdf  # noqa: F401

        from app import create_app  # noqa: F401
        from app import google_drive_oauth, order_services, pdf_generator  # noqa: F401

        _ok("imports criticos", f"openai {openai.__version__}")
    except Exception as exc:  # noqa: BLE001
        _fail("imports criticos", exc)


def check_env_presence() -> None:
    keys = [
        "OPENAI_API_KEY",
        "STRIPE_PUBLIC_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "EMAIL_SENDER",
        "EMAIL_PASSWORD",
        "ADMIN_EMAIL",
        "GOOGLE_DRIVE_FOLDER_ID",
    ]
    missing = [key for key in keys if not (os.getenv(key) or "").strip()]
    if missing:
        raise SystemExit(f"[FAIL] faltan variables: {', '.join(missing)}")
    _ok("variables criticas presentes")


def check_drive_files() -> None:
    paths = [
        PROJECT_ROOT / "secrets" / "google_drive_oauth_client.json",
        PROJECT_ROOT / "secrets" / "google_drive_token.json",
    ]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit(f"[FAIL] faltan archivos Drive: {', '.join(missing)}")
    _ok("archivos Drive presentes")


def check_database() -> None:
    from app import create_app
    from app import db as database

    app = create_app()
    with app.app_context():
        database.init_db()

    db_path = PROJECT_ROOT / "instance" / "tienda.sqlite"
    if not db_path.exists():
        raise SystemExit(f"[FAIL] no existe DB: {db_path}")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    columns = {row["name"] for row in con.execute("PRAGMA table_info(pedidos)")}
    required = {
        "id",
        "nombre",
        "apellidos",
        "email",
        "fecha_nacimiento",
        "idioma",
        "estado",
        "pdf_path",
        "drive_file_id",
        "drive_view_link",
        "drive_download_link",
        "drive_uploaded_at",
        "drive_expires_at",
        "drive_status",
        "contenido_openai",
        "tipo_producto",
        "es_regalo",
        "dedicatoria",
        "tracking_number",
        "shipping_carrier",
        "printed_at",
        "shipped_at",
        "precio_centavos",
        "promocion_codigo",
        "promocion_precio_centavos",
        "processing_lock",
        "processing_started_at",
        "error",
        "creado_en",
        "actualizado_en",
    }
    missing = sorted(required - columns)
    if missing:
        raise SystemExit(f"[FAIL] faltan columnas pedidos: {', '.join(missing)}")

    count = con.execute("SELECT count(*) FROM pedidos").fetchone()[0]
    _ok("base de datos", f"{count} pedido(s)")


def check_promo_state() -> None:
    from app import create_app
    from app import db as database

    app = create_app()
    with app.app_context():
        database.init_db()
        promo = database.get_promocion_inicio_estado()

    required = {
        "limite",
        "restantes",
        "activa",
        "precio_normal_centavos",
        "precio_promo_centavos",
        "precio_actual_centavos",
    }
    missing = sorted(required - set(promo))
    if missing:
        raise SystemExit(f"[FAIL] faltan claves promo: {', '.join(missing)}")
    if int(promo["limite"]) != 25:
        raise SystemExit(f"[FAIL] limite promo inesperado: {promo['limite']}")
    if int(promo["precio_normal_centavos"]) != 2222:
        raise SystemExit("[FAIL] precio normal promo inesperado")
    if int(promo["precio_promo_centavos"]) != 1111:
        raise SystemExit("[FAIL] precio 11:11 inesperado")
    if not 0 <= int(promo["restantes"]) <= int(promo["limite"]):
        raise SystemExit(f"[FAIL] cupos promo fuera de rango: {promo['restantes']}")

    _ok("promocion 11:11", f"quedan {promo['restantes']} de {promo['limite']}")


def check_checkout_promo_price() -> None:
    test_dir = PROJECT_ROOT / "output" / "smoke_tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / f"promo_checkout_{os.getpid()}.sqlite"

    old_db_path = os.environ.get("SQLITE_DATABASE_PATH")
    os.environ["SQLITE_DATABASE_PATH"] = str(test_db)

    from app import create_app
    from app import db as database
    from app import routes

    captured: dict = {}

    class FakeCheckoutSession:
        id = "cs_test_promo_1111"
        url = "https://checkout.stripe.test/promo-1111"

    original_create = routes.stripe.checkout.Session.create

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeCheckoutSession()

    routes.stripe.checkout.Session.create = fake_create
    try:
        app = create_app()
        with app.app_context():
            database.init_db()

        client = app.test_client()
        response = client.post(
            "/crear-checkout-session",
            data={
                "nombre": "Prueba",
                "apellidos": "Promocion",
                "email": "promo@example.com",
                "email_confirm": "promo@example.com",
                "idioma": "en",
                "tipo_producto": "digital",
                "acepta": "1",
                "acepta_digital": "1",
            },
            follow_redirects=False,
        )
        if response.status_code != 303:
            raise SystemExit(f"[FAIL] checkout promo devolvio {response.status_code}")

        unit_amount = captured["line_items"][0]["price_data"]["unit_amount"]
        if unit_amount != 1111:
            raise SystemExit(f"[FAIL] Stripe recibio {unit_amount}, esperaba 1111")

        metadata = captured.get("metadata") or {}
        if metadata.get("promocion_codigo") != database.PROMO_INICIO_CODIGO:
            raise SystemExit("[FAIL] checkout no incluyo codigo de promocion")
        if metadata.get("idioma") != "en":
            raise SystemExit("[FAIL] checkout no incluyo idioma del pedido")
        if metadata.get("tipo_producto") != "digital":
            raise SystemExit("[FAIL] checkout no incluyo tipo_producto digital")

        with app.app_context():
            promo = database.get_promocion_inicio_estado()
            pedido = database.list_pedidos(limit=1)[0]

        if int(promo["restantes"]) != 24:
            raise SystemExit(f"[FAIL] contador promo no bajo a 24: {promo['restantes']}")
        if int(pedido["precio_centavos"]) != 1111:
            raise SystemExit(f"[FAIL] pedido guardo precio inesperado: {pedido['precio_centavos']}")
        if pedido["idioma"] != "en":
            raise SystemExit(f"[FAIL] pedido guardo idioma inesperado: {pedido['idioma']}")
        if pedido["tipo_producto"] != "digital":
            raise SystemExit(f"[FAIL] pedido guardo tipo_producto inesperado: {pedido['tipo_producto']}")

        _ok("checkout promocional", "Stripe recibio 1111 centavos y quedan 24 de 25")
    finally:
        routes.stripe.checkout.Session.create = original_create
        if old_db_path is None:
            os.environ.pop("SQLITE_DATABASE_PATH", None)
        else:
            os.environ["SQLITE_DATABASE_PATH"] = old_db_path


def check_checkout_sold_out_price() -> None:
    test_dir = PROJECT_ROOT / "output" / "smoke_tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / f"promo_sold_out_{os.getpid()}.sqlite"

    old_db_path = os.environ.get("SQLITE_DATABASE_PATH")
    os.environ["SQLITE_DATABASE_PATH"] = str(test_db)

    from app import create_app
    from app import db as database
    from app import routes

    captured: dict = {}

    class FakeCheckoutSession:
        id = "cs_test_normal_2222"
        url = "https://checkout.stripe.test/normal-2222"

    original_create = routes.stripe.checkout.Session.create

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeCheckoutSession()

    routes.stripe.checkout.Session.create = fake_create
    try:
        app = create_app()
        with app.app_context():
            database.init_db()
            for index in range(database.PROMO_INICIO_LIMITE):
                database.insert_pedido(
                    nombre="Promo",
                    apellidos=f"Agotada {index}",
                    email=f"agotada{index}@example.com",
                    estado="pagado",
                    precio_centavos=database.PROMO_PRECIO_CENTAVOS,
                    promocion_codigo=database.PROMO_INICIO_CODIGO,
                    promocion_precio_centavos=database.PROMO_PRECIO_CENTAVOS,
                )
            promo = database.get_promocion_inicio_estado()

        if promo["activa"] or int(promo["restantes"]) != 0:
            raise SystemExit(f"[FAIL] promo agotada esperaba 0 cupos: {promo}")

        client = app.test_client()
        response = client.post(
            "/crear-checkout-session",
            data={
                "nombre": "Prueba",
                "apellidos": "Normal",
                "email": "normal@example.com",
                "email_confirm": "normal@example.com",
                "acepta": "1",
                "acepta_digital": "1",
            },
            follow_redirects=False,
        )
        if response.status_code != 303:
            raise SystemExit(f"[FAIL] checkout normal devolvio {response.status_code}")

        unit_amount = captured["line_items"][0]["price_data"]["unit_amount"]
        if unit_amount != 2222:
            raise SystemExit(f"[FAIL] Stripe recibio {unit_amount}, esperaba 2222")
        metadata = captured.get("metadata") or {}
        if metadata.get("promocion_codigo"):
            raise SystemExit("[FAIL] checkout agotado aun incluyo codigo de promocion")

        _ok("checkout agotado", "Stripe vuelve a 2222 centavos cuando quedan 0 cupos")
    finally:
        routes.stripe.checkout.Session.create = original_create
        if old_db_path is None:
            os.environ.pop("SQLITE_DATABASE_PATH", None)
        else:
            os.environ["SQLITE_DATABASE_PATH"] = old_db_path


def check_checkout_printed_product() -> None:
    test_dir = PROJECT_ROOT / "output" / "smoke_tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / f"printed_checkout_{os.getpid()}.sqlite"

    old_db_path = os.environ.get("SQLITE_DATABASE_PATH")
    os.environ["SQLITE_DATABASE_PATH"] = str(test_db)

    from app import create_app
    from app import db as database
    from app import routes

    captured: dict = {}

    class FakeCheckoutSession:
        id = "cs_test_printed"
        url = "https://checkout.stripe.test/printed"

    original_create = routes.stripe.checkout.Session.create

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeCheckoutSession()

    routes.stripe.checkout.Session.create = fake_create
    try:
        app = create_app()
        with app.app_context():
            database.init_db()

        client = app.test_client()
        response = client.post(
            "/crear-checkout-session",
            data={
                "nombre": "Prueba",
                "apellidos": "Impresa",
                "email": "impresa@example.com",
                "email_confirm": "impresa@example.com",
                "tipo_producto": "impreso",
                "es_regalo": "1",
                "dedicatoria": "Con amor para una persona especial.",
                "acepta": "1",
                "acepta_digital": "1",
            },
            follow_redirects=False,
        )
        if response.status_code != 303:
            raise SystemExit(f"[FAIL] checkout impreso devolvio {response.status_code}")

        unit_amount = captured["line_items"][0]["price_data"]["unit_amount"]
        if unit_amount != database.PRECIO_IMPRESO_CENTAVOS:
            raise SystemExit(
                f"[FAIL] Stripe impreso recibio {unit_amount}, esperaba {database.PRECIO_IMPRESO_CENTAVOS}"
            )
        metadata = captured.get("metadata") or {}
        if metadata.get("tipo_producto") != "impreso":
            raise SystemExit("[FAIL] checkout impreso no incluyo tipo_producto")
        if metadata.get("promocion_codigo"):
            raise SystemExit("[FAIL] checkout impreso no debe consumir promoción digital")

        with app.app_context():
            pedido = database.list_pedidos(limit=1)[0]
        if pedido["tipo_producto"] != "impreso" or not pedido["es_regalo"] or not pedido["dedicatoria"]:
            raise SystemExit("[FAIL] pedido impreso no guardo producto/regalo/dedicatoria")

        _ok("checkout impreso", f"Stripe recibio {database.PRECIO_IMPRESO_CENTAVOS} centavos y guardo dedicatoria")
    finally:
        routes.stripe.checkout.Session.create = original_create
        if old_db_path is None:
            os.environ.pop("SQLITE_DATABASE_PATH", None)
        else:
            os.environ["SQLITE_DATABASE_PATH"] = old_db_path


def check_routes() -> None:
    from app import create_app

    app = create_app()
    client = app.test_client()

    public_paths = [
        "/",
        "/pedido",
        "/que-es",
        "/vista-previa",
        "/incluye",
        "/preguntas",
        "/resenas",
        "/privacidad",
        "/condiciones",
        "/contacto",
        "/health",
    ]
    for path in public_paths:
        response = client.get(path)
        if response.status_code != 200:
            raise SystemExit(f"[FAIL] {path} devolvio {response.status_code}")

    with client.session_transaction() as session:
        session["admin_ok"] = True

    admin_paths = [
        "/admin/pedidos",
        "/admin/completados",
        "/admin/impresos",
        "/admin/resenas",
    ]
    for path in admin_paths:
        response = client.get(path)
        if response.status_code != 200:
            raise SystemExit(f"[FAIL] {path} devolvio {response.status_code}")

    _ok("rutas publicas/admin")


def check_pdf_generation() -> None:
    from app.pdf_generator import generar_pdf_desde_tienda
    from pypdf import PdfReader

    json_path = PROJECT_ROOT / "output" / "json_openai" / "openai_pedido_50.json"
    if not json_path.exists():
        _ok("pdf local", "omitido: no existe JSON de prueba")
        return

    # Confirm JSON can be parsed before passing it to the PDF generator.
    json.loads(json_path.read_text(encoding="utf-8"))

    output_dir = PROJECT_ROOT / "output" / "smoke_tests"
    data = {
        "pedido_id": 990052,
        "nombre": "Valentina",
        "apellidos": "Garcia Rivera",
        "fecha_nacimiento": "1995-08-22",
        "email": "prueba@example.com",
        "sexo": "femenino",
        "contenido_openai_path": str(json_path),
        "output_dir": str(output_dir),
    }
    pdf_path = Path(generar_pdf_desde_tienda(data))
    reader = PdfReader(str(pdf_path))
    if len(reader.pages) < 20:
        raise SystemExit(f"[FAIL] PDF con pocas paginas: {len(reader.pages)}")

    dedicatoria = (
        "Desde el día que llegaste a nuestras vidas llenaste todo de luz. "
        "Nunca olvides lo especial que eres.\n\nCon amor,\nMamá"
    )
    gift_data = {
        **data,
        "pedido_id": 990053,
        "es_regalo": True,
        "dedicatoria": dedicatoria,
    }
    gift_pdf_path = Path(generar_pdf_desde_tienda(gift_data))
    gift_reader = PdfReader(str(gift_pdf_path))
    if len(gift_reader.pages) != len(reader.pages):
        raise SystemExit(
            "[FAIL] La dedicatoria no debe agregar paginas: "
            f"sin regalo={len(reader.pages)}, con regalo={len(gift_reader.pages)}"
        )
    first_pages_text = "\n".join((gift_reader.pages[i].extract_text() or "") for i in range(min(2, len(gift_reader.pages))))
    if "Desde el día" not in first_pages_text and "Desde el dia" not in first_pages_text:
        raise SystemExit("[FAIL] La dedicatoria no aparece en la pagina personalizada del PDF")

    _ok("pdf local", f"{pdf_path.name}, {len(reader.pages)} paginas; dedicatoria sin paginas extra")


def main() -> int:
    check_imports()
    check_env_presence()
    check_drive_files()
    check_database()
    check_promo_state()
    check_checkout_promo_price()
    check_checkout_sold_out_price()
    check_checkout_printed_product()
    check_routes()
    check_pdf_generation()
    print("[OK] smoke check completo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
