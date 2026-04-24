from app.pdf_generator import generar_pdf as generar_pdf_real
import os

def generar_pdf(nombre, apellidos, fecha_nacimiento, **kwargs):

    # 1. Generar PDF con tu generador premium
    output_path = generar_pdf_real(
        nombre=nombre,
        apellidos=apellidos,
        fecha_nacimiento=fecha_nacimiento,
        **kwargs
    )

    print(f"✅ PDF GENERADO EN: {output_path}")

    # 🔥 2. SI devuelve string (ruta), convertir a bytes
    if isinstance(output_path, str) and os.path.exists(output_path):
        with open(output_path, "rb") as f:
            return f.read()

    # 🔥 3. SI ya devuelve bytes, devolver directo
    if isinstance(output_path, bytes):
        return output_path

    # ❌ 4. Si no es válido
    raise Exception("El generador no devolvió ni ruta válida ni bytes")