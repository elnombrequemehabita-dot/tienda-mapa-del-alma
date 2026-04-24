from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def generar_pdf(nombre, apellidos, fecha_nacimiento, **kwargs):
    
    # Asegurar carpeta output
    os.makedirs("output", exist_ok=True)

    # Ruta del archivo
    output_path = f"output/mapa_{nombre}_{apellidos}.pdf"

    # Crear PDF
    c = canvas.Canvas(output_path, pagesize=letter)

    # Contenido (puedes mejorar esto luego)
    c.drawString(100, 750, f"Mapa del Alma de {nombre} {apellidos}")
    c.drawString(100, 720, f"Fecha de nacimiento: {fecha_nacimiento}")

    # Guardar PDF
    c.save()

    print(f"✅ PDF REAL GENERADO EN: {output_path}")

    # 🔥 IMPORTANTE: devolver BYTES (no ruta)
    with open(output_path, "rb") as f:
        pdf_bytes = f.read()

    return pdf_bytes