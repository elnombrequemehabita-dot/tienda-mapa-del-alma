"""
Borra todos los pedidos y notificaciones; conserva las reseñas (quedan sin pedido).

Uso (desde la raíz del proyecto):
    python scripts/purge_pedidos.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from app import create_app
from app import db as database


def main() -> None:
    app = create_app()
    with app.app_context():
        stats = database.delete_all_pedidos_keep_resenas()
        print("Listo:", stats)


if __name__ == "__main__":
    main()
