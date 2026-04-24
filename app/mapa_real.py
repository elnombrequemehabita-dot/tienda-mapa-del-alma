import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generar_pdf(nombre, apellidos, fecha_nacimiento, **kwargs):
    try:
        print("🔥 GENERADOR REAL EJECUTÁNDOSE")

        # 🔥 crear carpeta output si no existe
        os.makedirs("output", exist_ok=True)

        # 🔥 limpiar valores por seguridad
        nombre = nombre or "SinNombre"
        apellidos = apellidos or "SinApellido"
        fecha_nacimiento = fecha_nacimiento or "SinFecha"

        # 🔥 nombre del archivo
        output_path = f"output/mapa_{nombre}_{apellidos}.pdf"

        print(f"📄 Generando PDF en: {output_path}")

        # 🔥 crear PDF
        c = canvas.Canvas(output_path, pagesize=letter)

        c.setFont("Helvetica", 14)
        c.drawString(100, 750, "MAPA DEL ALMA")

        c.setFont("Helvetica", 12)
        c.drawString(100, 720, f"Nombre: {nombre} {apellidos}")
        c.drawString(100, 700, f"Fecha de nacimiento: {fecha_nacimiento}")

        c.drawString(100, 650, "Este es tu PDF REAL generado correctamente.")

        c.save()

        print("✅ PDF REAL GENERADO")

        return output_path

    except Exception as e:
        print("❌ ERROR GENERANDO PDF REAL:", str(e))
        raise