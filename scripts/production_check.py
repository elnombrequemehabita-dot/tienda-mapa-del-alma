from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

FAILURES: list[str] = []
WARNINGS: list[str] = []


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _ok(label: str, detail: str = "") -> None:
    detail = str(detail).replace("→", "->")
    suffix = f" - {detail}" if detail else ""
    print(f"[OK] {label}{suffix}")


def _warn(label: str, detail: str = "") -> None:
    detail = str(detail).replace("→", "->")
    suffix = f" - {detail}" if detail else ""
    WARNINGS.append(f"{label}{suffix}")
    print(f"[WARN] {label}{suffix}")


def _fail(label: str, detail: str = "") -> None:
    detail = str(detail).replace("→", "->")
    suffix = f" - {detail}" if detail else ""
    FAILURES.append(f"{label}{suffix}")
    print(f"[FAIL] {label}{suffix}")


def _stripe_mode(value: str) -> str:
    if value.startswith(("pk_live_", "sk_live_")) or "_live_" in value:
        return "live"
    if value.startswith(("pk_test_", "sk_test_")) or "_test_" in value:
        return "test"
    return "unknown"


def _any_env(keys: Iterable[str]) -> bool:
    return any(_env(key) for key in keys)


def check_core_env(strict_live: bool) -> None:
    secret = _env("SECRET_KEY") or _env("FLASK_SECRET_KEY")
    if not secret or secret in {"dev-secret-key-change-me", "pon_aqui_un_valor_largo_aleatorio"}:
        _fail("SECRET_KEY", "debe ser un valor largo y privado")
    elif len(secret) < 24:
        _warn("SECRET_KEY", "funciona, pero conviene usar 32+ caracteres")
    else:
        _ok("SECRET_KEY", "configurado")

    admin_password = _env("FLASK_ADMIN_PASSWORD") or _env("ADMIN_PASSWORD")
    if not admin_password or "pon_aqui" in admin_password:
        _fail("FLASK_ADMIN_PASSWORD", "faltante o placeholder")
    elif len(admin_password) < 10:
        _warn("FLASK_ADMIN_PASSWORD", "funciona, pero conviene usar 10+ caracteres")
    else:
        _ok("FLASK_ADMIN_PASSWORD", "configurado")

    public_base_url = _env("PUBLIC_BASE_URL")
    if not public_base_url and strict_live:
        _fail("PUBLIC_BASE_URL", "necesario para emails, reseñas y links públicos")
    elif not public_base_url:
        _warn("PUBLIC_BASE_URL", "faltante; en Render debe ser tu URL pública")
    elif strict_live and not public_base_url.startswith("https://"):
        _fail("PUBLIC_BASE_URL", "en producción debe empezar con https://")
    else:
        _ok("PUBLIC_BASE_URL", public_base_url)

    database_url = _env("DATABASE_URL")
    if not database_url:
        if strict_live:
            _fail("DATABASE_URL", "Render debe usar PostgreSQL/Supabase")
        else:
            _warn("DATABASE_URL", "local usa SQLite; Render debe usar PostgreSQL/Supabase")
    elif database_url.startswith(("postgresql://", "postgres://")):
        _ok("DATABASE_URL", "PostgreSQL configurado")
    else:
        _fail("DATABASE_URL", "debe ser PostgreSQL para Render")

    if strict_live and _env("SESSION_COOKIE_SECURE") != "1":
        _fail("SESSION_COOKIE_SECURE", "en Render debe ser 1")
    elif _env("SESSION_COOKIE_SECURE") == "1":
        _ok("SESSION_COOKIE_SECURE", "1")
    else:
        _warn("SESSION_COOKIE_SECURE", "en Render debe ser 1")

    if strict_live and _env("TRUSTED_PROXY_COUNT") != "1":
        _fail("TRUSTED_PROXY_COUNT", "en Render debe ser 1")
    elif _env("TRUSTED_PROXY_COUNT") == "1":
        _ok("TRUSTED_PROXY_COUNT", "1")
    else:
        _warn("TRUSTED_PROXY_COUNT", "en Render debe ser 1")

    max_content = _env("MAX_CONTENT_LENGTH") or "1000000"
    try:
        max_content_int = int(max_content)
    except ValueError:
        _fail("MAX_CONTENT_LENGTH", "debe ser número")
    else:
        if max_content_int < 100_000:
            _warn("MAX_CONTENT_LENGTH", "muy bajo; puede bloquear formularios normales")
        else:
            _ok("MAX_CONTENT_LENGTH", str(max_content_int))

    token_hours = _env("PDF_DOWNLOAD_TOKEN_MAX_AGE_HOURS") or "72"
    try:
        token_hours_int = int(token_hours)
    except ValueError:
        _fail("PDF_DOWNLOAD_TOKEN_MAX_AGE_HOURS", "debe ser número")
    else:
        if token_hours_int > 168:
            _warn("PDF_DOWNLOAD_TOKEN_MAX_AGE_HOURS", "recomendado 168 horas o menos")
        else:
            _ok("PDF_DOWNLOAD_TOKEN_MAX_AGE_HOURS", f"{token_hours_int}h")


def check_stripe(strict_live: bool) -> None:
    pk = _env("STRIPE_PUBLIC_KEY")
    sk = _env("STRIPE_SECRET_KEY")
    wh = _env("STRIPE_WEBHOOK_SECRET")
    if not pk:
        _fail("STRIPE_PUBLIC_KEY", "faltante")
    if not sk:
        _fail("STRIPE_SECRET_KEY", "faltante")
    if not wh:
        _fail("STRIPE_WEBHOOK_SECRET", "faltante")
    if not (pk and sk):
        return

    pk_mode = _stripe_mode(pk)
    sk_mode = _stripe_mode(sk)
    if pk_mode != sk_mode:
        _fail("Stripe", f"public key={pk_mode}, secret key={sk_mode}; deben coincidir")
    elif strict_live and pk_mode != "live":
        _fail("Stripe", "para vender real necesitas pk_live_ y sk_live_")
    else:
        _ok("Stripe", f"modo {pk_mode}")

    if wh.startswith("whsec_"):
        _ok("STRIPE_WEBHOOK_SECRET", "formato correcto")
    else:
        _warn("STRIPE_WEBHOOK_SECRET", "no empieza con whsec_")


def check_openai(strict_live: bool) -> None:
    if _env("OPENAI_API_KEY"):
        _ok("OPENAI_API_KEY", "configurado")
    else:
        _fail("OPENAI_API_KEY", "faltante")

    real_orders = _env("OPENAI_ENABLE_REAL_ORDERS").lower()
    enabled = real_orders in {"1", "true", "yes", "on", "si", "sí"}
    if strict_live and not enabled:
        _fail("OPENAI_ENABLE_REAL_ORDERS", "debe ser true para ventas automáticas")
    elif enabled:
        _ok("OPENAI_ENABLE_REAL_ORDERS", "true")
    else:
        _warn("OPENAI_ENABLE_REAL_ORDERS", "false: no hará llamadas reales")

    max_calls = _env("MAX_OPENAI_CALLS_PER_ORDER") or "3"
    try:
        max_calls_int = int(max_calls)
    except ValueError:
        _fail("MAX_OPENAI_CALLS_PER_ORDER", "debe ser número")
        return
    if max_calls_int > 3:
        _warn("MAX_OPENAI_CALLS_PER_ORDER", "recomendado 3 o menos")
    else:
        _ok("MAX_OPENAI_CALLS_PER_ORDER", str(max_calls_int))

    _ok("OPENAI_MODEL", _env("OPENAI_MODEL") or "gpt-4o-mini")


def check_email() -> None:
    if _env("EMAIL_SENDER"):
        _ok("EMAIL_SENDER", _env("EMAIL_SENDER"))
    else:
        _fail("EMAIL_SENDER", "faltante")

    if _env("ADMIN_EMAIL"):
        _ok("ADMIN_EMAIL", _env("ADMIN_EMAIL"))
    else:
        _fail("ADMIN_EMAIL", "faltante")

    if _env("BREVO_API_KEY"):
        _ok("BREVO_API_KEY", "configurado")
    elif _env("EMAIL_PASSWORD"):
        _ok("EMAIL_PASSWORD", "SMTP configurado")
    else:
        _fail("Email", "falta BREVO_API_KEY o EMAIL_PASSWORD")


def check_drive(strict_live: bool) -> None:
    if _env("GOOGLE_DRIVE_FOLDER_ID"):
        _ok("GOOGLE_DRIVE_FOLDER_ID", "configurado")
    else:
        _fail("GOOGLE_DRIVE_FOLDER_ID", "faltante")

    if _env("DISABLE_GOOGLE_DRIVE").lower() in {"1", "true", "yes", "on"}:
        _fail("DISABLE_GOOGLE_DRIVE", "no puede estar activo para ventas reales")
    else:
        _ok("DISABLE_GOOGLE_DRIVE", "inactivo")

    has_env_creds = _any_env(
        [
            "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON",
            "GOOGLE_DRIVE_CREDENTIALS_PATH",
            "GOOGLE_DRIVE_TOKEN_JSON",
            "GOOGLE_DRIVE_TOKEN_PATH",
        ]
    )
    has_local_oauth = (
        (PROJECT_ROOT / "secrets" / "google_drive_oauth_client.json").exists()
        and (PROJECT_ROOT / "secrets" / "google_drive_token.json").exists()
    )

    if has_env_creds:
        _ok("Google Drive credenciales", "configuradas")
    elif has_local_oauth and not strict_live:
        _ok("Google Drive credenciales", "archivos locales presentes")
    elif has_local_oauth and strict_live:
        _fail("Google Drive credenciales", "Render necesita variables o Secret Files; no subas secrets/")
    else:
        _fail("Google Drive credenciales", "falta Service Account u OAuth token")


def check_assets() -> None:
    image_dir = PROJECT_ROOT / "app" / "assets" / "imagenes"
    required = [
        "nombre.png",
        "mensaje_alma_fondo_1.png",
        "origen_nombre_fondo_1.png",
        "linaje_apellidos_fondo_1.png",
        "esencia_profunda_fondo_1.png",
        "energia_esencial_fondo_1.png",
        "zodiaco_occidental_fondo_1.png",
        "zodiaco_chino_fondo_1.png",
        "numerologia_alma_fondo_1.png",
        "animal_totem_fondo_1.png",
        "angel_guarda_fondo_1.png",
        "piedra_energetica_fondo_1.png",
        "dones_talentos_fondo_1.png",
        "sombras_fondo_1.png",
        "herida_sanacion_fondo_1.png",
        "proposito_alma_fondo_1.png",
        "amor_vinculos_fondo_1.png",
        "dinero_trabajo_expansion_fondo_1.png",
        "ritual_personalizado_fondo_1.png",
        "afirmaciones_poder_fondo_1.png",
        "mensaje_final_fondo_1.png",
        "esencia_del_alma_fondo_1.png",
        "logo.png",
    ]
    missing = [name for name in required if not (image_dir / name).exists()]
    if missing:
        _fail("assets PDF", ", ".join(missing))
    else:
        _ok("assets PDF", "completos")

    logo = image_dir / "logo.png"
    if logo.exists():
        size_mb = logo.stat().st_size / 1024 / 1024
        if size_mb > 95:
            _fail("logo.png", f"{size_mb:.1f} MB: GitHub puede rechazarlo")
        else:
            _ok("logo.png", f"{size_mb:.2f} MB")


def check_repo_hygiene() -> None:
    gitignore = PROJECT_ROOT / ".gitignore"
    text = gitignore.read_text(encoding="utf-8", errors="ignore") if gitignore.exists() else ""
    for pattern in ("instance/", "*.sqlite", ".env", "secrets/"):
        if pattern in text:
            _ok(f".gitignore {pattern}", "protegido")
        else:
            _fail(".gitignore", f"falta {pattern}")

    try:
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
    except Exception as exc:  # noqa: BLE001
        _warn("Git hygiene", f"no se pudo revisar git ls-files: {exc}")
        return

    tracked = set(completed.stdout.splitlines())
    risky = sorted(
        path
        for path in tracked
        if path == ".env"
        or path.startswith("secrets/")
        or path.startswith("instance/")
        or path.endswith((".sqlite", ".sqlite3"))
    )
    if risky:
        _fail("Archivos privados versionados", ", ".join(risky[:8]))
    else:
        _ok("Archivos privados versionados", "ninguno")


def check_app_routes() -> None:
    from app import create_app

    app = create_app()
    client = app.test_client()
    for path in ["/health", "/", "/pedido", "/resenas", "/privacidad", "/condiciones"]:
        response = client.get(path)
        if response.status_code != 200:
            _fail(f"ruta {path}", f"HTTP {response.status_code}")
        else:
            _ok(f"ruta {path}", "200")


def check_external_services() -> None:
    os.environ["GOOGLE_DRIVE_DISABLE_INTERACTIVE_OAUTH"] = "1"
    try:
        from fpdf import FPDF
        from app.google_drive_oauth import (
            eliminar_archivo_drive_oauth,
            probar_conexion_drive_oauth,
            subir_pdf_a_drive_oauth,
        )

        result = probar_conexion_drive_oauth()
        _ok("Google Drive conexión", result)

        out_dir = PROJECT_ROOT / "output" / "production_check"
        out_dir.mkdir(parents=True, exist_ok=True)
        test_pdf = out_dir / "drive_upload_check.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, "Mapa del Alma - prueba de subida Drive", new_x="LMARGIN", new_y="NEXT")
        pdf.output(str(test_pdf))

        uploaded = subir_pdf_a_drive_oauth(
            test_pdf,
            "TEST_BORRAR_mapa_alma_delivery_check.pdf",
        )
        file_id = uploaded.get("file_id")
        if not file_id:
            _fail("Google Drive subida", "no devolvió file_id")
            return
        if not (uploaded.get("download_link") or uploaded.get("view_link")):
            _fail("Google Drive link", "no devolvió enlace público")
            return
        _ok("Google Drive subida", "archivo de prueba subido")

        deleted = eliminar_archivo_drive_oauth(str(file_id))
        if deleted.get("ok"):
            _ok("Google Drive borrado", "archivo de prueba eliminado")
        else:
            _warn("Google Drive borrado", str(deleted.get("error") or "no confirmado"))
    except Exception as exc:  # noqa: BLE001
        _fail("Google Drive conexión", str(exc)[:400])


def main() -> int:
    parser = argparse.ArgumentParser(description="Chequeo de producción para Mapa del Alma.")
    parser.add_argument("--strict-live", action="store_true", help="Exige configuración real para vender.")
    parser.add_argument("--external", action="store_true", help="Prueba servicios externos como Google Drive.")
    args = parser.parse_args()

    print("=== PRODUCTION CHECK - MAPA DEL ALMA ===")
    check_core_env(strict_live=args.strict_live)
    check_stripe(strict_live=args.strict_live)
    check_openai(strict_live=args.strict_live)
    check_email()
    check_drive(strict_live=args.strict_live)
    check_assets()
    check_repo_hygiene()
    check_app_routes()
    if args.external:
        check_external_services()

    print("")
    if WARNINGS:
        print(f"WARNINGS: {len(WARNINGS)}")
    if FAILURES:
        print(f"FAILURES: {len(FAILURES)}")
        return 1
    print("PRODUCTION CHECK OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
