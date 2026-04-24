def generar_pdf(nombre, apellidos, fecha_nacimiento, **kwargs):
    from app.generador_pdf import generar_pdf as generar_pdf_real

    # Genera el PDF (esto te devuelve la ruta)
    ruta_pdf = generar_pdf_real(nombre, apellidos, fecha_nacimiento)

    # Convertir a bytes (ESTO ES LO QUE FALTABA)
    with open(ruta_pdf, "rb") as f:
        pdf_bytes = f.read()

    return pdf_bytes