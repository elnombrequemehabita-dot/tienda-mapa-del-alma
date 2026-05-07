import os
from PIL import Image, ImageDraw, ImageFont

# DATOS
datos = {
    "nombre": "Génesis",
    "apellidos": "García",
    "signo": "Leo",
    "elemento": "Fuego",
    "totem": "Pantera",
    "zodiaco_chino": "Cerdo",
    "gema": "Rubí"
}

print("DATOS:", datos)

# TOMAR LA ÚLTIMA IMAGEN GENERADA
carpeta = "output/imagenes_ai"
archivos = [a for a in os.listdir(carpeta) if a.lower().endswith((".png", ".jpg", ".jpeg"))]
archivos.sort(reverse=True)

ruta_imagen = os.path.join(carpeta, archivos[0])
print("Usando imagen:", ruta_imagen)

# ABRIR IMAGEN
imagen = Image.open(ruta_imagen).convert("RGB")
draw = ImageDraw.Draw(imagen)

ancho, alto = imagen.size

# FUENTES
try:
    fuente_titulo = ImageFont.truetype("arial.ttf", 115)
    fuente_texto = ImageFont.truetype("arial.ttf", 46)
except:
    fuente_titulo = ImageFont.load_default()
    fuente_texto = ImageFont.load_default()

# TEXTOS
titulo = datos["nombre"]
texto = "No eres casualidad…\neres el comienzo de algo que debía existir."

# COLORES
dorado = (230, 200, 140)
sombra = (10, 8, 5)

# POSICIONES CENTRADAS
x_centro = ancho // 2
y_titulo = 300
y_texto = 470

# SOMBRA + TÍTULO
draw.text((x_centro + 3, y_titulo + 3), titulo, fill=sombra, font=fuente_titulo, anchor="mm")
draw.text((x_centro, y_titulo), titulo, fill=dorado, font=fuente_titulo, anchor="mm")

# SOMBRA + TEXTO
for i, linea in enumerate(texto.split("\n")):
    y = y_texto + (i * 60)
    draw.text((x_centro + 2, y + 2), linea, fill=sombra, font=fuente_texto, anchor="mm")
    draw.text((x_centro, y), linea, fill=dorado, font=fuente_texto, anchor="mm")

# GUARDAR
imagen.save("pagina_final.jpg", quality=85, optimize=True)

print("Página creada correctamente 🔥")