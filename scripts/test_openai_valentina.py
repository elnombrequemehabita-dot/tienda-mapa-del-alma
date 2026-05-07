from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import openai_generator, pdf_generator


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    datos_openai = {
        "nombre": "Valentina",
        "apellidos": "García",
        "fecha": "1995-08-22",
        "signo": "leo",
        "elemento": "fuego",
        "planeta": "sol",
        "animal_chino": "cerdo",
        "numero_vida": "7",
        "numero_expresion": "3",
        "alma": "2",
        "personalidad": "6",
        "totem": "aguila",
        "gema": "amatista",
    }
    contenido = openai_generator.generar_contenido_mapa(datos_openai)

    datos_pedido = {
        "pedido_id": 999001,
        "nombre": "Valentina",
        "apellidos": "García",
        "fecha_nacimiento": "1995-08-22",
        "email": "valentina@example.com",
        "sexo": "femenino",
        "contenido_openai": contenido,
    }
    ruta_pdf = pdf_generator.generar_pdf_desde_tienda(datos_pedido)
    print(ruta_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

