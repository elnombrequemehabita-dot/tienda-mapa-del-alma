def generar_pdf(nombre, apellidos, fecha_nacimiento, **kwargs):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    import os

    output_path = f"output/mapa_{nombre}_{apellidos}.pdf"

    c = canvas.Canvas(output_path, pagesize=letter)

    c.drawString(100, 750, f"Mapa del Alma de {nombre} {apellidos}")
    c.drawString(100, 720, f"Fecha de nacimiento: {fecha_nacimiento}")

    c.save()

    return output_path