# scripts/limpiar_drive_expirados.py

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app import db as database
from app.drive_cleanup import limpiar_drive_expirados


def main() -> int:
    app = create_app()
    with app.app_context():
        try:
            database.init_db()
        except Exception:
            raise

        resultado = limpiar_drive_expirados()
        print(resultado)
        return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
