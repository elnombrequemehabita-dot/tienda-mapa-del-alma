"""
Onomástica aplicada para Mapa del Alma.

Entrega bloques editoriales con base filológica:
- nombre de pila: raíz lingüística, etimón y evolución cultural.
- apellidos: origen (patronímico, toponímico, oficio, etc.) y lectura heráldica general.

No pretende ser una enciclopedia total: usa base curada + heurísticas transparentes.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
import re
import unicodedata


@dataclass(frozen=True)
class NameEtymology:
    canonical: str
    root_language: str
    etymon: str
    historical_meaning: str
    cultural_path: str
    symbolic_evolution: str


@dataclass(frozen=True)
class SurnameOrigin:
    canonical: str
    origin_type: str
    source_region: str
    historical_note: str
    heraldic_force: str


_NAME_DB: dict[str, NameEtymology] = {
    "diego": NameEtymology(
        canonical="Diego",
        root_language="uso medieval ibérico documentado",
        etymon="Didacus (forma medieval usada en registros hispanos)",
        historical_meaning=(
            "Se asocia con la idea de asumir lugar, responsabilidad y continuidad dentro del grupo."
        ),
        cultural_path=(
            "Su uso crece en la Península Ibérica medieval y se consolida en América como nombre de autoridad cercana."
        ),
        symbolic_evolution=(
            "Hoy se vincula con liderazgo práctico, protección del entorno y tendencia a cargar más de la cuenta."
        ),
    ),
    "maria": NameEtymology(
        canonical="María",
        root_language="hebreo bíblico, vía griego y latín",
        etymon="Miryam / Mariam",
        historical_meaning=(
            "Su interpretación histórica más aceptada oscila entre 'la amada', "
            "'la excelsa' y 'la rebelde'."
        ),
        cultural_path=(
            "Se difunde del hebreo al griego koiné (Mariam/María) y luego al latín cristiano, "
            "convirtiéndose en uno de los nombres más extendidos de Europa e Hispanoamérica."
        ),
        symbolic_evolution=(
            "Pasó de nombre de filiación religiosa a símbolo de fortaleza serena, cuidado y resistencia íntima."
        ),
    ),
    "jose": NameEtymology(
        canonical="José",
        root_language="hebreo bíblico",
        etymon="Yosef",
        historical_meaning="Literalmente 'Dios añadirá' o 'que se agregue'.",
        cultural_path=(
            "Entra al mundo hispano desde la tradición judeocristiana y adquiere gran peso "
            "en registros parroquiales, civiles y dinásticos."
        ),
        symbolic_evolution=(
            "Evoluciona hacia la idea de sostén, continuidad familiar y labor paciente."
        ),
    ),
    "juan": NameEtymology(
        canonical="Juan",
        root_language="hebreo, vía griego y latín",
        etymon="Yohanan",
        historical_meaning="Se traduce como 'Dios es misericordioso' o 'gracia divina'.",
        cultural_path=(
            "Uno de los nombres más persistentes en la documentación medieval ibérica y americana."
        ),
        symbolic_evolution=(
            "Con el tiempo adopta una lectura de honestidad directa y carácter estable."
        ),
    ),
    "ana": NameEtymology(
        canonical="Ana",
        root_language="hebreo",
        etymon="Hannah",
        historical_meaning="Gracia, favor o benevolencia.",
        cultural_path=(
            "Nombre de larga continuidad en tradiciones semíticas y cristianas, frecuente "
            "en onomástica conventual y civil."
        ),
        symbolic_evolution=(
            "Se asocia a templanza, lucidez emocional y una ética del cuidado sin estridencia."
        ),
    ),
    "sofia": NameEtymology(
        canonical="Sofía",
        root_language="griego clásico",
        etymon="Sophía",
        historical_meaning="Sabiduría.",
        cultural_path=(
            "Del léxico filosófico griego pasa a la tradición cristiana y luego a la onomástica moderna."
        ),
        symbolic_evolution=(
            "Su lectura actual combina inteligencia analítica con criterio ético."
        ),
    ),
    "lucia": NameEtymology(
        canonical="Lucía",
        root_language="latín",
        etymon="Lux / Lucis",
        historical_meaning="Luz; vinculada al amanecer o a quien trae claridad.",
        cultural_path=(
            "Muy presente en la tradición latina y mediterránea, con fuerte arraigo en España e Italia."
        ),
        symbolic_evolution=(
            "Evoluciona hacia el simbolismo de claridad mental y firmeza luminosa."
        ),
    ),
    "carlos": NameEtymology(
        canonical="Carlos",
        root_language="germánico",
        etymon="Karl",
        historical_meaning="Hombre libre.",
        cultural_path=(
            "Su prestigio crece por el uso dinástico carolingio y su expansión en Europa occidental."
        ),
        symbolic_evolution=(
            "En clave moderna suele leerse como autonomía, responsabilidad y capacidad de mando."
        ),
    ),
    "laura": NameEtymology(
        canonical="Laura",
        root_language="latín",
        etymon="Laurus",
        historical_meaning="Laurel; emblema clásico de victoria y honor.",
        cultural_path=(
            "Se consolida en la tradición literaria europea desde la Edad Media."
        ),
        symbolic_evolution=(
            "Deriva hacia una imagen de mérito, constancia y elegancia sobria."
        ),
    ),
    "gabriel": NameEtymology(
        canonical="Gabriel",
        root_language="hebreo bíblico, vía tradición judeocristiana",
        etymon="Gavri'el",
        historical_meaning="Se interpreta como 'Dios es mi fuerza' o 'fortaleza de Dios'.",
        cultural_path=(
            "Se difunde en la tradición bíblica y litúrgica, y pasa al mundo hispano como nombre de mensajero y autoridad espiritual."
        ),
        symbolic_evolution=(
            "En uso actual suele reflejar voz firme, necesidad de verdad directa y tensión entre proteger a otros y no tragarse lo propio."
        ),
    ),
    "valentina": NameEtymology(
        canonical="Valentina",
        root_language="latín tardío",
        etymon="Valentinus / Valens",
        historical_meaning="Se asocia con 'valiente', 'fuerte' y 'de vigor firme'.",
        cultural_path=(
            "Surge del latín imperial y se consolida en Europa cristiana; en Hispanoamérica toma una lectura de carácter, temple y dignidad."
        ),
        symbolic_evolution=(
            "Hoy expresa coraje emocional, dificultad para mostrarse vulnerable y tendencia a cargar en silencio para no parecer frágil."
        ),
    ),
    "camila": NameEtymology(
        canonical="Camila",
        root_language="latín clásico",
        etymon="Camillus / Camilla",
        historical_meaning=(
            "En Roma antigua nombraba a quien servía en rituales; hoy se lee como 'la que sirve con propósito' o 'mensajera dedicada'."
        ),
        cultural_path=(
            "Pasa del mundo romano a la tradición hispana moderna, conservando la idea de servicio, presencia y responsabilidad relacional."
        ),
        symbolic_evolution=(
            "En clave actual señala capacidad de sostener a otros, pero también riesgo de olvidarse de sí por exceso de entrega."
        ),
    ),
}

_SURNAME_DB: dict[str, SurnameOrigin] = {
    "ramirez": SurnameOrigin(
        canonical="Ramírez",
        origin_type="patronímico",
        source_region="Castilla y expansión hispanoamericana",
        historical_note="Significa 'hijo de Ramiro', con tradición de linajes de servicio, defensa y organización familiar.",
        heraldic_force=(
            "Se asocia a responsabilidad de sostén, lealtad en crisis y mandato de dar la cara por los suyos."
        ),
    ),
    "garcia": SurnameOrigin(
        canonical="García",
        origin_type="patronímico / antropónimo medieval",
        source_region="norte de la Península Ibérica",
        historical_note=(
            "Apellido de raíz muy antigua en la tradición hispánica; "
            "se vive como marca de persistencia, pertenencia y memoria familiar."
        ),
        heraldic_force=(
            "En tradición heráldica hispana aparece asociado a casas de servicio militar, "
            "tenacidad territorial y expansión familiar."
        ),
    ),
    "lopez": SurnameOrigin(
        canonical="López",
        origin_type="patronímico",
        source_region="ámbito hispánico medieval",
        historical_note="Significa 'hijo de Lope'; es un patronímico clásico de raíz ibérica.",
        heraldic_force=(
            "Connota continuidad de linaje, transmisión de autoridad doméstica y deber de representación."
        ),
    ),
    "martinez": SurnameOrigin(
        canonical="Martínez",
        origin_type="patronímico",
        source_region="Castilla y León, expansión peninsular",
        historical_note="Deriva de 'hijo de Martín', nombre vinculado al latín Martinus.",
        heraldic_force=(
            "Suele asociarse a disciplina, trabajo sostenido y fidelidad al oficio."
        ),
    ),
    "rodriguez": SurnameOrigin(
        canonical="Rodríguez",
        origin_type="patronímico",
        source_region="hispánico medieval",
        historical_note="Significa 'hijo de Rodrigo' (de raíz germánica, 'fama' + 'poder').",
        heraldic_force=(
            "Porta una tradición de mando, defensa del clan y reputación pública."
        ),
    ),
    "fernandez": SurnameOrigin(
        canonical="Fernández",
        origin_type="patronímico",
        source_region="reinos ibéricos medievales",
        historical_note="Significa 'hijo de Fernando'; este nombre proviene de raíces germánicas.",
        heraldic_force=(
            "Simboliza perseverancia, pacto de lealtad y estructura familiar sólida."
        ),
    ),
}


def _normalize_token(token: str) -> str:
    nf = unicodedata.normalize("NFKD", token or "")
    no_marks = "".join(ch for ch in nf if not unicodedata.combining(ch))
    clean = re.sub(r"[^a-zA-Z]", "", no_marks).lower().strip()
    return clean


def _titlecase(token: str) -> str:
    t = (token or "").strip()
    return t[:1].upper() + t[1:].lower() if t else t


def _symbolic_origin_label(origin_type: str) -> str:
    o = (origin_type or "").strip().lower()
    if "patron" in o:
        return "memoria de linaje y pertenencia"
    if "territorial" in o:
        return "raíces de territorio emocional"
    if "oficio" in o:
        return "herencia de trabajo y sostén"
    if "compuesto" in o:
        return "identidad compuesta en capas"
    return "historia familiar con peso simbólico"


_CONNECTOR_TOKENS = {"de", "del", "la", "las", "los"}


@dataclass(frozen=True)
class NameAnalysis:
    kind: str  # conocido | raro | compuesto
    full: str
    primary: str
    secondary_parts: tuple[str, ...]
    primary_key: str
    known_primary: NameEtymology | None
    known_secondary: tuple[NameEtymology | None, ...]


def _split_name_parts(nombre_pila: str) -> tuple[str, tuple[str, ...]]:
    tokens = [t for t in re.split(r"\s+", (nombre_pila or "").strip()) if t]
    if not tokens:
        return "Nombre", tuple()
    primary = tokens[0]
    if len(tokens) == 1:
        return primary, tuple()
    parts: list[str] = []
    i = 1
    while i < len(tokens):
        tk = tokens[i]
        low = _normalize_token(tk)
        if low in ("de", "del"):
            start = i
            i += 1
            while i < len(tokens) and _normalize_token(tokens[i]) in ("la", "las", "los"):
                i += 1
            if i < len(tokens):
                i += 1
            parts.append(" ".join(tokens[start:i]))
            continue
        parts.append(tk)
        i += 1
    return primary, tuple(parts)


def _meaningful_key(fragment: str) -> str:
    for tk in [t for t in re.split(r"\s+", (fragment or "").strip()) if t]:
        key = _normalize_token(tk)
        if key and key not in _CONNECTOR_TOKENS:
            return key
    return ""


def detect_name_profile_type(nombre_pila: str) -> str:
    analysis = _analyze_name(nombre_pila)
    return analysis.kind


def _analyze_name(nombre_pila: str) -> NameAnalysis:
    full = (nombre_pila or "").strip() or "Nombre"
    primary, secondary = _split_name_parts(full)
    primary_key = _meaningful_key(primary)
    known_primary = _NAME_DB.get(primary_key)
    known_secondary: list[NameEtymology | None] = []
    for part in secondary:
        known_secondary.append(_NAME_DB.get(_meaningful_key(part)))
    if secondary:
        kind = "compuesto"
    elif known_primary is not None:
        kind = "conocido"
    else:
        kind = "raro"
    return NameAnalysis(
        kind=kind,
        full=full,
        primary=primary,
        secondary_parts=secondary,
        primary_key=primary_key,
        known_primary=known_primary,
        known_secondary=tuple(known_secondary),
    )


def _numerology_profile_phrase(
    rng: random.Random,
    camino_vida: int,
    expresion: int,
    alma: int,
    perfil_psicologico: str | None,
) -> tuple[str, str]:
    perfil = (perfil_psicologico or "").strip().lower()
    if camino_vida in (1, 8):
        impactos = (
            "Sueles vivir el nombre desde liderazgo y autoexigencia: tomas el control rápido, "
            "pero te cuesta bajar la guardia cuando no tienes certeza.",
            "Tu nombre se siente como mandato de dirección: avanzas, organizas y sostienes, aunque a veces pagues con tensión interna.",
            "El nombre te empuja a ocupar lugar visible: asumes responsabilidad y cuesta pedir descanso sin culpa.",
        )
        acciones = (
            "Antes de resolver por todas las personas, pregunta una sola vez quién se hace cargo y sostén ese límite.",
            "Elige una sola prioridad de la semana y delega un tramo concreto sin recuperarlo por ansiedad.",
            "Escribe tres límites que sí te corresponden esta semana y cumple uno hoy sin negociarlo.",
        )
    elif camino_vida in (2, 6):
        impactos = (
            "Tu tendencia es sostener vínculos y responsabilidades por lealtad, incluso cuando eso te deja al final de tu propia lista.",
            "Tu nombre se vive como cuidado y contención: das estabilidad, aunque a veces te quedas sin espacio propio.",
            "El nombre te inclina a medir el ambiente antes de pedir: priorizas armonía y pagas con cansancio acumulado.",
        )
        acciones = (
            "Esta semana di un no claro en un lugar donde sueles ceder por culpa.",
            "Hoy elige un pedido mínimo de reciprocidad en un vínculo clave y mantenlo 72 horas.",
            "Agenda 20 minutos solo para ti y protégelos como un compromiso serio, sin disculparte.",
        )
    elif camino_vida in (3, 5):
        impactos = (
            "Tu energía mezcla agilidad y cambio: te mueves rápido entre roles, y bajo presión cuesta sostener foco.",
            "Tu nombre se vive con curiosidad y movimiento: exploras opciones, aunque a veces te cueste cerrar ciclos.",
            "El nombre te impulsa a buscar estímulo y libertad; el riesgo es dispersarte cuando la emoción sube.",
        )
        acciones = (
            "Elige una decisión pendiente y no la reabras durante siete días.",
            "Cierra una conversación pendiente con una frase directa y evita abrir tres temas nuevos el mismo día.",
            "Define una sola meta creativa o social de la semana y elimina dos distracciones que la roban tiempo.",
        )
    else:
        impactos = (
            "Tu nombre se vive con sentido de estructura y responsabilidad; el riesgo es cargar de más para evitar errores.",
            "El nombre te pide orden y consistencia: cumples, aunque a veces te rigidices cuando hay incertidumbre.",
            "Tu firma nominal se asocia a trabajo serio: sostienes procesos largos y cuesta aflojar sin sentir culpa.",
        )
        acciones = (
            "Define por escrito qué sí te toca y qué no vas a cargar esta semana.",
            "Elige una tarea que hoy harás 'suficientemente bien' y ciérrala sin rehacerla.",
            "Pide una sola ayuda concreta en algo que normalmente resuelves solo por inercia.",
        )
    impacto = rng.choice(impactos)
    accion = rng.choice(acciones)
    if perfil == "adaptador" and camino_vida in (3, 5):
        impacto = rng.choice(
            (
                impacto,
                "Tu nombre se vive con flexibilidad social: ajustas ritmo para encajar, y eso te cuesta sostener prioridades propias.",
            )
        )
    if perfil == "evitador_emocional" and camino_vida in (2, 6):
        impacto = rng.choice(
            (
                impacto,
                "Tu nombre se vive como contención silenciosa: cuidas al otro primero y posergas lo que te incomoda.",
            )
        )
    if perfil == "independiente" and camino_vida in (1, 8):
        impacto = rng.choice(
            (
                impacto,
                "Tu nombre se vive desde autosuficiencia: lideras y resolves, aunque a veces te cueste pedir apoyo a tiempo.",
            )
        )
    cierre = (
        f"Camino {camino_vida}, expresión {expresion} y alma {alma} marcan el matiz: no es destino fijo, es patrón de decisión que se puede dirigir."
    )
    return f"{impacto} {cierre}", accion


def _perfil_psicologico_hint(perfil_psicologico: str | None) -> str:
    hints = {
        "controlador": "Tu patrón psicológico base tiende al control preventivo: quieres evitar errores antes de que aparezcan.",
        "sobreanalitico": "Tu patrón psicológico base es sobreanalítico: procesas mucho antes de moverte y eso puede frenarte.",
        "evitador_emocional": "Tu patrón psicológico base evita el conflicto directo: callas, acumulas y reaccionas tarde.",
        "impulsivo": "Tu patrón psicológico base es impulsivo: actúas rápido y muchas veces corriges después.",
        "adaptador": "Tu patrón psicológico base es adaptador: priorizas aceptación y a veces dejas tu identidad en segundo plano.",
        "independiente": "Tu patrón psicológico base es independiente: resuelves sola o solo y te cuesta pedir apoyo a tiempo.",
    }
    return hints.get((perfil_psicologico or "").strip().lower(), "")


def _sound_symbolic_read(name: str) -> str:
    key = _normalize_token(name)
    vowels = sum(1 for ch in key if ch in "aeiou")
    ratio = (vowels / len(key)) if key else 0.5
    has_hard = any(ch in key for ch in ("k", "x", "z", "r"))
    if has_hard and ratio < 0.48:
        return (
            "Su sonoridad es firme y directa, con una presencia que suele marcar carácter antes de que la persona explique quién es."
        )
    if ratio > 0.55:
        return (
            "Su sonoridad es abierta y fluida, y suele transmitir cercanía, sensibilidad y capacidad de adaptación."
        )
    return (
        "Su sonoridad combina fuerza y flexibilidad, por eso suele percibirse como un nombre difícil de encasillar."
    )


def _rare_name_lived_experience(rng: random.Random, primary: str, nombre_completo: str) -> str:
    """Lectura simbólica honesta para nombres no documentados: sin inventar etimología."""
    key = _normalize_token(primary)
    n = len(key)
    vowels = sum(1 for ch in key if ch in "aeiou")
    ratio = (vowels / n) if n else 0.5
    parts = [p for p in re.split(r"[\s\-]+", nombre_completo.strip()) if p]
    n_tokens = len(parts)
    opts: list[str] = []
    if n <= 4:
        opts.append(
            f"En uso cotidiano, <i>{primary}</i> funciona como firma breve: se pronuncia rápido, se recuerda y obliga a una presencia clara."
        )
    if n >= 9:
        opts.append(
            f"En uso cotidiano, <i>{primary}</i> ocupa espacio en la boca y en la memoria: se siente como nombre de trayectoria, no de paso."
        )
    if ratio >= 0.55:
        opts.append(
            f"En la práctica, <i>{primary}</i> suele percibirse como cercano y fluido, aunque el mundo lo lea primero por rareza y después por carácter."
        )
    elif ratio <= 0.42:
        opts.append(
            f"En la práctica, <i>{primary}</i> suele percibirse como contundente: marca terreno antes de explicar intenciones."
        )
    if any(ch in key for ch in ("x", "z", "k")):
        opts.append(
            f"En entornos conservadores, <i>{primary}</i> se vive como nombre que rompe expectativa: eso puede ser ventaja de marca o costo de explicación constante."
        )
    if n_tokens >= 3:
        opts.append(
            f"En {nombre_completo}, el nombre completo funciona como identidad compuesta: cada pieza aporta tono distinto y la gente te lee por capas, no por una sola etiqueta."
        )
    if not opts:
        opts.append(
            f"En la vida real, <i>{primary}</i> se vive como nombre propio con peso propio: no entra fácil en plantillas, y eso te empuja a definirte con más precisión que la media."
        )
    return rng.choice(opts)


def _compose_known_name_block(
    analysis: NameAnalysis,
    nombre_completo: str,
    camino_vida: int,
    expresion: int,
    alma: int,
    perfil_psicologico: str | None,
    rng: random.Random,
) -> str:
    assert analysis.known_primary is not None
    ne = analysis.known_primary
    impacto, accion = _numerology_profile_phrase(rng, camino_vida, expresion, alma, perfil_psicologico)
    perfil_hint = _perfil_psicologico_hint(perfil_psicologico)
    impacto_txt = f"{impacto} {perfil_hint}".strip()
    return (
        f"<b>Origen real.</b> {ne.canonical} proviene de {ne.root_language}. "
        f"Está documentado en la forma <i>{ne.etymon}</i>."
        f"<br/><br/>"
        f"<b>Significado claro.</b> {ne.historical_meaning}"
        f"<br/><br/>"
        f"<b>Traducción a la vida real.</b> En {nombre_completo}, este nombre suele reflejarse así: {ne.symbolic_evolution}"
        f"<br/><br/>"
        f"<b>Impacto emocional.</b> {impacto_txt}"
        f"<br/><br/>"
        f"<b>Acción concreta.</b> {accion}"
    )


def _compose_rare_name_block(
    analysis: NameAnalysis,
    nombre_completo: str,
    camino_vida: int,
    expresion: int,
    alma: int,
    perfil_psicologico: str | None,
    rng: random.Random,
) -> str:
    impacto, accion = _numerology_profile_phrase(rng, camino_vida, expresion, alma, perfil_psicologico)
    sonido = _sound_symbolic_read(analysis.primary)
    perfil_hint = _perfil_psicologico_hint(perfil_psicologico)
    impacto_txt = f"{impacto} {perfil_hint}".strip()
    rare_open = rng.choice(
        (
            f"<b>Origen real.</b> <i>{analysis.primary}</i> llega como nombre que el tiempo no encerró en un solo libro: "
            "no es ausencia de historia, es historia demasiado viva para que un manual la domesticara.",
            f"<b>Origen real.</b> <i>{analysis.primary}</i> trae un halo de misterio honesto: su filiación exacta no está sellada en fuentes comunes, "
            "y eso te coloca en un lugar raro —te leen primero por presencia, después por dato.",
            f"<b>Origen real.</b> Tu nombre (<i>{analysis.primary}</i>) se sostiene más en memoria humana que en archivo cerrado: "
            "como una melodía que el linaje y el uso fueron tejiendo sin pedir permiso al diccionario.",
        )
    )
    rare_meaning = rng.choice(
        (
            "<b>Significado claro.</b> Aquí el sentido no se prueba con papel: se prueba en el cuerpo cuando lo pronuncian, "
            "en la pausa que dejan los demás y en el espacio que ocupa tu nombre cuando entra en una habitación.",
            "<b>Significado claro.</b> Lo que no está escrito en filología aparece escrito en vínculo: cómo te recuerdan, cómo te buscan y qué tono usan cuando te nombran.",
            "<b>Significado claro.</b> El misterio no vacía el nombre: lo llena de responsabilidad poética —vos elegís qué historia le das con el uso diario.",
        )
    )
    lived = _rare_name_lived_experience(rng, analysis.primary, nombre_completo)
    return (
        f"{rare_open}"
        f"<br/><br/>"
        f"{rare_meaning}"
        f"<br/><br/>"
        f"<b>Traducción a la vida real.</b> {sonido} {lived}"
        f"<br/><br/>"
        f"<b>Impacto emocional.</b> {impacto_txt}"
        f"<br/><br/>"
        f"<b>Acción concreta.</b> {accion}"
    )


def _compose_compound_name_block(
    analysis: NameAnalysis,
    nombre_completo: str,
    camino_vida: int,
    expresion: int,
    alma: int,
    perfil_psicologico: str | None,
    rng: random.Random,
) -> str:
    impacto, accion = _numerology_profile_phrase(rng, camino_vida, expresion, alma, perfil_psicologico)
    perfil_hint = _perfil_psicologico_hint(perfil_psicologico)
    impacto_txt = f"{impacto} {perfil_hint}".strip()
    primary_desc: str
    if analysis.known_primary is not None:
        primary_desc = (
            f"El nombre principal (<i>{analysis.primary}</i>) sostiene tu identidad base y aporta el eje de {analysis.known_primary.historical_meaning.lower().rstrip('.')}"
        )
    else:
        primary_desc = (
            f"El nombre principal (<i>{analysis.primary}</i>) sostiene tu identidad base y te posiciona como una persona de marca personal fuerte."
        )
    sec_lines: list[str] = []
    for idx, part in enumerate(analysis.secondary_parts):
        known = analysis.known_secondary[idx] if idx < len(analysis.known_secondary) else None
        if known is not None:
            sec_lines.append(
                f"<i>{part}</i> aporta memoria familiar o espiritual con el sentido de {known.historical_meaning.lower().rstrip('.')}"
            )
        else:
            sec_lines.append(
                f"<i>{part}</i> funciona como capa de tradición y pertenencia: memoria de casa y sangre que habla antes que el papel"
            )
    secondary_desc = "; ".join(sec_lines)
    tension = rng.choice(
        (
            f"En {nombre_completo}, la tensión viva es interna: una parte empuja identidad propia y otra honra lo recibido, y eso se nota en decisiones grandes.",
            f"En {nombre_completo}, la combinación se traduce en doble pertenencia: familia, historia y un nombre propio que quiere dirección propia.",
            f"En {nombre_completo}, no es 'dos nombres': es un solo contrato emocional con dos palancas: identidad personal y memoria familiar.",
        )
    )
    return (
        f"<b>Origen real.</b> Tu nombre funciona como nombre compuesto: combina {1 + len(analysis.secondary_parts)} componentes con funciones distintas."
        f"<br/><br/>"
        f"<b>Significado claro.</b> {primary_desc}. {secondary_desc}."
        f"<br/><br/>"
        f"<b>Traducción a la vida real.</b> {tension}"
        f"<br/><br/>"
        f"<b>Impacto emocional.</b> {impacto_txt}"
        f"<br/><br/>"
        f"<b>Acción concreta.</b> {accion}"
    )


def _fallback_surname(token: str) -> SurnameOrigin:
    canonical = _titlecase(token)
    t = _normalize_token(token)
    if t.endswith("ez"):
        typ = "linaje de pertenencia fuerte"
        note = (
            "Este apellido suele sentirse como mandato de continuidad: cuidar el nombre de la casa y sostener presencia en momentos de presión."
        )
        heraldic = (
            "En lectura simbólica, pide honrar raíces sin convertir lealtad familiar en autosacrificio."
        )
    elif t.endswith("es"):
        typ = "linaje de memoria activa"
        note = (
            "Este apellido suele traer memoria de origen y pertenencia, con una mezcla de orgullo familiar y necesidad de identidad propia."
        )
        heraldic = "Su clave emocional es equilibrar pertenencia con libertad personal."
    else:
        typ = "linaje de territorio emocional"
        note = (
            "Este apellido se vive como herencia de esfuerzo acumulado: una historia que pide ser honrada con límites sanos."
        )
        heraldic = (
            "Su potencia no está en la etiqueta social, sino en la capacidad de transformar memoria heredada en dirección consciente."
        )
    return SurnameOrigin(
        canonical=canonical,
        origin_type=typ,
        source_region="hispánico de tradición familiar",
        historical_note=note,
        heraldic_force=heraldic,
    )


def resolve_name_etymology(nombre_pila: str) -> NameEtymology:
    analysis = _analyze_name(nombre_pila)
    if analysis.known_primary is not None:
        return analysis.known_primary
    return NameEtymology(
        canonical=_titlecase(analysis.primary),
        root_language="lenguaje vivo, más allá de un solo archivo",
        etymon="raíz que el tiempo guardó en el uso, no en una sola página",
        historical_meaning=(
            "Nombre de identidad singular: su fuerza no está en una traducción única, sino en cómo te habita la gente que te ama y el mundo que te nombra."
        ),
        cultural_path=(
            "Su presencia se transmite en familia, en acento, en apodo y en el silencio cómodo cuando alguien te dice bien tu nombre."
        ),
        symbolic_evolution=_sound_symbolic_read(analysis.primary),
    )


def resolve_surnames(apellidos: str) -> list[SurnameOrigin]:
    tokens = [t for t in (apellidos or "").split() if t.strip()]
    out: list[SurnameOrigin] = []
    for token in tokens[:2]:
        key = _normalize_token(token)
        out.append(_SURNAME_DB.get(key, _fallback_surname(token)))
    return out


def compose_name_identity_blocks(
    nombre_completo: str,
    nombre_pila: str,
    apellidos: str,
    *,
    camino_vida: int,
    expresion: int,
    alma: int,
    perfil_psicologico: str | None = None,
    rng: random.Random | None = None,
) -> tuple[str, str]:
    """
    Devuelve 2 bloques:
    - Bloque A: historia filológica del nombre + cruce psicológico.
    - Bloque B: legado de apellidos con lectura heráldica y vínculo con el nombre.
    """
    analysis = _analyze_name(nombre_pila)
    r = rng if rng is not None else random.Random(hash(nombre_completo.strip().lower()) & 0xFFFFFFFF)
    surnames = resolve_surnames(apellidos)
    apellido_lineas: list[str] = []
    for s in surnames:
        origen_emocional = _symbolic_origin_label(s.origin_type)
        apellido_lineas.append(
            f"<b>{s.canonical}</b> · {origen_emocional}. {s.historical_note} "
            f"Clave simbólica en tu vida: {s.heraldic_force}"
        )
    if not apellido_lineas:
        apellido_lineas.append(
            "Tu apellido conserva memoria de pertenencia, responsabilidad y reputación heredada."
        )

    if analysis.kind == "compuesto":
        bloque_nombre = _compose_compound_name_block(
            analysis, nombre_completo, camino_vida, expresion, alma, perfil_psicologico, r
        )
    elif analysis.kind == "conocido":
        bloque_nombre = _compose_known_name_block(
            analysis, nombre_completo, camino_vida, expresion, alma, perfil_psicologico, r
        )
    else:
        bloque_nombre = _compose_rare_name_block(
            analysis, nombre_completo, camino_vida, expresion, alma, perfil_psicologico, r
        )
    ap_cierre = r.choice(
        (
            f"{nombre_completo}: tu apellido es un testamento que todavía late; no se trata de ser fiel al dolor heredado, sino de no traicionarte por no romper tabúes.",
            f"Cargar {nombre_completo} es cargar historia viva: el apellido no pide perfección, pide que elijas qué honor sostiene tu cuerpo hoy y qué peso devuelves sin culpa.",
            f"En {nombre_completo}, el linaje te dio piel para el mundo: si lo confundes con deuda eterna, el amor se vuelve rendición; si lo honras con límites, se vuelve raíz.",
            f"{nombre_completo} no es solo firma en un papel: es eco de quienes caminaron antes; la pregunta adulta no es si mereces el legado, sino cuánto de él habitas con libertad.",
        )
    )
    bloque_apellido = "<b>Legado del apellido en tu vida actual.</b> " + " ".join(apellido_lineas) + "<br/><br/>" + ap_cierre
    return bloque_nombre, bloque_apellido
