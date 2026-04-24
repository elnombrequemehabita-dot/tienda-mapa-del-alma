"""
Cálculos de carta natal (Sol), numerología, zodiaco chino y correspondencias coherentes
gobernadas por la semilla de identidad (nombre + fecha).
"""
from __future__ import annotations

import hashlib
import random
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Literal

from config import CHINESE_ANIMAL_FILES, CHINESE_ANIMAL_LABELS_ES, ELEMENT_IMAGE, ENERGY_FILES, PLANET_IMAGE, SIGN_IMAGE


SignKey = Literal[
    "aries",
    "tauro",
    "geminis",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "escorpion",
    "sagitario",
    "capricornio",
    "acuario",
    "piscis",
]

ElementKey = Literal["fuego", "tierra", "aire", "agua"]
EnergyKind = Literal["vital", "emocional", "mental"]
SexKey = Literal["femenino", "masculino"]
PerfilPsicologico = Literal[
    "controlador",
    "sobreanalitico",
    "evitador_emocional",
    "impulsivo",
    "adaptador",
    "independiente",
]

# --- Correspondencias signo/elemento → símbolos (coherencia editorial) ---

GEM_BY_ELEMENT: dict[ElementKey, list[str]] = {
    "fuego": ["rubi.png", "granate.png", "diamante.png", "topacio.png", "esmeralda.png"],
    "tierra": ["esmeralda.png", "peridot.png", "granate.png", "perla.png", "zafiro.png"],
    "aire": ["aguamarina.png", "amatista.png", "cristal_de_cuarzo.png", "turquesa.png", "diamante.png"],
    "agua": ["amatista.png", "perla.png", "turquesa.png", "aguamarina.png", "zafiro.png", "esmeralda.png"],
}

TOTEM_BY_ELEMENT: dict[ElementKey, list[str]] = {
    "fuego": ["leon.png", "pantera.png", "colibri.png"],
    "tierra": ["oso.png", "ciervo.png", "leon.png"],
    "aire": ["colibri.png", "delfin.png", "ciervo.png"],
    "agua": ["delfin.png", "ciervo.png", "oso.png", "pantera.png"],
}

# Pool por signo para reforzar diferenciación entre personas con distinto Sol.
# Si un signo no existe aquí, cae al pool por elemento.
TOTEM_BY_SIGN: dict[SignKey, list[str]] = {
    "aries": ["pantera.png", "leon.png"],
    "tauro": ["oso.png", "ciervo.png"],
    "geminis": ["colibri.png", "delfin.png"],
    "cancer": ["delfin.png", "oso.png"],
    "leo": ["leon.png", "pantera.png"],
    "virgo": ["ciervo.png", "oso.png"],
    "libra": ["colibri.png", "delfin.png"],
    "escorpion": ["pantera.png", "delfin.png"],
    "sagitario": ["leon.png", "colibri.png"],
    "capricornio": ["oso.png", "ciervo.png"],
    "acuario": ["delfin.png", "colibri.png"],
    "piscis": ["delfin.png", "ciervo.png"],
}

# Firma de tótem por perfil psicológico para reducir repeticiones entre clientes
# con perfiles distintos, incluso si comparten signo/elemento.
TOTEM_BY_PROFILE: dict[PerfilPsicologico, list[str]] = {
    "controlador": ["leon.png", "oso.png"],
    "sobreanalitico": ["ciervo.png", "delfin.png"],
    "evitador_emocional": ["pantera.png", "delfin.png"],
    "impulsivo": ["leon.png", "pantera.png"],
    "adaptador": ["colibri.png", "ciervo.png"],
    "independiente": ["oso.png", "pantera.png"],
}

ARCHANGEL_BY_PLANET: dict[str, list[str]] = {
    "sol": ["arcangel_miguel.png", "arcangel_Metatron.png", "arcangel_Zadkiel.png"],
    "luna": ["arcangel_gabriel.png", "arcangel_Sandalphon.png", "arcangel_rafael.png"],
    "mercurio": ["arcangel_gabriel.png", "arcangel_rafael.png", "arcangel_Metatron.png"],
    "venus": ["arcangel_uriel.png", "arcangel_Jofiel.png", "arcangel_gabriel.png"],
    "marte": ["arcangel_miguel.png", "arcangel_Chamuel.png", "arcangel_Jofiel.png"],
    "jupiter": ["arcangel_Zadkiel.png", "arcangel_Metatron.png", "arcangel_uriel.png"],
    "saturno": ["arcangel_uriel.png", "arcangel_Metatron.png", "arcangel_Sandalphon.png"],
}

# Opciones de energía compatibles con el temperamento elemental
ENERGY_BY_ELEMENT: dict[ElementKey, tuple[EnergyKind, ...]] = {
    "fuego": ("vital", "mental", "emocional"),
    "tierra": ("emocional", "vital", "mental"),
    "aire": ("mental", "vital", "emocional"),
    "agua": ("emocional", "mental", "vital"),
}


def identity_seed(nombre: str, fecha: date) -> int:
    """
    Semilla estable y única por persona. Alimenta random.Random para variantes narrativas
    y elecciones dentro de pools coherentes (gema, tótem, arcángel, matiz de energía).
    """
    payload = f"{nombre.strip().lower()}|{fecha.isoformat()}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def universe_fingerprint_code(nombre: str, fecha: date, seed: int) -> str:
    """Código único legible para la firma del universo en contraportada (no es PII reversible)."""
    raw = hashlib.sha256(
        f"FIRMA|{nombre.strip()}|{fecha.isoformat()}|{seed}".encode("utf-8")
    ).hexdigest()
    return " · ".join(raw[i : i + 4].upper() for i in range(0, 20, 4))


def _strip_accents(s: str) -> str:
    nf = unicodedata.normalize("NFD", s)
    return "".join(c for c in nf if unicodedata.category(c) != "Mn")


def _norm_name_token(s: str) -> str:
    s = _strip_accents(s.strip().lower())
    out = []
    for ch in s:
        if ch.isalpha() or ch in ("ñ",):
            out.append(ch)
    return "".join(out)


def sun_sign(d: date) -> SignKey:
    """Signo solar occidental por fecha (trópico)."""
    m, day = d.month, d.day
    if (m == 3 and day >= 21) or (m == 4 and day <= 19):
        return "aries"
    if (m == 4 and day >= 20) or (m == 5 and day <= 20):
        return "tauro"
    if (m == 5 and day >= 21) or (m == 6 and day <= 20):
        return "geminis"
    if (m == 6 and day >= 21) or (m == 7 and day <= 22):
        return "cancer"
    if (m == 7 and day >= 23) or (m == 8 and day <= 22):
        return "leo"
    if (m == 8 and day >= 23) or (m == 9 and day <= 22):
        return "virgo"
    if (m == 9 and day >= 23) or (m == 10 and day <= 22):
        return "libra"
    if (m == 10 and day >= 23) or (m == 11 and day <= 21):
        return "escorpion"
    if (m == 11 and day >= 22) or (m == 12 and day <= 21):
        return "sagitario"
    if (m == 12 and day >= 22) or (m == 1 and day <= 19):
        return "capricornio"
    if (m == 1 and day >= 20) or (m == 2 and day <= 18):
        return "acuario"
    return "piscis"


def element_for_sign(sign: SignKey) -> ElementKey:
    if sign in ("aries", "leo", "sagitario"):
        return "fuego"
    if sign in ("tauro", "virgo", "capricornio"):
        return "tierra"
    if sign in ("geminis", "libra", "acuario"):
        return "aire"
    return "agua"


def ruling_planet(sign: SignKey) -> str:
    return {
        "aries": "marte",
        "tauro": "venus",
        "geminis": "mercurio",
        "cancer": "luna",
        "leo": "sol",
        "virgo": "mercurio",
        "libra": "venus",
        "escorpion": "marte",
        "sagitario": "jupiter",
        "capricornio": "saturno",
        "acuario": "saturno",
        "piscis": "jupiter",
    }[sign]


def chinese_zodiac_index(year: int) -> int:
    return (year - 4) % 12


def digit_sum(n: int) -> int:
    s = 0
    while n > 0:
        s += n % 10
        n //= 10
    return s


def reduce_number(n: int) -> int:
    if n in (11, 22, 33):
        return n
    while n > 9:
        n = digit_sum(n)
        if n in (11, 22, 33):
            return n
    return n


def life_path_number(d: date) -> int:
    parts = [d.day, d.month, d.year]
    total = 0
    for p in parts:
        total += digit_sum(p)
    return reduce_number(total)


def _letter_value(ch: str) -> int:
    table = {
        **{c: 1 for c in "ajs"},
        **{c: 2 for c in "bkt"},
        **{c: 3 for c in "clu"},
        **{c: 4 for c in "dmv"},
        **{c: 5 for c in "enw"},
        **{c: 6 for c in "fox"},
        **{c: 7 for c in "gpy"},
        **{c: 8 for c in "hqz"},
        **{c: 9 for c in "ir"},
    }
    return table.get(ch, 0)


def expression_number(full_name: str) -> int:
    name = _norm_name_token(full_name.replace("ñ", "n"))
    total = sum(_letter_value(c) for c in name if c.isalpha())
    if total == 0:
        return 1
    return reduce_number(digit_sum(total))


def soul_urge_number(full_name: str) -> int:
    vowels = set("aeiou")
    name = _norm_name_token(full_name)
    total = sum(_letter_value(c) for c in name if c in vowels)
    if total == 0:
        return expression_number(full_name)
    return reduce_number(digit_sum(total))


def personality_number(full_name: str) -> int:
    vowels = set("aeiou")
    name = _norm_name_token(full_name)
    total = sum(_letter_value(c) for c in name if c.isalpha() and c not in vowels)
    if total == 0:
        return expression_number(full_name)
    return reduce_number(digit_sum(total))


def digits_for_numerology_stamp(n: int) -> list[int]:
    """Cifras 1..9 para cargar 1.png…9.png; maestros 11/22/33 como dos dígitos."""
    if n in (11, 22, 33):
        return [int(ch) for ch in str(n)]
    if 1 <= n <= 9:
        return [n]
    x = max(1, n)
    while x > 9:
        x = digit_sum(x)
        if x in (11, 22, 33):
            return [int(ch) for ch in str(x)]
    return [x]


def pick_coherent_energy(elem: ElementKey, camino: int, expresion: int, seed: int) -> EnergyKind:
    opts = ENERGY_BY_ELEMENT[elem]
    idx = (camino * 7 + expresion * 11 + (seed % 1_000_003)) % len(opts)
    return opts[idx]


def energy_image_index(kind: EnergyKind, camino: int, seed: int) -> int:
    rng = random.Random(seed ^ 0x9E3779B9)
    base = {"vital": 1, "emocional": 2, "mental": 3}[kind]
    offset = (camino + rng.randint(0, 2)) % 3
    idx = base + offset - 1
    if idx < 1:
        idx = 1
    if idx > 5:
        idx = 5
    return idx


def _is_compound_name(nombre_pila: str) -> bool:
    return len([t for t in (nombre_pila or "").split() if t.strip()]) > 1


def determinar_perfil(
    nombre: str,
    fecha: date,
    signo: SignKey,
    *,
    camino_vida: int,
    expresion: int,
    alma: int,
    personalidad: int,
) -> PerfilPsicologico:
    perfiles: dict[str, float] = {
        "controlador": 0.0,
        "sobreanalitico": 0.0,
        "evitador_emocional": 0.0,
        "impulsivo": 0.0,
        "adaptador": 0.0,
        "independiente": 0.0,
    }

    # Peso alto: numerología.
    if camino_vida in (1, 8):
        perfiles["controlador"] += 3.4
        perfiles["independiente"] += 2.3
        perfiles["impulsivo"] += 1.0
    elif camino_vida in (2, 6):
        perfiles["adaptador"] += 3.1
        perfiles["evitador_emocional"] += 2.2
    elif camino_vida in (3, 5):
        perfiles["impulsivo"] += 3.0
        perfiles["sobreanalitico"] += 1.4
        perfiles["adaptador"] += 0.8
    elif camino_vida in (4, 7):
        perfiles["sobreanalitico"] += 3.2
        perfiles["controlador"] += 1.6
    elif camino_vida in (9, 11, 22, 33):
        perfiles["evitador_emocional"] += 2.0
        perfiles["adaptador"] += 1.8
        perfiles["independiente"] += 1.4

    if expresion in (1, 8):
        perfiles["controlador"] += 1.4
    if expresion in (4, 7):
        perfiles["sobreanalitico"] += 1.6
    if expresion in (3, 5):
        perfiles["impulsivo"] += 1.3
    if expresion in (2, 6, 9):
        perfiles["adaptador"] += 1.2

    if alma in (2, 6, 9):
        perfiles["evitador_emocional"] += 1.5
        perfiles["adaptador"] += 1.0
    if alma in (1, 8):
        perfiles["independiente"] += 1.2

    if personalidad in (4, 7):
        perfiles["sobreanalitico"] += 1.1
    if personalidad in (1, 8):
        perfiles["controlador"] += 0.9

    # Signo zodiacal.
    if signo in ("aries", "leo", "sagitario"):
        perfiles["impulsivo"] += 1.6
        perfiles["independiente"] += 0.7
    elif signo in ("tauro", "capricornio"):
        perfiles["controlador"] += 1.5
        perfiles["sobreanalitico"] += 0.8
    elif signo in ("virgo", "geminis"):
        perfiles["sobreanalitico"] += 1.7
    elif signo in ("cancer", "piscis"):
        perfiles["evitador_emocional"] += 1.6
        perfiles["adaptador"] += 1.0
    elif signo in ("libra",):
        perfiles["adaptador"] += 1.8
    elif signo in ("escorpion", "acuario"):
        perfiles["independiente"] += 1.4
        perfiles["evitador_emocional"] += 0.8

    # Longitud y estructura del nombre.
    clean_name = _norm_name_token(nombre or "")
    nlen = len(clean_name)
    if nlen <= 5:
        perfiles["impulsivo"] += 0.6
    elif nlen >= 10:
        perfiles["sobreanalitico"] += 0.6
        perfiles["adaptador"] += 0.4
    if _is_compound_name(nombre):
        perfiles["adaptador"] += 0.8
        perfiles["evitador_emocional"] += 0.6
    else:
        perfiles["independiente"] += 0.4

    # Variación pseudoaleatoria estable por identidad (evita clones).
    seed = identity_seed(nombre, fecha)
    rng = random.Random(seed ^ 0xA5A5_5A5A)
    jitter_order = [
        "controlador",
        "sobreanalitico",
        "evitador_emocional",
        "impulsivo",
        "adaptador",
        "independiente",
    ]
    for key in jitter_order:
        perfiles[key] += rng.uniform(0.0, 0.45)

    return max(perfiles.items(), key=lambda kv: kv[1])[0]  # type: ignore[return-value]


def sign_label_es(sign: SignKey) -> str:
    return {
        "aries": "Aries",
        "tauro": "Tauro",
        "geminis": "Géminis",
        "cancer": "Cáncer",
        "leo": "Leo",
        "virgo": "Virgo",
        "libra": "Libra",
        "escorpion": "Escorpio",
        "sagitario": "Sagitario",
        "capricornio": "Capricornio",
        "acuario": "Acuario",
        "piscis": "Piscis",
    }[sign]


def element_label_es(el: ElementKey) -> str:
    return {"fuego": "Fuego", "tierra": "Tierra", "aire": "Aire", "agua": "Agua"}[el]


def planet_label_es(p: str) -> str:
    return {
        "sol": "Sol",
        "luna": "Luna",
        "mercurio": "Mercurio",
        "venus": "Venus",
        "marte": "Marte",
        "jupiter": "Júpiter",
        "saturno": "Saturno",
    }.get(p, p.title())


def sign_label(sign: SignKey) -> str:
    return sign_label_es(sign)


def element_label(el: ElementKey) -> str:
    return element_label_es(el)


def planet_label(p: str) -> str:
    return planet_label_es(p)


def month_name(month: int) -> str:
    months = [
        "",
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    return months[month]


def long_birth_date(d: date) -> str:
    return f"{d.day} de {month_name(d.month)} de {d.year}"


def split_nombre_pila_apellidos(nombre_completo: str) -> tuple[str, str]:
    """
    Heurística española: primera palabra = nombre de pila; el resto = apellidos.
    Para nombres compuestos muy específicos, usar --apellidos en CLI.
    """
    parts = nombre_completo.split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


@dataclass(frozen=True)
class SoulProfile:
    nombre: str
    nombre_pila: str
    apellidos: str
    sexo: SexKey
    fecha: date
    seed: int
    signo: SignKey
    elemento: ElementKey
    planeta_regente: str
    animal_chino_idx: int
    animal_chino: str
    camino_vida: int
    expresion: int
    alma: int
    personalidad: int
    energia: EnergyKind
    energia_png_index: int
    perfil_psicologico: PerfilPsicologico
    totem_file: str
    gema_file: str
    arcangel_file: str

    @property
    def sign_label(self) -> str:
        return sign_label(self.signo)

    @property
    def element_label(self) -> str:
        return element_label(self.elemento)

    @property
    def planet_label(self) -> str:
        return planet_label(self.planeta_regente)

    @property
    def weekday_es(self) -> str:
        names = [
            "lunes",
            "martes",
            "miércoles",
            "jueves",
            "viernes",
            "sábado",
            "domingo",
        ]
        return names[self.fecha.weekday()]

    @property
    def birth_day_of_month(self) -> int:
        return self.fecha.day

    @property
    def birth_month_name(self) -> str:
        return month_name(self.fecha.month)

    @property
    def age_years(self) -> int:
        today = date.today()
        y = today.year - self.fecha.year
        if (today.month, today.day) < (self.fecha.month, self.fecha.day):
            y -= 1
        return max(y, 0)


def build_profile(
    nombre: str,
    fecha: date,
    *,
    apellidos: str | None = None,
    sexo: str | None = None,
) -> SoulProfile:
    nombre = nombre.strip()
    if apellidos is not None:
        ap = apellidos.strip()
        nombre_pila = nombre
        nombre_completo = f"{nombre_pila} {ap}".strip() if ap else nombre_pila
    else:
        nombre_completo = nombre
        nombre_pila, ap = split_nombre_pila_apellidos(nombre_completo)

    sx_raw = (sexo or "femenino").strip().lower()
    if sx_raw in ("f", "fem", "femenino", "mujer"):
        sx: SexKey = "femenino"
    elif sx_raw in ("m", "masc", "masculino", "hombre"):
        sx = "masculino"
    else:
        raise ValueError("sexo inválido: usa femenino/f o masculino/m")
    seed = identity_seed(nombre_completo, fecha)
    rng = random.Random(seed)

    sign = sun_sign(fecha)
    elem = element_for_sign(sign)
    planet = ruling_planet(sign)
    cz = chinese_zodiac_index(fecha.year)
    animal = CHINESE_ANIMAL_LABELS_ES[cz]

    lp = life_path_number(fecha)
    expr = expression_number(nombre_completo)
    soul = soul_urge_number(nombre_completo)
    pers = personality_number(nombre_completo)

    energy = pick_coherent_energy(elem, lp, expr, seed)
    eidx = energy_image_index(energy, lp, seed)
    perfil = determinar_perfil(
        nombre_pila,
        fecha,
        sign,
        camino_vida=lp,
        expresion=expr,
        alma=soul,
        personalidad=pers,
    )

    gema = rng.choice(GEM_BY_ELEMENT[elem])
    base_totem_pool = TOTEM_BY_SIGN.get(sign) or TOTEM_BY_ELEMENT[elem]
    profile_totem_pool = TOTEM_BY_PROFILE.get(perfil, [])
    totem_pool = [t for t in profile_totem_pool if t in base_totem_pool] or profile_totem_pool or base_totem_pool
    totem = rng.choice(totem_pool)
    arch_pool = ARCHANGEL_BY_PLANET.get(planet) or list(
        {a for pool in ARCHANGEL_BY_PLANET.values() for a in pool}
    )
    arcangel = rng.choice(arch_pool)

    return SoulProfile(
        nombre=nombre_completo,
        nombre_pila=nombre_pila,
        apellidos=ap,
        sexo=sx,
        fecha=fecha,
        seed=seed,
        signo=sign,
        elemento=elem,
        planeta_regente=planet,
        animal_chino_idx=cz,
        animal_chino=animal,
        camino_vida=lp,
        expresion=expr,
        alma=soul,
        personalidad=pers,
        energia=energy,
        energia_png_index=eidx,
        perfil_psicologico=perfil,
        totem_file=totem,
        gema_file=gema,
        arcangel_file=arcangel,
    )


def expected_image_paths(profile: SoulProfile) -> dict[str, str]:
    ch_file = CHINESE_ANIMAL_FILES[profile.animal_chino_idx]
    energy_name = (
        ENERGY_FILES[0]
        if profile.energia_png_index == 0
        else f"energia{profile.energia_png_index}.png"
    )
    return {
        "signo": SIGN_IMAGE[profile.signo],
        "elemento": ELEMENT_IMAGE[profile.elemento],
        "planeta": PLANET_IMAGE[profile.planeta_regente],
        "totem": profile.totem_file,
        "gema": profile.gema_file,
        "arcangel": profile.arcangel_file,
        "chino": ch_file,
        "energia": energy_name,
    }


# --- API explícita para PDF y utilidades (mapeo por diccionarios en config + perfil) ---


def obtener_signo_zodiacal(fecha: date) -> SignKey:
    return sun_sign(fecha)


def obtener_elemento(signo: SignKey) -> ElementKey:
    return element_for_sign(signo)


def obtener_planeta_regente(signo: SignKey) -> str:
    return ruling_planet(signo)


def obtener_totem(profile: SoulProfile) -> str:
    return profile.totem_file


def obtener_arcangel(profile: SoulProfile) -> str:
    return profile.arcangel_file


def obtener_gema(profile: SoulProfile) -> str:
    return profile.gema_file


def obtener_zodiaco_chino(fecha: date) -> str:
    return CHINESE_ANIMAL_LABELS_ES[chinese_zodiac_index(fecha.year)]
