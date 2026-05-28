from __future__ import annotations

import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_DIR = PROJECT_ROOT / "secrets"
CLIENT_PATH = SECRETS_DIR / "google_drive_oauth_client.json"
TOKEN_PATH = SECRETS_DIR / "google_drive_token.json"
RENDER_ENV_PATH = SECRETS_DIR / "render_google_drive_oauth_env.txt"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def _single_line_json(path: Path) -> str:
    return json.dumps(json.loads(path.read_text(encoding="utf-8")), separators=(",", ":"))


def main() -> int:
    if not CLIENT_PATH.exists():
        print(f"[FAIL] No existe {CLIENT_PATH}")
        return 1

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    print("Abriendo navegador para autorizar Google Drive...")
    print("Inicia sesión con la cuenta dueña de la carpeta de entregas.")

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    client_json = _single_line_json(CLIENT_PATH)
    token_json = _single_line_json(TOKEN_PATH)
    RENDER_ENV_PATH.write_text(
        "\n".join(
            [
                "Copia estas variables en Render:",
                "",
                f"GOOGLE_DRIVE_OAUTH_CLIENT_JSON={client_json}",
                f"GOOGLE_DRIVE_TOKEN_JSON={token_json}",
                "",
                "No subas este archivo a GitHub.",
            ]
        ),
        encoding="utf-8",
    )

    print(f"[OK] Token renovado: {TOKEN_PATH}")
    print(f"[OK] Variables para Render: {RENDER_ENV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
