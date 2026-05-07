from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.45"))
MAX_REINTENTOS_BLOQUE = int(os.getenv("MAX_REINTENTOS_BLOQUE", "3"))
ESPERA_REINTENTO_SEGUNDOS = float(os.getenv("ESPERA_REINTENTO_SEGUNDOS", "0.8"))
OPENAI_TIMEOUT_SEGUNDOS = float(os.getenv("OPENAI_TIMEOUT_SEGUNDOS", "120"))
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "6500"))

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en .env o en variables de entorno.")

client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SEGUNDOS)

SECCIONES_OBLIGATORIAS = [
    "mensaje_alma",
    "origen_nombre",
    "linaje_apellidos",
    "esencia",
    "energia",
    "zodiaco",
    "zodiaco_chino",
    "numerologia",
    "animal_espiritual",
    "angel_guardian",
    "piedra_energetica",
    "dones",
    "sombras",
    "herida",
    "proposito",
    "amor_vinculos",
    "dinero_camino",
    "ritual_personalizado",
    "afirmaciones",
    "mensaje_final",
    "esencia_alma",
]

CAMPOS_OBLIGATORIOS = [
    "primera_lectura",
    "profundizacion",
    "integracion",
]

# IMPORTANTE:
# Antes se generaban bloques de 5 secciones. Eso hacia llamadas enormes,
# respuestas lentas y JSON incompleto. Ahora se genera 1 seccion por llamada:
# mas estable, mas controlable y con texto abundante por pagina.
BLOQUES = [[sec] for sec in SECCIONES_OBLIGATORIAS]

# Objetivo visual: cada pagina debe sentirse llena y premium.
# Aproximado por seccion completa: 600 a 775 palabras.
RANGOS_IDEALES = {
    "primera_lectura": (225, 285),
    "profundizacion": (235, 305),
    "integracion": (140, 185),
}

# Minimos duros: por debajo de esto la pagina puede verse vacia.
RANGOS_DUROS = {
    # Mantiene paginas llenas, pero evita fallar por diferencias pequenas
    # como 194 vs 205 palabras cuando el texto sigue siendo usable/premium.
    "primera_lectura": (180, 345),
    "profundizacion": (180, 365),
    "integracion": (95, 240),
}

FRASES_PROHIBIDAS = [
    "esta seccion se revela",
    "esta sección se revela",
    "lectura simbolica personalizada creada",
    "lectura simbólica personalizada creada",
    "creada para abrir una conversacion profunda",
    "creada para abrir una conversación profunda",
    "el modo en que tu nombre habita tu camino",
    "la clave esta en volver al centro",
    "la clave está en volver al centro",
    "una decision pequena puede ordenar",
    "una decisión pequeña puede ordenar",
    "lo importante es practicar la verdad",
    "tu energia es unica",
    "tu energía es única",
    "eres una persona especial",
    "brillas con luz propia",
    "el universo tiene un mensaje",
    "conecta con tu esencia",
    "aqui descubriremos",
    "aquí descubriremos",
    "en esta pagina veremos",
    "en esta página veremos",
    "esta profundizacion no repite",
    "esta profundización no repite",
]

SECCION_INFO: Dict[str, Dict[str, str]] = {
    "mensaje_alma": {
        "titulo": "Mensaje de tu alma",
        "mision": "abrir el libro con una lectura emocional fuerte sobre la identidad interior, la verdad que la persona ha callado y la forma en que su alma pide ser escuchada",
        "evitar": "no repetir esencia, no hablar de signos todavía, no cerrar con consejos simples",
    },
    "origen_nombre": {
        "titulo": "Origen simbolico del nombre",
        "mision": "interpretar el nombre desde sonido, ritmo, presencia, letras, vibracion emocional y marca simbolica, sin inventar etimologias falsas",
        "evitar": "no decir que el origen historico es real si no se sabe, no sonar como diccionario",
    },
    "linaje_apellidos": {
        "titulo": "Linaje de tus apellidos",
        "mision": "hablar de memoria familiar, herencia emocional, fuerza ancestral, patrones recibidos, lealtades invisibles y posibilidad de sanar sin negar la raiz",
        "evitar": "no inventar historia genealogica concreta, no decir paises o escudos falsos",
    },
    "esencia": {
        "titulo": "Esencia profunda",
        "mision": "describir la forma interna de ser, amar, decidir, sostenerse, protegerse y mostrarse ante la vida",
        "evitar": "no repetir mensaje_alma, no quedarse en elogios",
    },
    "energia": {
        "titulo": "Energia esencial",
        "mision": "mostrar temperamento, magnetismo, impacto en ambientes, ritmo personal, fuerza vital y sensibilidad energetica",
        "evitar": "no usar frases vacias como energia unica",
    },
    "zodiaco": {
        "titulo": "Zodiaco occidental",
        "mision": "integrar signo, elemento y planeta regente como lectura emocional y practica, no como horoscopo barato",
        "evitar": "no predecir futuro, no frases de horoscopo diario",
    },
    "zodiaco_chino": {
        "titulo": "Zodiaco chino",
        "mision": "explicar el animal chino como instinto ancestral, estrategia, modo de resistir, protegerse y actuar ante ciclos de vida",
        "evitar": "no sonar enciclopedico",
    },
    "numerologia": {
        "titulo": "Numerologia del alma",
        "mision": "integrar numero de vida y numero de expresion como patron de aprendizaje, destino, reto, potencial y direccion",
        "evitar": "no hacer calculos dentro del texto, no repetir formulas",
    },
    "animal_espiritual": {
        "titulo": "Animal totem",
        "mision": "convertir el animal totem en espejo de instinto, defensa, intuicion fisica, proteccion y manera de recuperar poder",
        "evitar": "no describir solo al animal, conectarlo con la persona",
    },
    "angel_guardian": {
        "titulo": "Angel de la guarda",
        "mision": "presentar el angel como simbolo de guia, calma, proteccion, discernimiento y fuerza invisible sin prometer milagros",
        "evitar": "no fanatismo religioso, no promesas sobrenaturales",
    },
    "piedra_energetica": {
        "titulo": "Piedra energetica",
        "mision": "explicar la piedra como ancla simbolica, apoyo emocional, enfoque, proteccion y practica cotidiana",
        "evitar": "no afirmar curaciones medicas",
    },
    "dones": {
        "titulo": "Dones y talentos",
        "mision": "identificar talentos naturales, capacidades utiles, valor que puede ofrecer, belleza practica y forma de convertir dones en accion",
        "evitar": "no elogios vacios",
    },
    "sombras": {
        "titulo": "Lado oscuro y sombras",
        "mision": "mostrar patrones dificiles, defensas, miedos, control, apego, autosabotaje y lecciones que piden madurez",
        "evitar": "no atacar, no culpar, no repetir herida",
    },
    "herida": {
        "titulo": "Herida emocional y sanacion",
        "mision": "nombrar una herida emocional probable de forma humana, sensible y reparadora, conectada con necesidad de reconocimiento, seguridad, amor o permiso para ser",
        "evitar": "no diagnosticar, no sonar clinico",
    },
    "proposito": {
        "titulo": "Proposito de alma",
        "mision": "dar direccion concreta, sentido de vida, servicio, decisiones, camino vocacional y forma de vivir con mas verdad",
        "evitar": "no decir que nacio para sanar al mundo de forma generica",
    },
    "amor_vinculos": {
        "titulo": "Amor y vinculos",
        "mision": "leer la forma de amar, limites, entrega, pareja, familia, amistad, miedo al abandono o exceso de carga emocional",
        "evitar": "no hacerlo cursi, no prometer pareja",
    },
    "dinero_camino": {
        "titulo": "Dinero, trabajo y expansion",
        "mision": "conectar valor personal, trabajo, prosperidad, bloqueos economicos, disciplina, merecimiento y expansion concreta",
        "evitar": "no prometer riqueza, no hacerlo motivacional barato",
    },
    "ritual_personalizado": {
        "titulo": "Ritual personalizado",
        "mision": "crear un ritual con velas como cierre emocional del libro, coherente con herida, sombras, proposito y esencia",
        "evitar": "no hacerlo largo, no magia irreal, no usar muchos materiales",
    },
    "afirmaciones": {
        "titulo": "Afirmaciones de poder",
        "mision": "crear afirmaciones profundas, no genericas, conectadas con identidad, herida, sombra, merecimiento y direccion",
        "evitar": "no frases motivacionales comunes",
    },
    "mensaje_final": {
        "titulo": "Mensaje final",
        "mision": "cerrar el libro con fuerza emocional, integracion, dignidad, permiso para avanzar y sensacion de antes y despues",
        "evitar": "no despedida corta, no resumen flojo",
    },
    "esencia_alma": {
        "titulo": "Esencia del Alma",
        "mision": "crear una pagina final especial, valiosa y profundamente personalizada que funcione como una hoja de vida emocional del alma: no debe resumir todo el libro, sino revelar la verdad central del nombre, la energia dominante, el don principal, la herida que pide cuidado, la direccion interior y una guia concreta para recordar quien es la persona",
        "evitar": "no hacer un resumen aburrido del libro, no repetir secciones anteriores, no sonar como conclusion generica, no llenar con lista tecnica",
    },
}


class ErrorContenidoMapa(RuntimeError):
    pass


def _project_root() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name == "app":
        return here.parent.parent
    return here.parent


def _json_dir() -> Path:
    folder = _project_root() / "output" / "json_openai"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _safe_filename(texto: str) -> str:
    base = quitar_acentos(limpiar_texto(texto)).lower()
    base = re.sub(r"[^a-z0-9_-]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "mapa"


def limpiar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor)
    reemplazos = {
        "\r": " ",
        "\t": " ",
        "\u00a0": " ",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "—": "-",
        "–": "-",
        "…": "...",
        "\u200b": "",
        "\ufeff": "",
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    return re.sub(r"\s+", " ", texto).strip()


def quitar_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


def contar_palabras(texto: str) -> int:
    texto = limpiar_texto(texto)
    if not texto:
        return 0
    return len(re.findall(r"\b[\wáéíóúÁÉÍÓÚñÑüÜ]+\b", texto, flags=re.UNICODE))


def contar_oraciones(texto: str) -> int:
    texto = limpiar_texto(texto)
    if not texto:
        return 0
    partes = re.split(r"[.!?;:]+", texto)
    return len([p for p in partes if len(p.strip()) > 12])


def normalizar_fecha(fecha: Optional[str]) -> Optional[datetime]:
    raw = limpiar_texto(fecha)
    if not raw:
        return None

    formatos = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]

    for formato in formatos:
        try:
            return datetime.strptime(raw, formato)
        except ValueError:
            continue

    raise ValueError("Fecha invalida. Usa formato YYYY-MM-DD, por ejemplo 1993-02-13.")


def signo_zodiacal(fecha_nacimiento: Optional[str]) -> str:
    fecha = normalizar_fecha(fecha_nacimiento)
    if not fecha:
        return "No especificado"

    dia = fecha.day
    mes = fecha.month

    if (mes == 3 and dia >= 21) or (mes == 4 and dia <= 19):
        return "Aries"
    if (mes == 4 and dia >= 20) or (mes == 5 and dia <= 20):
        return "Tauro"
    if (mes == 5 and dia >= 21) or (mes == 6 and dia <= 20):
        return "Geminis"
    if (mes == 6 and dia >= 21) or (mes == 7 and dia <= 22):
        return "Cancer"
    if (mes == 7 and dia >= 23) or (mes == 8 and dia <= 22):
        return "Leo"
    if (mes == 8 and dia >= 23) or (mes == 9 and dia <= 22):
        return "Virgo"
    if (mes == 9 and dia >= 23) or (mes == 10 and dia <= 22):
        return "Libra"
    if (mes == 10 and dia >= 23) or (mes == 11 and dia <= 21):
        return "Escorpio"
    if (mes == 11 and dia >= 22) or (mes == 12 and dia <= 21):
        return "Sagitario"
    if (mes == 12 and dia >= 22) or (mes == 1 and dia <= 19):
        return "Capricornio"
    if (mes == 1 and dia >= 20) or (mes == 2 and dia <= 18):
        return "Acuario"
    return "Piscis"


def elemento_zodiacal(signo: str) -> str:
    mapping = {
        "Aries": "Fuego",
        "Leo": "Fuego",
        "Sagitario": "Fuego",
        "Tauro": "Tierra",
        "Virgo": "Tierra",
        "Capricornio": "Tierra",
        "Geminis": "Aire",
        "Libra": "Aire",
        "Acuario": "Aire",
        "Cancer": "Agua",
        "Escorpio": "Agua",
        "Piscis": "Agua",
    }
    return mapping.get(signo, "No especificado")


def planeta_regente(signo: str) -> str:
    mapping = {
        "Aries": "Marte",
        "Tauro": "Venus",
        "Geminis": "Mercurio",
        "Cancer": "Luna",
        "Leo": "Sol",
        "Virgo": "Mercurio",
        "Libra": "Venus",
        "Escorpio": "Pluton",
        "Sagitario": "Jupiter",
        "Capricornio": "Saturno",
        "Acuario": "Urano",
        "Piscis": "Neptuno",
    }
    return mapping.get(signo, "No especificado")


def angel_guardian(signo: str) -> str:
    mapping = {
        "Aries": "Arcangel Ariel",
        "Tauro": "Arcangel Chamuel",
        "Geminis": "Arcangel Rafael",
        "Cancer": "Arcangel Gabriel",
        "Leo": "Arcangel Miguel",
        "Virgo": "Arcangel Metatron",
        "Libra": "Arcangel Jofiel",
        "Escorpio": "Arcangel Jeremiel",
        "Sagitario": "Arcangel Raguel",
        "Capricornio": "Arcangel Azrael",
        "Acuario": "Arcangel Uriel",
        "Piscis": "Arcangel Sandalfon",
    }
    return mapping.get(signo, "Arcangel Miguel")


def reducir_numero(numero: int) -> int:
    while numero > 9 and numero not in (11, 22, 33):
        numero = sum(int(d) for d in str(numero))
    return numero


def numero_vida(fecha_nacimiento: Optional[str]) -> int:
    fecha = normalizar_fecha(fecha_nacimiento)
    if not fecha:
        return 0
    digitos = f"{fecha.year:04d}{fecha.month:02d}{fecha.day:02d}"
    total = sum(int(d) for d in digitos)
    return reducir_numero(total)


def valor_pitagorico(letra: str) -> int:
    letra = quitar_acentos(letra).upper()
    tabla = {
        "A": 1,
        "J": 1,
        "S": 1,
        "B": 2,
        "K": 2,
        "T": 2,
        "C": 3,
        "L": 3,
        "U": 3,
        "D": 4,
        "M": 4,
        "V": 4,
        "E": 5,
        "N": 5,
        "W": 5,
        "F": 6,
        "O": 6,
        "X": 6,
        "G": 7,
        "P": 7,
        "Y": 7,
        "H": 8,
        "Q": 8,
        "Z": 8,
        "I": 9,
        "R": 9,
    }
    return tabla.get(letra, 0)


def numero_expresion(nombre_completo: str) -> int:
    total = 0
    for letra in quitar_acentos(nombre_completo):
        if letra.isalpha():
            total += valor_pitagorico(letra)
    return reducir_numero(total)


def zodiaco_chino(fecha_nacimiento: Optional[str]) -> str:
    fecha = normalizar_fecha(fecha_nacimiento)
    if not fecha:
        return "No especificado"

    animales = [
        "Rata",
        "Buey",
        "Tigre",
        "Conejo",
        "Dragon",
        "Serpiente",
        "Caballo",
        "Cabra",
        "Mono",
        "Gallo",
        "Perro",
        "Cerdo",
    ]
    return animales[(fecha.year - 4) % 12]


def animal_totem(signo: str, n_vida: int) -> str:
    especiales = {
        11: "Pantera blanca",
        22: "Elefante",
        33: "Colibri dorado",
    }

    if n_vida in especiales:
        return especiales[n_vida]

    mapping = {
        "Aries": "Lobo",
        "Tauro": "Oso",
        "Geminis": "Zorro",
        "Cancer": "Ciervo",
        "Leo": "Leon",
        "Virgo": "Buho",
        "Libra": "Cisne",
        "Escorpio": "Serpiente",
        "Sagitario": "Caballo",
        "Capricornio": "Cabra de montana",
        "Acuario": "Aguila",
        "Piscis": "Delfin",
    }
    return mapping.get(signo, "Lobo")


def piedra_energetica(signo: str, n_expresion: int) -> str:
    por_numero = {
        1: "Ojo de tigre",
        2: "Piedra lunar",
        3: "Citrino",
        4: "Hematita",
        5: "Turquesa",
        6: "Cuarzo rosa",
        7: "Amatista",
        8: "Pirita",
        9: "Labradorita",
        11: "Selenita",
        22: "Granate",
        33: "Cuarzo cristal",
    }

    if n_expresion in por_numero:
        return por_numero[n_expresion]

    por_signo = {
        "Aries": "Cornalina",
        "Tauro": "Cuarzo rosa",
        "Geminis": "Agata",
        "Cancer": "Piedra lunar",
        "Leo": "Citrino",
        "Virgo": "Amazonita",
        "Libra": "Lapislazuli",
        "Escorpio": "Obsidiana",
        "Sagitario": "Turquesa",
        "Capricornio": "Granate",
        "Acuario": "Amatista",
        "Piscis": "Aguamarina",
    }
    return por_signo.get(signo, "Cuarzo cristal")


def normalizar_sexo(sexo: Optional[str]) -> str:
    s = quitar_acentos(limpiar_texto(sexo or "")).lower()

    if s in ("mujer", "femenino", "f", "female", "ella"):
        return "femenino"
    if s in ("hombre", "masculino", "m", "male", "el"):
        return "masculino"
    return "neutral"


def crear_calculos(
    nombre: str,
    nombre_completo: Optional[str],
    fecha_nacimiento: Optional[str],
    sexo: str,
) -> Dict[str, Any]:
    nombre_limpio = limpiar_texto(nombre)
    nombre_completo_limpio = limpiar_texto(nombre_completo or nombre_limpio)
    sexo_norm = normalizar_sexo(sexo)

    signo = signo_zodiacal(fecha_nacimiento)
    elemento = elemento_zodiacal(signo)
    planeta = planeta_regente(signo)
    n_vida = numero_vida(fecha_nacimiento)
    n_expresion = numero_expresion(nombre_completo_limpio)
    chino = zodiaco_chino(fecha_nacimiento)
    animal = animal_totem(signo, n_vida)
    piedra = piedra_energetica(signo, n_expresion)
    angel = angel_guardian(signo)

    return {
        "nombre": nombre_limpio,
        "nombre_completo": nombre_completo_limpio,
        "fecha_nacimiento": limpiar_texto(fecha_nacimiento or ""),
        "sexo": sexo_norm,
        "signo": signo,
        "elemento": elemento,
        "planeta_regente": planeta,
        "angel_guardian": angel,
        "numero_vida": n_vida,
        "numero_expresion": n_expresion,
        "zodiaco_chino": chino,
        "animal_totem": animal,
        "piedra_energetica": piedra,
    }


def _ruta_json_pedido(pedido_id: Any) -> Optional[Path]:
    if pedido_id is None or limpiar_texto(pedido_id) == "":
        return None
    try:
        pedido_int = int(pedido_id)
    except (TypeError, ValueError):
        return _json_dir() / f"openai_pedido_{_safe_filename(str(pedido_id))}.json"
    return _json_dir() / f"openai_pedido_{pedido_int}.json"


def _guardar_json(path: Path, data: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_path.replace(path)
    return str(path)


def _guardar_json_nombre(prefix: str, calculos: Dict[str, Any], data: Dict[str, Any]) -> str:
    nombre = _safe_filename(str(calculos.get("nombre") or "mapa"))
    stamp = int(time.time())
    path = _json_dir() / f"{prefix}_{nombre}_{stamp}.json"
    return _guardar_json(path, data)


def _cargar_json_si_existe(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not path or not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if _json_final_valido(data):
            return data
    except Exception:
        return None
    return None


def _json_final_valido(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    secciones = data.get("secciones") or data.get("secciones_editoriales")
    if not isinstance(secciones, dict):
        return False
    for sec in SECCIONES_OBLIGATORIAS:
        node = secciones.get(sec)
        if not isinstance(node, dict):
            return False
        for campo in CAMPOS_OBLIGATORIOS:
            if not limpiar_texto(node.get(campo)):
                return False
    return True


def _schema_json(secciones: List[str]) -> str:
    data = {"secciones": {}}
    for sec in secciones:
        data["secciones"][sec] = {
            "primera_lectura": f"texto de {RANGOS_IDEALES['primera_lectura'][0]} a {RANGOS_IDEALES['primera_lectura'][1]} palabras",
            "profundizacion": f"texto de {RANGOS_IDEALES['profundizacion'][0]} a {RANGOS_IDEALES['profundizacion'][1]} palabras",
            "integracion": f"texto de {RANGOS_IDEALES['integracion'][0]} a {RANGOS_IDEALES['integracion'][1]} palabras",
        }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _resumen_contexto_previo(secciones_generadas: Dict[str, Dict[str, str]]) -> str:
    if not secciones_generadas:
        return "Aun no hay secciones previas. Este es el inicio del libro."

    claves = [
        "mensaje_alma",
        "origen_nombre",
        "linaje_apellidos",
        "esencia",
        "energia",
        "sombras",
        "herida",
        "proposito",
    ]

    partes: List[str] = []
    for key in claves:
        node = secciones_generadas.get(key)
        if not isinstance(node, dict):
            continue
        texto = " ".join(limpiar_texto(node.get(campo, "")) for campo in CAMPOS_OBLIGATORIOS)
        if texto:
            partes.append(f"{key}: {texto[:900]}")

    return "\n\n".join(partes) if partes else "Hay secciones previas, pero no se encontro resumen util."


def _detalles_secciones(secciones: List[str]) -> str:
    lines = []
    for sec in secciones:
        info = SECCION_INFO[sec]
        lines.append(
            f"- {sec}: titulo='{info['titulo']}'. Mision editorial: {info['mision']}. Evitar: {info['evitar']}."
        )
    return "\n".join(lines)


def _prompt_bloque(
    secciones: List[str],
    calculos: Dict[str, Any],
    secciones_generadas: Dict[str, Dict[str, str]],
    errores_previos: Optional[Dict[str, Any]] = None,
) -> str:
    datos = json.dumps(calculos, ensure_ascii=False, indent=2)
    estructura = _schema_json(secciones)
    contexto = _resumen_contexto_previo(secciones_generadas)
    detalles = _detalles_secciones(secciones)

    sexo = calculos.get("sexo", "neutral")
    if sexo == "femenino":
        regla_genero = (
            "La persona debe ser tratada en femenino cuando corresponda: ella, la, guiada, protegida, preparada, decidida. "
            "Evita masculinos visibles como guiado, protegido, preparado, decidido."
        )
    elif sexo == "masculino":
        regla_genero = (
            "La persona debe ser tratada en masculino cuando corresponda: el, lo, guiado, protegido, preparado, decidido. "
            "Evita femeninos visibles como guiada, protegida, preparada, decidida."
        )
    else:
        regla_genero = (
            "Usa lenguaje neutral: la persona, su camino, su esencia. Evita adjetivos con genero cuando sea posible."
        )

    bloque_final = ""
    if any(sec in secciones for sec in ["amor_vinculos", "dinero_camino", "ritual_personalizado", "afirmaciones", "mensaje_final"]):
        bloque_final = """
REGLA ESPECIAL PARA EL BLOQUE FINAL:
Este bloque NO puede bajar calidad. Debe sentirse igual o mas poderoso que el primer bloque.
Amor, dinero, ritual, afirmaciones y mensaje final son el cierre emocional del producto.
No resuelvas estas secciones rapido. No las hagas mas cortas, mas genericas ni menos profundas.
El ritual y el mensaje final deben sentirse como un antes y despues.
"""

    ritual_extra = ""
    if "ritual_personalizado" in secciones:
        ritual_extra = f"""
INSTRUCCIONES OBLIGATORIAS PARA ritual_personalizado:
Eres un experto en creacion de contenido espiritual personalizado de alto nivel para un producto premium llamado "El Nombre Que Me Habita".

Tu tarea es generar UN SOLO ritual personalizado que sera la parte final del libro, como integracion y cierre emocional del Mapa del Alma.

IMPORTANTE:
Este ritual debe estar completamente alineado con el perfil del alma de la persona y con todo lo revelado previamente en el libro.
NO puede contradecir la herida, la esencia ni el proposito.

DATOS DE ENTRADA:
* Nombre: {calculos.get("nombre")}
* Sexo: {calculos.get("sexo")}
* Signo zodiacal: {calculos.get("signo")}
* Elemento: {calculos.get("elemento")}
* Numero de vida: {calculos.get("numero_vida")}
* Herida principal: usar lo generado previamente en la seccion herida.
* Sombras: usar lo generado previamente en la seccion sombras.
* Proposito del alma: usar lo generado previamente en la seccion proposito.

REGLAS ESTRICTAS DEL RITUAL:
* El ritual es el cierre del libro, no una seccion decorativa.
* Debe sentirse profundo, intimo y emocional.
* Debe usar velas como elemento central.
* Puede incluir SOLO UNO adicional: hilo, papel, agua o sal.
* Debe ser simple y realizable en casa.
* NO debe ser largo ni complicado.
* NO debe sonar magico irreal, sino simbolico y consciente.
* Debe mencionar el nombre de la persona dentro del ritual.
* Debe sentirse como un antes y despues.

ESTRUCTURA INTERNA OBLIGATORIA DEL RITUAL:
1. Nombre del ritual, corto, poderoso y personalizado.
2. Proposito del ritual, explicando que libera o sana segun su herida y energia.
3. Materiales, lista breve, maximo 3 a 4 elementos.
4. Preparacion, indicando escribir el nombre en la vela y la intencion.
5. Pasos del ritual, numerados, claros y simples.
6. Frase de activacion personalizada, incluyendo el nombre de la persona.
7. Interpretacion emocional, explicando por que este ritual es exactamente para esta persona segun su mapa.
8. Recomendacion, indicando si se hace una vez o varios dias.

DISTRIBUCION DEL RITUAL:
- primera_lectura: nombre del ritual, proposito y materiales.
- profundizacion: preparacion y pasos.
- integracion: frase de activacion, interpretacion emocional y recomendacion.
"""

    esencia_alma_extra = ""
    if "esencia_alma" in secciones:
        esencia_alma_extra = f"""
INSTRUCCIONES OBLIGATORIAS PARA esencia_alma:
Esta es una pagina nueva y especial del libro, ubicada despues de las 20 lecturas interiores y antes de la pagina de notas.
Debe sentirse aun mas valiosa que una seccion normal, como una hoja de vida emocional del alma.
NO debe resumir todo el libro ni repetir lo ya escrito. Debe destilar la verdad central de la persona en una lectura elegante, concreta y memorable.

DATOS DE ENTRADA:
* Nombre: {calculos.get("nombre")}
* Nombre completo: {calculos.get("nombre_completo")}
* Sexo: {calculos.get("sexo")}
* Signo: {calculos.get("signo")}
* Elemento: {calculos.get("elemento")}
* Planeta regente: {calculos.get("planeta_regente")}
* Numero de vida: {calculos.get("numero_vida")}
* Numero de expresion: {calculos.get("numero_expresion")}
* Animal totem: {calculos.get("animal_totem")}
* Piedra energetica: {calculos.get("piedra_energetica")}

ENFOQUE EDITORIAL:
- primera_lectura: abrir con una declaracion poderosa sobre la identidad central del alma y la energia que el nombre sostiene.
- profundizacion: mostrar el patron emocional principal, el don que mas valor tiene, la herida que pide cuidado y la manera concreta en que esa persona recupera fuerza.
- integracion: cerrar con una guia breve y accionable: que debe recordar, que debe soltar y que debe practicar para vivir mas alineada con su nombre.

REGLAS ESPECIALES:
- Debe sentirse como la pagina mas especial del libro.
- No uses formato de lista.
- No digas "en resumen", "este libro", "como vimos" ni "a lo largo de estas paginas".
- No repitas titulos de secciones anteriores.
- No metas todos los datos de forma forzada; usa solo los que eleven la lectura.
- Debe ser emocional, premium, directa, concreta y vendible.
"""

    correccion = ""
    if errores_previos:
        correccion = f"""
CORRECCION OBLIGATORIA:
La respuesta anterior tuvo estos errores. Corrige SOLO generando el JSON correcto para las secciones solicitadas:
{json.dumps(errores_previos, ensure_ascii=False, indent=2)}
"""

    return f"""
Eres el escritor principal de un producto premium llamado "Mapa del Alma - El Nombre Que Me Habita".

No estas llenando campos.
Estas escribiendo paginas de un libro digital personalizado que una clienta pago para sentirse profundamente vista.
Cada seccion debe sentirse como una pagina valiosa, no como relleno.

DATOS DEL PERFIL:
{datos}

CONTEXTO YA GENERADO:
{contexto}

SECCIONES QUE DEBES GENERAR AHORA:
{detalles}

REGLA DE GENERO:
{regla_genero}

REGLAS DE CALIDAD CONSTANTE:
- La calidad debe ser constante desde el bloque 1 hasta el bloque 4.
- Prohibido que las ultimas secciones salgan mas pobres que las primeras.
- Prohibido resolver una seccion con una o dos oraciones.
- Prohibido escribir contenido generico, motivacional barato o de horoscopo comun.
- Prohibido repetir el mismo angulo emocional entre secciones.
- Prohibido repetir frases hechas.
- Prohibido usar frases como "esta seccion se revela", "energia unica", "brillas con luz propia", "conecta con tu esencia".
- Cada seccion debe tener una funcion editorial distinta.
- Si una seccion parece mas breve, mas generica o menos trabajada que las anteriores, el producto completo falla.
- No priorices terminar rapido. Prioriza profundidad, coherencia y calidad editorial constante.
- Integra datos del perfil solo cuando aporten sentido. No metas todos los datos de forma forzada.
- Menciona el nombre con moderacion. No lo repitas en cada parrafo.
- Mantente en tono editorial mistico premium: humano, profundo, claro, emocional, elegante y vendible.
- No hagas promesas medicas, financieras, religiosas ni milagrosas.
- No digas que eres IA.
- No expliques el proceso.
- Devuelve SOLO JSON valido.
- OBLIGATORIO: incluye TODAS las secciones solicitadas en esta llamada. No omitas ninguna clave.
- OBLIGATORIO: cada seccion debe incluir los 3 campos completos.
- OBLIGATORIO: nunca devuelvas una seccion vacia ni resumida.
- OBLIGATORIO: escribe contenido suficiente para llenar una pagina completa de PDF.
- OBLIGATORIO: cada seccion completa debe sentirse como una pagina editorial terminada, no como una respuesta corta.

EXTENSION IDEAL:
- primera_lectura: {RANGOS_IDEALES["primera_lectura"][0]} a {RANGOS_IDEALES["primera_lectura"][1]} palabras.
- profundizacion: {RANGOS_IDEALES["profundizacion"][0]} a {RANGOS_IDEALES["profundizacion"][1]} palabras.
- integracion: {RANGOS_IDEALES["integracion"][0]} a {RANGOS_IDEALES["integracion"][1]} palabras.

ESTRUCTURA:
Cada seccion debe tener exactamente:
- primera_lectura
- profundizacion
- integracion

{bloque_final}

{ritual_extra}

{esencia_alma_extra}

{correccion}

JSON EXACTO ESPERADO:
{estructura}
""".strip()


def _extraer_json(texto: str) -> Dict[str, Any]:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?", "", texto, flags=re.IGNORECASE).strip()
        texto = re.sub(r"```$", "", texto).strip()

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        inicio = texto.find("{")
        fin = texto.rfind("}")
        if inicio >= 0 and fin > inicio:
            return json.loads(texto[inicio : fin + 1])
        raise


def llamar_openai(prompt: str) -> Dict[str, Any]:
    try:
        respuesta = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Responde solamente JSON valido. No uses markdown. "
                        "No agregues explicaciones fuera del JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=OPENAI_TEMPERATURE,
            timeout=OPENAI_TIMEOUT_SEGUNDOS,
            max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
            response_format={"type": "json_object"},
        )
    except TypeError:
        respuesta = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Responde solamente JSON valido. No uses markdown. "
                        "No agregues explicaciones fuera del JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=OPENAI_TEMPERATURE,
            timeout=OPENAI_TIMEOUT_SEGUNDOS,
            max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
            text={"format": {"type": "json_object"}},
        )

    texto = getattr(respuesta, "output_text", None)
    if not texto:
        texto = str(respuesta)

    return _extraer_json(texto)


def _repeticion_excesiva(texto: str) -> bool:
    limpio = limpiar_texto(texto).lower()
    palabras = re.findall(r"\b[\wáéíóúñü]+\b", limpio, flags=re.UNICODE)
    if len(palabras) < 45:
        return False

    segmentos = [" ".join(palabras[i : i + 6]) for i in range(max(0, len(palabras) - 5))]
    vistos: Dict[str, int] = {}
    for seg in segmentos:
        vistos[seg] = vistos.get(seg, 0) + 1
        if vistos[seg] >= 3:
            return True
    return False


def _validar_genero(texto: str, sexo: str) -> List[str]:
    """
    Validacion de genero con menos falsos positivos.
    Antes rechazaba palabras como "decidido" aunque fueran verbos correctos
    (ej: "ha decidido"). Aqui solo marcamos frases claramente dirigidas
    a la persona con genero incorrecto.
    """
    errores: List[str] = []
    lower = f" {limpiar_texto(texto).lower()} "

    if sexo == "femenino":
        patrones = [
            r"\btu estas\s+(guiado|protegido|preparado|listo|lindo|hermoso)\b",
            r"\btu eres\s+(guiado|protegido|preparado|listo|lindo|hermoso)\b",
            r"\bestas\s+(guiado|protegido|preparado|listo|lindo|hermoso)\b",
            r"\beres\s+(guiado|protegido|preparado|listo|lindo|hermoso)\b",
            r"\bte sientes\s+(guiado|protegido|preparado|listo)\b",
        ]
        if any(re.search(p, quitar_acentos(lower)) for p in patrones):
            errores.append("posible masculino incorrecto para una lectura femenina")
    elif sexo == "masculino":
        patrones = [
            r"\btu estas\s+(guiada|protegida|preparada|lista|linda|hermosa)\b",
            r"\btu eres\s+(guiada|protegida|preparada|lista|linda|hermosa)\b",
            r"\bestas\s+(guiada|protegida|preparada|lista|linda|hermosa)\b",
            r"\beres\s+(guiada|protegida|preparada|lista|linda|hermosa)\b",
            r"\bte sientes\s+(guiada|protegida|preparada|lista)\b",
        ]
        if any(re.search(p, quitar_acentos(lower)) for p in patrones):
            errores.append("posible femenino incorrecto para una lectura masculina")

    return errores

def validar_campo(seccion: str, campo: str, valor: Any, sexo: str) -> List[str]:
    errores: List[str] = []

    if not isinstance(valor, str):
        return [f"{seccion}.{campo} no es texto"]

    texto = limpiar_texto(valor)
    if not texto:
        return [f"{seccion}.{campo} esta vacio"]

    palabras = contar_palabras(texto)
    minimo, maximo = RANGOS_DUROS[campo]

    # Ajuste especial SOLO para ritual_personalizado.
    # El ritual debe ser claro, realizable en casa y no demasiado largo; por eso
    # no conviene exigirle exactamente los mismos minimos que a una lectura editorial.
    # Esto evita rechazar rituales buenos por quedar apenas cortos y reduce gasto
    # por reintentos innecesarios de OpenAI.
    if seccion == "ritual_personalizado":
        limites_ritual = {
            "primera_lectura": (145, 345),
            "profundizacion": (145, 365),
            "integracion": (80, 240),
        }
        minimo, maximo = limites_ritual.get(campo, (minimo, maximo))

    if palabras < minimo:
        errores.append(f"{seccion}.{campo} tiene {palabras} palabras; minimo duro {minimo}")
    if palabras > maximo:
        errores.append(f"{seccion}.{campo} tiene {palabras} palabras; maximo duro {maximo}")

    if contar_oraciones(texto) < 3 and campo != "integracion":
        errores.append(f"{seccion}.{campo} tiene muy pocas oraciones para una lectura premium")

    if contar_oraciones(texto) < 2 and campo == "integracion":
        errores.append(f"{seccion}.{campo} tiene muy pocas oraciones para integrar bien")

    lower = texto.lower()
    for frase in FRASES_PROHIBIDAS:
        if frase in lower:
            errores.append(f"{seccion}.{campo} contiene frase prohibida: {frase}")

    if _repeticion_excesiva(texto):
        errores.append(f"{seccion}.{campo} tiene repeticion excesiva")

    errores.extend(_validar_genero(texto, sexo))

    return errores


def validar_seccion(seccion: str, node: Any, sexo: str) -> List[str]:
    if not isinstance(node, dict):
        return [f"{seccion} no es objeto"]

    errores: List[str] = []
    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in node:
            errores.append(f"Falta {seccion}.{campo}")
            continue
        errores.extend(validar_campo(seccion, campo, node.get(campo), sexo))

    if seccion == "ritual_personalizado":
        texto_total = " ".join(limpiar_texto(node.get(c, "")) for c in CAMPOS_OBLIGATORIOS).lower()
        if "vela" not in texto_total and "velas" not in texto_total:
            errores.append("ritual_personalizado no menciona velas")
        if "nombre" not in texto_total and "intencion" not in texto_total and "intención" not in texto_total:
            errores.append("ritual_personalizado no incluye preparacion con nombre/intencion")

    return errores


def validar_bloque(data: Any, secciones: List[str], sexo: str) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, str]]]:
    errores: Dict[str, List[str]] = {}
    validas: Dict[str, Dict[str, str]] = {}

    if not isinstance(data, dict):
        return {"estructura": ["La respuesta no es un diccionario"]}, validas

    root = data.get("secciones")
    if not isinstance(root, dict):
        return {"estructura": ["Falta objeto raiz 'secciones'"]}, validas

    for sec in secciones:
        if sec not in root:
            errores[sec] = [f"Falta seccion obligatoria {sec}"]
            continue

        err = validar_seccion(sec, root.get(sec), sexo)
        if err:
            errores[sec] = err
        else:
            node = root[sec]
            validas[sec] = {
                "primera_lectura": limpiar_texto(node["primera_lectura"]),
                "profundizacion": limpiar_texto(node["profundizacion"]),
                "integracion": limpiar_texto(node["integracion"]),
            }

    extras = [k for k in root.keys() if k not in secciones]
    if extras:
        errores["extras"] = [f"Secciones no solicitadas: {extras}"]

    return errores, validas


def _validacion_global(secciones: Dict[str, Dict[str, str]]) -> List[str]:
    errores: List[str] = []

    for sec in SECCIONES_OBLIGATORIAS:
        if sec not in secciones:
            errores.append(f"Falta seccion final: {sec}")

    if errores:
        return errores

    totales: Dict[str, int] = {}
    for sec, node in secciones.items():
        totales[sec] = sum(contar_palabras(node.get(campo, "")) for campo in CAMPOS_OBLIGATORIOS)

    primeras = [totales[s] for s in SECCIONES_OBLIGATORIAS[:5]]
    ultimas = [totales[s] for s in SECCIONES_OBLIGATORIAS[-5:]]

    prom_primeras = sum(primeras) / max(1, len(primeras))
    prom_ultimas = sum(ultimas) / max(1, len(ultimas))

    if prom_ultimas < prom_primeras * 0.72:
        errores.append(
            "Las ultimas 5 secciones quedaron demasiado por debajo de las primeras 5. "
            "Esto indica perdida de calidad al final."
        )

    seccion_mas_corta = min(totales, key=totales.get)
    seccion_mas_larga = max(totales, key=totales.get)

    if totales[seccion_mas_corta] < max(260, int(totales[seccion_mas_larga] * 0.45)):
        errores.append(
            f"La seccion {seccion_mas_corta} quedo demasiado corta frente a {seccion_mas_larga}."
        )

    return errores


def _prompt_reparar_seccion(
    seccion: str,
    calculos: Dict[str, Any],
    secciones_generadas: Dict[str, Dict[str, str]],
    errores_previos: Optional[Dict[str, Any]] = None,
) -> str:
    """Prompt de emergencia: pide UNA sola seccion para evitar que el modelo omita claves."""
    return _prompt_bloque(
        [seccion],
        calculos,
        secciones_generadas,
        errores_previos=errores_previos,
    ) + f"""

MODO RESCATE DE UNA SOLA SECCION:
Genera UNICAMENTE la seccion {seccion}.
No incluyas otras secciones.
No resumas.
No bajes de los minimos.
La raiz debe ser exactamente: {{"secciones": {{"{seccion}": {{...}} }} }}.
"""


def _generar_seccion_individual_validada(
    seccion: str,
    calculos: Dict[str, Any],
    secciones_generadas: Dict[str, Dict[str, str]],
    errores_iniciales: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Recupera una seccion que falto o vino corta sin tirar todo el bloque.
    Esto reduce errores como: OpenAI genero mensaje_alma pero omitio las otras 4.
    """
    sexo = str(calculos.get("sexo", "neutral"))
    errores_previos = errores_iniciales or {}
    ultimo_error: Any = errores_previos

    for intento in range(1, MAX_REINTENTOS_BLOQUE + 3):
        prompt = _prompt_reparar_seccion(seccion, calculos, secciones_generadas, errores_previos)
        try:
            respuesta = llamar_openai(prompt)
            errores, validas = validar_bloque(respuesta, [seccion], sexo)
            if seccion in validas and not errores:
                return validas[seccion]
            ultimo_error = errores
            errores_previos = errores
        except Exception as exc:  # noqa: BLE001
            ultimo_error = str(exc)
            errores_previos = {"openai": [str(exc)]}

        if intento <= MAX_REINTENTOS_BLOQUE + 2:
            time.sleep(ESPERA_REINTENTO_SEGUNDOS)

    raise ErrorContenidoMapa(
        f"OpenAI no pudo reparar la seccion {seccion}. Errores: "
        + json.dumps(ultimo_error, ensure_ascii=False)
    )


def generar_bloque_validado(
    secciones: List[str],
    calculos: Dict[str, Any],
    secciones_generadas: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    sexo = str(calculos.get("sexo", "neutral"))
    faltantes = list(secciones)
    resultado_bloque: Dict[str, Dict[str, str]] = {}
    errores_previos: Optional[Dict[str, Any]] = None
    ultimo_error: Any = None

    # 1) Intento normal por bloque de 5 secciones.
    for intento in range(1, MAX_REINTENTOS_BLOQUE + 2):
        prompt = _prompt_bloque(
            faltantes,
            calculos,
            {**secciones_generadas, **resultado_bloque},
            errores_previos=errores_previos,
        )

        try:
            respuesta = llamar_openai(prompt)
            errores, validas = validar_bloque(respuesta, faltantes, sexo)

            for sec, contenido in validas.items():
                resultado_bloque[sec] = contenido

            faltantes = [sec for sec in faltantes if sec not in resultado_bloque]

            parcial = {
                "tipo": "mapa_del_alma_parcial",
                "calculos": calculos,
                "secciones": {**secciones_generadas, **resultado_bloque},
                "faltantes": faltantes,
                "errores": errores,
            }
            _guardar_json_nombre("PARCIAL", calculos, parcial)

            if not faltantes:
                return resultado_bloque

            errores_previos = errores
            ultimo_error = errores

        except Exception as exc:  # noqa: BLE001
            ultimo_error = str(exc)
            errores_previos = {"openai": [str(exc)]}

        if faltantes and intento <= MAX_REINTENTOS_BLOQUE + 1:
            time.sleep(ESPERA_REINTENTO_SEGUNDOS)

    # 2) Rescate: pedir una por una las secciones que faltaron o salieron invalidas.
    errores_rescate = errores_previos if isinstance(errores_previos, dict) else {}
    for sec in list(faltantes):
        contenido = _generar_seccion_individual_validada(
            sec,
            calculos,
            {**secciones_generadas, **resultado_bloque},
            errores_iniciales={sec: errores_rescate.get(sec, ultimo_error)},
        )
        resultado_bloque[sec] = contenido

        parcial = {
            "tipo": "mapa_del_alma_rescate_seccion",
            "calculos": calculos,
            "seccion_rescatada": sec,
            "secciones": {**secciones_generadas, **resultado_bloque},
            "faltantes": [s for s in secciones if s not in resultado_bloque],
        }
        _guardar_json_nombre("RESCATE", calculos, parcial)

    faltantes = [sec for sec in secciones if sec not in resultado_bloque]
    if not faltantes:
        return resultado_bloque

    raise ErrorContenidoMapa(
        "OpenAI no entrego contenido valido para las secciones "
        + json.dumps(faltantes, ensure_ascii=False)
        + ". Errores: "
        + json.dumps(ultimo_error, ensure_ascii=False)
    )

def generar_mapa_del_alma(
    nombre: str,
    nombre_completo: Optional[str] = None,
    fecha_nacimiento: Optional[str] = None,
    sexo: str = "neutral",
    pedido_id: Any = None,
    force_regenerate: bool = False,
) -> Dict[str, Any]:
    nombre = limpiar_texto(nombre)
    nombre_completo = limpiar_texto(nombre_completo or nombre)

    if not nombre:
        raise ValueError("Falta el nombre para generar el Mapa del Alma.")

    ruta_pedido = _ruta_json_pedido(pedido_id)
    if ruta_pedido and not force_regenerate:
        existente = _cargar_json_si_existe(ruta_pedido)
        if existente:
            existente["_json_guardado_en"] = str(ruta_pedido)
            existente["_reutilizado"] = True
            return existente

    calculos = crear_calculos(nombre, nombre_completo, fecha_nacimiento, sexo)
    secciones_finales: Dict[str, Dict[str, str]] = {}

    for bloque in BLOQUES:
        generado = generar_bloque_validado(bloque, calculos, secciones_finales)
        secciones_finales.update(generado)

        parcial_ok = {
            "tipo": "mapa_del_alma",
            "version": "premium_parcial_secciones_individuales",
            "calculos": calculos,
            "secciones": secciones_finales,
            "secciones_editoriales": secciones_finales,
        }
        _guardar_json_nombre(f"OK_SECCION_{len(secciones_finales)}", calculos, parcial_ok)

    errores_globales = _validacion_global(secciones_finales)
    if errores_globales:
        data_error = {
            "tipo": "mapa_del_alma_error_global",
            "version": "premium_error_global",
            "calculos": calculos,
            "secciones": secciones_finales,
            "errores": errores_globales,
        }
        _guardar_json_nombre("ERROR_GLOBAL", calculos, data_error)
        raise ErrorContenidoMapa("Validacion global fallida: " + json.dumps(errores_globales, ensure_ascii=False))

    final = {
        "tipo": "mapa_del_alma",
        "version": "premium_21_secciones_mas_notas_pdf",
        "calculos": calculos,
        "secciones": secciones_finales,
        "secciones_editoriales": secciones_finales,
    }

    if ruta_pedido:
        ruta = _guardar_json(ruta_pedido, final)
    else:
        ruta = _guardar_json_nombre("FINAL", calculos, final)

    final["_json_guardado_en"] = ruta
    final["_reutilizado"] = False

    return final


def generar_contenido(
    nombre: str,
    nombre_completo: Optional[str] = None,
    fecha_nacimiento: Optional[str] = None,
    sexo: str = "neutral",
) -> Dict[str, Any]:
    return generar_mapa_del_alma(nombre, nombre_completo, fecha_nacimiento, sexo)


def generar_texto_openai(
    nombre: str,
    nombre_completo: Optional[str] = None,
    fecha_nacimiento: Optional[str] = None,
    sexo: str = "neutral",
) -> Dict[str, Any]:
    return generar_mapa_del_alma(nombre, nombre_completo, fecha_nacimiento, sexo)


def generar_libro_nombre(
    nombre: str,
    nombre_completo: Optional[str] = None,
    fecha_nacimiento: Optional[str] = None,
    sexo: str = "neutral",
) -> Dict[str, Any]:
    return generar_mapa_del_alma(nombre, nombre_completo, fecha_nacimiento, sexo)


def generar_contenido_mapa(datos: Optional[dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    datos = datos or {}
    datos.update(kwargs)

    nombre = limpiar_texto(datos.get("nombre") or datos.get("first_name") or "")
    apellidos = limpiar_texto(datos.get("apellidos") or datos.get("last_name") or "")
    nombre_completo = limpiar_texto(datos.get("nombre_completo") or f"{nombre} {apellidos}".strip())
    fecha = limpiar_texto(datos.get("fecha_nacimiento") or datos.get("fecha") or datos.get("birthdate") or "")
    sexo = limpiar_texto(datos.get("sexo") or datos.get("genero") or datos.get("gender") or datos.get("forma_trato") or "neutral")
    pedido_id = datos.get("pedido_id") or datos.get("order_id") or datos.get("id")
    force_regenerate = bool(datos.get("force_regenerate") or datos.get("regenerar"))

    if not nombre:
        raise ValueError("Falta el nombre para generar el Mapa del Alma.")

    return generar_mapa_del_alma(
        nombre=nombre,
        nombre_completo=nombre_completo or nombre,
        fecha_nacimiento=fecha or None,
        sexo=sexo,
        pedido_id=pedido_id,
        force_regenerate=force_regenerate,
    )


if __name__ == "__main__":
    ejemplo = generar_contenido_mapa(
        {
            "pedido_id": 999999,
            "nombre": "Alma",
            "apellidos": "Rivera",
            "fecha_nacimiento": "2001-02-14",
            "sexo": "mujer",
        }
    )
    print(json.dumps(ejemplo, ensure_ascii=False, indent=2))