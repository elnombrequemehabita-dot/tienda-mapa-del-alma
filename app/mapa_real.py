from app.pdf_generator import generar_pdf as generar_pdf_real

def generar_pdf(nombre, apellidos, fecha_nacimiento, **kwargs):

    # Llamar a tu generador REAL
    output_path = generar_pdf_real(
        nombre=nombre,
        apellidos=apellidos,
        fecha_nacimiento=fecha_nacimiento,
        **kwargs
    )

    print(f"✅ PDF REAL GENERADO EN: {output_path}")

    # Convertir a bytes (lo que Render necesita)
    with open(output_path, "rb") as f:
        pdf_bytes = f.read()

    return pdf_bytes