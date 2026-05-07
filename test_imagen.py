from app.openai_images import generar_imagen_pagina

prompt = """
Poster vertical místico premium sobre el nombre Génesis.
Fondo oscuro, detalles dorados, luz celestial, energía de creación y renacimiento.
Dejar espacio limpio en el centro para poner texto después.
No escribir texto dentro de la imagen.
Alta calidad, elegante, espiritual.
"""

ruta = generar_imagen_pagina(prompt, "genesis_test")

print("Imagen creada:", ruta)