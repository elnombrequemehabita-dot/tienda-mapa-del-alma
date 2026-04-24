"""
Mapa del Alma — narrative_banks_v15 (única fuente de verdad V15).
Mitología planetaria, sombras por elemento, portada y compositores de las 15 secciones.
"""
from __future__ import annotations

import random
import re

from logic import SoulProfile
from onomastica import compose_name_identity_blocks


def _pick(rng: random.Random, options: tuple[str, ...]) -> str:
    return rng.choice(options)


def _br(*parts: str) -> str:
    """Separa párrafos para ReportLab (bloques con <br/><br/>)."""
    return "<br/><br/>".join(s.strip() for s in parts if s and s.strip())


def _lector_momento_wow(rng: random.Random, slot: str) -> str:
    """Frase de reconocimiento fuerte; pools separados por sección para no chocar en validación cruzada del libro."""
    planeta = (
        "<b>Lo que no decís en voz alta.</b> La frase que te guardás es la que más ordena tu día.",
        "<b>Aquí es donde te perdés sin darte cuenta.</b> No es la decisión épica: es el hábito pequeño que repetís como si fuera neutral.",
        "<b>Tu patrón real no es el que mostrás.</b> Es el que sostenés cuando creés que nadie está mirando… y después negás en silencio.",
        "<b>Esto es lo que otros leen en vos antes de que hables.</b> No es verdad total: es frecuencia; y te condiciona igual.",
    )
    gema = (
        "<b>Lo que el cuerpo ya sabe.</b> Antes de la explicación elegante, aparece un nudo, un sueño raro, un apetito que cambia: señal honesta.",
        "<b>El atajo que no es atajo.</b> Cuando evitás sentir, comprás paz con plazos: después cobra con cansancio o con un estallido chico.",
        "<b>La vergüenza que no nombraste.</b> No es el error: es la historia que te contaste sobre vos para no ocupar espacio.",
        "<b>Lo que repetís “sin querer”.</b> Eso no es casualidad: es acuerdo silencioso con vos para no arriesgar el corazón.",
    )
    hilo = (
        "<b>La contradicción que te cansa.</b> Querés dos cosas a la vez y el mundo te pide una sola respuesta; el cuerpo paga la diferencia.",
        "<b>El truco que te funciona… hasta que no.</b> Lo que te salvó de chica o chico hoy te cobra en vínculo, sueño o paciencia.",
        "<b>Lo que nadie te devuelve.</b> Si siempre traducís el grupo, alguien tiene que traducerte a vos: si no, se apaga la brújula.",
        "<b>El precio invisible.</b> Cada “estoy bien” que no lo sentís deja intereses: después explotan en algo que “no venía al caso”.",
    )
    pools = {"planeta": planeta, "gema": gema, "hilo": hilo}
    return _pick(rng, pools[slot])


def compose_cover_tagline(
    rng: random.Random, p: SoulProfile, sign: str, elem: str, nacimiento: str
) -> str:
    hooks = (
        "No es un título bonito: es un espejo.",
        "No es decoración: es contrato contigo.",
        "No es promesa vacía: es memoria futura escrita con tu nombre.",
        "No es tendencia: es archivo emocional con tu firma.",
        "No es adorno: es evidencia de que alguien te tomó en serio.",
    )
    mids = (
        "Carta interior nacida un {wd} {nac}, bajo la luz de {sign}, sostenida por el elemento {elem}.",
        "Lectura tejida un {wd} {nac}: {sign} en el gesto, {elem} en la textura.",
        "Este mapa respira un {wd} {nac}; {sign} marca el gesto y {elem} el modo en que lo encarnas.",
        "Nacida la lectura un {wd} {nac}, con {sign} como firma solar y {elem} como temperatura.",
        "Un {wd} {nac} abre el relato: {sign} en la luz, {elem} en la forma de sostenerla.",
    )
    ends = (
        "Estable como tu firma, íntima como un secreto que eliges honrar.",
        "Irrepetible como tu historia, honesta como tu silencio cuando callas con propósito.",
        "Única como tu combinación de cielo y cuerpo.",
        "Coherente con lo que ya intuías y no te atrevías a nombrar.",
        "Hecha para ser tuya, no para ser genérica.",
    )
    mid = _pick(rng, mids).format(
        wd=p.weekday_es, nac=nacimiento, sign=sign, elem=elem
    )
    return f"{_pick(rng, hooks)} {mid} {_pick(rng, ends)}"


def compose_impact_lines(rng: random.Random, nombre: str) -> tuple[str, str]:
    """Frases de impacto (página sin caja) — tono distinto por sorteo para no sonar genérico."""
    a = (
        f"<i>{nombre}</i>: no viniste a repetir el mismo silencio.",
        "Tu cuerpo ya sabe lo que tu mente aún negocia.",
        "Lo que no te nombran no te libera.",
        "No eres fondo: eres figura, aunque te enseñaron a hacerte pequeña o pequeño.",
        "El mapa no adivina: recuerda lo que el ruido te quitó.",
        "Aquí no hay promesa vacía: hay evidencia que puedes sentir.",
    )
    b = (
        "Lo sagrado no grita: late en lo cotidiano.",
        "La coherencia es una forma de amor que no necesita aplauso.",
        "No es decoración: es contrato suave con tu sistema nervioso.",
        "Tu historia no es lineal: es constelación.",
        "Cierra los ojos un segundo: el nombre correcto vibra distinto.",
        "Irrepetible no es ego: es precisión.",
    )
    return _pick(rng, a), _pick(rng, b)


def compose_chino(rng: random.Random, p: SoulProfile, animal: str) -> str:
    s = (
        "El zodiaco oriental no contradice tu carta occidental: amplía el tiempo como ciclo, no como línea recta.",
        "El año del {an} no borra tu Sol: le agrega memoria colectiva y ritmo de supervivencia elegante.",
        "Lo oriental aquí no es turismo simbólico: es otra capa de temple aplicada a tu año de nacimiento.",
        "El {an} no te encasilla: te sitúa en un clima que convive con tu carta.",
        "Leer el {an} es leer una paciencia o audacia que ya estaba en tu historia.",
    )
    origen = (
        _pick(rng, s).format(an=animal)
        + " Origen: el zodiaco oriental añade memoria de ciclos largos a tu carta occidental; no te contradice, te ensancha el tiempo."
    )
    presente = _pick(
        rng,
        (
            "Tu nombre nació en un año con clima propio: eso sigue coloreando decisiones que hoy crees solo tuyas.",
            "Nada de esto te quita agencia: te da contexto para dejar de culparte con la historia equivocada.",
            "La raíz oriental no es excusa: es explicación compasiva.",
            "Si te sientes “demasiado” o “poco”, el {an} recuerda que los ciclos existen.",
            "El {an} no manda: sugiere un estilo de paciencia o astucia.",
        ),
    ).format(an=animal)
    futuro = (
        "Potencial futuro: cruza el {an} con tu camino {cv} y tu expresión {ex}. "
        "Ahí aparece una lectura que no es genérica: es el estilo exacto con el que tu cuerpo aprende a sostener promesas sin traicionarse."
    ).format(an=animal, cv=p.camino_vida, ex=p.expresion)
    return _br(origen, presente, futuro)


def compose_mision(rng: random.Random, p: SoulProfile, nombre: str, sign: str, elem: str) -> str:
    m = (
        "La misión del alma, sin endulzar, es esta: que lo que te rompió no te defina por rencor, sino por lucidez.",
        "Tu misión no es brillar para todos: es dejar de traicionarte cuando el miedo aprieta.",
        "El propósito real no es un escenario épico: es integridad en lo cotidiano.",
        "La misión no es salvar al mundo: es no abandonarte cuando alguien más tiene miedo.",
        "Si hay misión, es humana: carne, límites, abrazos, facturas.",
    )
    n = (
        "{nom}, tu propósito aparece cuando integras {sign} con el {cv} de tu camino y el {elem} como ética de trabajo en el mundo real.",
        "{nom}: {sign} pide un gesto, el {cv} pide un arco y el {elem} pide una forma honesta de ejecutarlo.",
        "Con {sign} y camino {cv}, tu misión no es fantasía: es práctica nerviosa con alma.",
        "{nom}, el {cv} te recuerda el tempo; {sign} y {elem} te recuerdan el estilo.",
        "Integrar {sign}, {cv} y {elem} es dejar de pedir permiso para ocupar tu vida.",
    )
    origen = _pick(rng, m) + " Origen: la misión no llegó de un folleto; llegó de lo que ya resististe con nombre propio."
    presente = _pick(rng, n).format(nom=nombre, sign=sign, cv=p.camino_vida, elem=elem)
    futuro = (
        "Potencial futuro: {nom}, cuando integres {sign}, el {cv} y el {elem} sin pedir permiso para ocupar tu vida, "
        "la misión deja de ser frase bonita y se vuelve hábito: pequeño, repetible, verdadero."
    ).format(nom=nombre, sign=sign, cv=p.camino_vida, elem=elem)
    return _br(origen, presente, futuro)


def compose_numerologia(rng: random.Random, p: SoulProfile) -> str:
    r = (
        "La numerología sagrada te pide leer cifras como psique, no como superstición.",
        "Tus números no son amuleto: son descripciones de ritmo interno.",
        "Numerología útil es la que te devuelve palabras para lo que ya sentías.",
        "Aquí las cifras no compiten: se cruzan como voces en una misma habitación.",
        "Si separas los números, te pierdes el retrato: juntos son una sola melodía.",
    )
    s = (
        "El {cv} narra el arco largo; el {ex} narra el timbre con el que nombras lo que sientes; el {al} susurra lo que necesitas recibir; el {pe} es la puerta pública.",
        "Camino {cv}, expresión {ex}, alma {al} y personalidad {pe} no son cuatro vidas: son cuatro micrófonos del mismo ser.",
        "El {cv} pide sentido; el {ex} pide palabra; el {al} pide nutrición simbólica; el {pe} pide coherencia visible.",
        "Leer {cv} sin {ex} es leer solo mitad del clima interno.",
        "La combinación {cv}-{ex}-{al}-{pe} es casi imposible de copiar: por eso este texto no es plantilla.",
    )
    origen = _pick(rng, r) + " Origen: las cifras son lenguaje antiguo para describir ritmos internos que ya sentías pero no nombrabas."
    presente = _pick(rng, s).format(
        cv=p.camino_vida,
        ex=p.expresion,
        al=p.alma,
        pe=p.personalidad,
    )
    futuro = (
        "Potencial futuro: cruza el camino {cv} con tu signo y tu año del {an} para dejar de leerte como error. "
        "La numerología aquí no predice: te devuelve palanca para elegir con menos vergüenza ajena y más verdad propia."
    ).format(cv=p.camino_vida, an=p.animal_chino)
    return _br(origen, presente, futuro)


def compose_sentir(
    rng: random.Random,
    p: SoulProfile,
    sign: str,
    elem: str,
    planet: str,
    *,
    nombre_pila: str = "",
    apellidos: str = "",
) -> str:
    np = (nombre_pila or "").strip()
    ap = (apellidos or "").strip()
    capa_nom = ""
    if np or ap:
        nom_ap = (
            "En vínculos, no solo importa cómo te sentís: importa cómo te nombran. "
            "<i>{np}</i> es tu entrada emocional; {ap_txt} es el contexto ancestral que modula confianza y miedo.",
            "Tu forma de amar está tejida con <i>{np}</i>: la sílaba con la que pedís cuidado. "
            "{ap_frag}",
            "Cuando alguien pronuncia bien tu nombre, sana algo antiguo. "
            "Cuando lo distorsionan, no es drama: es linaje y dignidad pidiendo fronteras. <i>{np}</i> {ap_frag2}",
        )
        ap_txt = f"<i>{ap}</i>" if ap else "tu linaje (aún sin apellido escrito)"
        ap_frag = (
            f"El apellido <i>{ap}</i> enseña lealtades y límites heredados."
            if ap
            else "Tu linaje, aunque no esté escrito aquí, modula cómo confiás."
        )
        ap_frag2 = (
            f"y <i>{ap}</i> recuerdan que el amor también es responsabilidad con la historia."
            if ap
            else "y tu historia recuerdan que el amor también es responsabilidad."
        )
        capa_nom = _pick(rng, nom_ap).format(np=np or "tu nombre", ap_txt=ap_txt, ap_frag=ap_frag, ap_frag2=ap_frag2)
        capa_nom += " "

    t = (
        "Tu forma de sentir está tejida con {elem}, con el temperamento de {sign} y con la inteligencia {en} que aprendió a nombrarse tarde, pero bien.",
        "Sientes a través de {elem}, piensas el vínculo con el filtro de {sign} y sostienes el ritmo con energía {en}.",
        "{elem} da el canal; {sign} da el estilo; la energía {en} da la velocidad emocional.",
        "No eres “demasiado sensible”: eres {sign} en {elem} con una energía {en} que pide respeto, no simplificación.",
        "En vínculos, {sign} y {elem} explican tu umbral; {en} explica cómo lo atravesás.",
    )
    u = (
        "No buscas perfección de manual: buscas reciprocidad que no te haga pedir disculpas por existir.",
        "Tu vínculo sano no es ausencia de fricción: es presencia de verdad.",
        "Cuando te traicionan, duele el doble porque tu sistema ya midió el riesgo con cuerpo.",
        "Cuando alguien se queda con la verdad incómoda, sanas entera.",
        "Tu corazón no es ingenuo: es laboratorio.",
    )
    v = (
        "Ahí {pl} enseña límites hermosos y ternura firme, sin humo.",
        "{pl} aparece como maestro de límites cuando el amor confunde entrega con abandono.",
        "Con {pl} en la ecuación, el amor no es anestesia: es elección consciente.",
        "{pl} te recuerda que el vínculo también es práctica, no solo sentimiento.",
        "Incluso en el amor, {pl} pide coherencia: no performance.",
    )
    origen = (
        capa_nom
        + _pick(rng, t).format(elem=elem, sign=sign, en=p.energia)
        + " Origen: tu forma de sentir tiene raíz en el elemento y en el gesto solar que aprendiste temprano."
    )
    presente = _pick(rng, u) + " " + _pick(rng, v).format(pl=planet)
    futuro = (
        "Potencial futuro: permitir que {elem}, {sign} y {pl} co-educhen tu vínculo sin que el miedo sea director de escena. "
        "No se trata de ser perfecta o perfecto: se trata de ser veraz sin humillar al corazón."
    ).format(elem=elem, sign=sign, pl=planet)
    return _br(origen, presente, futuro)


def compose_sombra(rng: random.Random, p: SoulProfile, sign: str, elem: str, shadow_frag: str) -> str:
    a = (
        "Tu poder no es volumen: es precisión emocional.",
        "Tu fuerza no es ruido: es exactitud afectiva.",
        "Tu potencia no es dominar escenarios: es sostener contradicciones sin humillar a nadie, empezando por ti.",
        "Tu poder adulto es nombrear la contradicción sin dramatizarla para manipular.",
        "Tu fuerza crece cuando admites miedo sin convertirlo en espectáculo.",
    )
    b = (
        "La sombra sagrada no es enemiga: es la parte que aún no recibió lenguaje amable.",
        "La sombra es información que todavía no tradujiste: no es maldición.",
        "Nombrar sombra no te ensucia: te devuelve credibilidad.",
        "La sombra grita con hábitos cuando el cuerpo ya no aguanta el guion de “todo bien”.",
        "Integrar sombra es dejar de pelear contra ti como si fueras el error.",
    )
    c = (
        "Cuando {sign} se agota, puede volverse terco; cuando {elem} se desborda, puede querer controlar lo incontrolable.",
        "El cansancio de {sign} se nota en terchez; el desborde de {elem} se nota en control.",
        "{sign} y {elem} explican tu estilo de defensa: nombrarlos te devuelve palanca.",
        "Si ignoras {sign} y {elem}, la sombra gana por omisión.",
        "La sombra de {sign} en {elem} pide ternura, no castigo.",
    )
    d = (
        "La gente confía en quien admite miedos sin victimizarse para manipular.",
        "Credibilidad nace de honestidad nerviosa, no de discurso inspirador de domingo.",
        "Esto no es autoayuda: es psicología con respeto.",
        "Si te incomoda, es porque toca verdad: eso es el precio de la lucidez.",
        "Nombrar debilidad con ternura es un acto de poder.",
    )
    origen = _pick(rng, a) + " Origen: el poder y la sombra comparten archivo; uno es luz con nombre, el otro es luz mal traducida."
    presente = shadow_frag + " " + _pick(rng, b) + " " + _pick(rng, c).format(sign=sign, elem=elem)
    futuro = (
        _pick(rng, d)
        + " Potencial futuro: llevar el poder sin performance y la sombra sin castigo, hasta que tu vulnerabilidad deje de ser moneda de manipulación."
    )
    return _br(origen, presente, futuro)


def compose_hilo(
    rng: random.Random,
    p: SoulProfile,
    sign: str,
    totem_hint: str,
    *,
    nombre_pila: str = "",
    apellidos: str = "",
    nombre_completo: str = "",
) -> str:
    np = (nombre_pila or "").strip()
    ap = (apellidos or "").strip()
    nc = (nombre_completo or p.nombre or "").strip()

    hilo_nombre = (
        "El hilo maestro empieza antes del cielo: empieza en <i>{np}</i> y en el linaje que pronunciás cuando firmás "
        "con tu nombre completo. Sin esa firma humana, los astros quedan bonitos pero lejanos.",
        "Aquí el cielo no compite con tu historia: la conversa. <i>{np}</i> es la puerta; el linaje {lin} es el pasillo "
        "por el que entra la memoria.",
        "No es magia escapar del nombre: la carta se lee mejor cuando entendés que <i>{nc}</i> es un código vivo, "
        "no un dato administrativo.",
        "Si ignorás cómo te llaman, los números se vuelven fríos. Si honrás <i>{np}</i>, los números recuperan pulso.",
        "Tu identidad no es un sticker: es una melodía donde <i>{np}</i> {lin2} y el cielo aporta el tempo.",
    )
    lin = f"(<i>{ap}</i>)" if ap else "(aún en silencio, pero presente)"
    lin2 = f"y <i>{ap}</i> entonan" if ap else "y tu historia entonan"

    apertura = ""
    if np:
        apertura = (
            _pick(rng, hilo_nombre).format(np=np, lin=lin, lin2=lin2, nc=nc)
            + " "
        )

    h = (
        "Esta es la sección maestra: el hilo invisible que une lo que parecían datos sueltos.",
        "Aquí no hay piezas sueltas: hay un cable conductor entre cielo, número e instinto.",
        "Si ves el hilo, dejas de leerte como lista: te lees como sinfonía.",
        "El hilo invisible es la narrativa que une carta, cifra y cuerpo.",
        "Sin este hilo, los símbolos compiten; con él, conversan.",
    )
    i = (
        "{sign} no es una etiqueta aparte de tu número {cv}: es el gesto existencial con el que tu vida aprende a repetir y variar ese tempo.",
        "Tu {sign} se cruza con el camino {cv}: el gesto y el arco no son dos vidas, son una.",
        "Leer {sign} sin {cv} es leer apellido sin nombre propio.",
        "El {cv} da el tempo; {sign} da la melodía emocional.",
        "La ecuación {sign} + {cv} evita que te interpretes como accidente.",
    )
    j = (
        "El tótem ({tot}) no compite con tu carta: le da cuerpo e instinto al arco que tus cifras describen en abstracto.",
        "El tótem ({tot}) traduce lo numérico a piel: instinto, hambre, defensa noble.",
        "Sin el tótem ({tot}), el número queda frío; con él, respira.",
        "El tótem ({tot}) es la imagen animal que tu sistema reconoce antes que el discurso.",
        "En {tot} está el gesto primario que el número ordena.",
    )
    k = (
        "Cuando ves el hilo, dejas de culparte como error: empiezas a afinar con precisión.",
        "Ver el hilo no te salva: te alinea.",
        "El hilo no es misticismo vacío: es coherencia entre datos y carne.",
        "Unir signo, número y tótem es dejar de sentirte fragmentada o fragmentado.",
        "Este hilo es el antídoto contra la sensación de estar mal “sin razón”.",
    )
    origen = (
        apertura
        + _pick(rng, h)
        + " Origen: el hilo nace cuando dejas de ver datos aislados y empiezas a oír conversación entre ellos."
    )
    presente = (
        _pick(rng, i).format(sign=sign, cv=p.camino_vida)
        + " "
        + _pick(rng, j).format(tot=totem_hint)
    )
    futuro = (
        _pick(rng, k)
        + " Potencial futuro: cruza {sign}, el camino {cv}, el tótem y el año del {an} como una sola melodía. "
        "Ahí deja de doler la sensación de estar “partida” o “partido”: lo que queda es afinación."
    ).format(sign=sign, cv=p.camino_vida, an=p.animal_chino)
    return _br(origen, presente, futuro)


def compose_mensaje(rng: random.Random, nombre: str) -> str:
    a = (
        f"{nombre}, este es el momento más íntimo y fuerte del libro: nadie puede leerlo por ti.",
        f"{nombre}, si algo aquí te partió al medio, probablemente sea porque te nombró bien.",
        f"{nombre}, lo que duele en esta página no es crueldad: es precisión.",
        f"{nombre}, nadie puede hacer este tramo por ti: es de piel.",
        f"{nombre}, cerrar esto con dignidad es un acto de valentía.",
    )
    b = (
        "Lo que llamas error, muchas veces es entrenamiento disfrazado.",
        "Lo que llamas fracaso a veces es límite sano apareciendo tarde.",
        "Lo que llamas tardanza, a veces es maduración que no se apura por aplausos.",
        "Lo que llamas debilidad a veces es sensibilidad sin apoyo.",
        "Lo que llamas caos a veces es reorganización silenciosa.",
    )
    c = (
        "El cielo que te tocó no es sentencia: es idioma.",
        "Tu carta no te encadena: te enseña a leerte.",
        "El destino, aquí, no es jaula: es vocabulario.",
        "Lo que te tocó no te absuelve: te invita a elegir con nombre propio.",
        "Tu historia no es castigo: es material para lucidez.",
    )
    origen = _pick(rng, a) + " Origen: este mensaje no busca aplauso; busca ubicarte donde el silencio deja de ser refugio y pasa a ser verdad."
    presente = _pick(rng, b) + " Impacto presente: lo que te duele aquí es precisión, no crueldad."
    futuro = _pick(rng, c) + " Potencial futuro: cerrar el libro con la dignidad de quien ya no necesita mentirse para sostenerse."
    return _br(origen, presente, futuro)


def compose_oraculo(rng: random.Random) -> str:
    o = _pick(
        rng,
        (
            "El oráculo de esta carta no promete un universo sin fricción: promete claridad para caminar con fricción sin perder alma.",
            "Este oráculo no es promesa mágica: es luz para no confundir dolor con derrota.",
            "El oráculo aquí es sobrio: te devuelve el piso cuando el romanticismo espiritual te lo quita.",
            "No es predicción: es permiso para integrar lo humano sin vergüenza.",
            "El oráculo te recuerda que lo sagrado también es simple.",
        ),
    )
    p = _pick(
        rng,
        (
            "Lo sagrado también es simple: agua, sueño, pan, abrazo, verdad dicha sin crueldad.",
            "Lo sagrado baja a taza de té, a mensaje honesto, a límites dichos con amor.",
            "Lo sagrado no siempre truena: a veces susurra en lo cotidiano.",
            "Lo sagrado es frecuente: lo raro es permitirte recibirlo.",
            "Lo sagrado no te pide huir del mundo: te pide bajar el mundo a tamaño de corazón.",
        ),
    )
    f = _pick(
        rng,
        (
            "Cierra con tres afirmaciones que no son fantasía: son instrucciones nerviosas para volver a casa en ti.",
            "Las afirmaciones que siguen no son espejismo: son contratos suaves con tu sistema nervioso.",
            "Tres líneas para cerrar: no son magia, son dirección.",
            "Tres frases para llevar: no reemplazan terapia, pero ordenan el día.",
            "Tres afirmaciones: una para el cuerpo, una para el vínculo, una para el sentido.",
        ),
    )
    return _br(o, p, f)


def compose_affirmations(
    rng: random.Random,
    p: SoulProfile,
    nombre: str,
    sign: str,
    elem: str,
    *,
    nombre_pila: str = "",
    apellidos: str = "",
) -> tuple[str, str, str]:
    np = (nombre_pila or "").strip()
    ap = (apellidos or "").strip()
    if np and ap:
        pool1 = (
            f"Yo, {nombre}, honro <i>{np}</i> y el linaje de <i>{ap}</i>: llevo esta historia con lucidez, no con culpa heredada sin nombre.",
            f"Yo, {nombre}, mi nombre <i>{np}</i> y mis apellidos <i>{ap}</i> son sagrados: no son escudo de ego, son responsabilidad amorosa.",
            f"Yo, {nombre}, elijo que cada vez que diga <i>{np}</i> sea un acto de presencia, y que <i>{ap}</i> me recuerde fuerza ancestral sin jaula.",
            f"Yo, {nombre}, integro <i>{np}</i> + <i>{ap}</i> como frecuencia única: no compito, me alineo con mi verdad.",
            f"Yo, {nombre}, dejo de avergonzar mi linaje ({ap}) y empiezo a honrarlo con límites sanos, empezando por cómo me llamo: <i>{np}</i>.",
        )
    elif np:
        pool1 = (
            f"Yo, {nombre}, honro el nombre <i>{np}</i> como primer altar: no es vanidad, es verdad encarnada.",
            f"Yo, {nombre}, permito que <i>{np}</i> sea hogar en mi boca antes que performance para otros.",
            f"Yo, {nombre}, elijo pronunciarme con respeto: <i>{np}</i> merece tono de ternura firme.",
            f"Yo, {nombre}, integro <i>{np}</i> con mi {elem}: una sola melodía, una sola responsabilidad.",
            f"Yo, {nombre}, dejo de traicionar <i>{np}</i> con culpa: es sagrado, no perfecto.",
        )
    else:
        pool1 = (
            f"Yo, {nombre}, honro el elemento {elem} y elijo que mi energía {p.energia} sea brújula, no prisión.",
            f"Yo, {nombre}, permito que {elem} me enseñe límites hermosos sin confundirlos con muros de miedo.",
            f"Yo, {nombre}, integro el {elem} como ética: lo que sostengo y lo que suelto con nombre.",
            f"Yo, {nombre}, elijo {elem} con dignidad: como forma de cuidado, no de castigo.",
            f"Yo, {nombre}, dejo de avergonzar mi {elem}: es parte de mi lenguaje interno.",
        )
    pool2 = (
        f"Yo, {nombre}, camino con el gesto de {sign} y el coraje de quien ya se leyó entera.",
        f"Yo, {nombre}, permito que {sign} sea verdad, no estampa que me aprieta.",
        f"Yo, {nombre}, honro {sign} sin usarlo como excusa ni como jaula.",
        f"Yo, {nombre}, elijo la lucidez de {sign} antes que la performance de “perfecta”.",
        f"Yo, {nombre}, llevo {sign} como pregunta viva, no como respuesta cerrada.",
    )
    pool3 = (
        f"Yo, {nombre}, uno mi camino {p.camino_vida} y mi expresión {p.expresion} en una sola verdad viva, hoy.",
        f"Yo, {nombre}, dejo de pelear contra el {p.camino_vida} y el {p.expresion}: los integro como mapa y voz.",
        f"Yo, {nombre}, elijo coherencia entre {p.camino_vida} y {p.expresion}: un arco y un timbre alineados.",
        f"Yo, {nombre}, mi {p.camino_vida} y mi {p.expresion} co-crean mi día con responsabilidad amorosa.",
        f"Yo, {nombre}, permito que {p.camino_vida} y {p.expresion} conversen sin anularse.",
    )
    return _pick(rng, pool1), _pick(rng, pool2), _pick(rng, pool3)


def compose_back_cover(
    rng: random.Random, p: SoulProfile, nombre: str, sign: str, planet: str, animal: str, nacimiento: str
) -> str:
    x = (
        "Este mapa nació para {nom}, tejido desde {nac}, con el {an} como memoria oriental, {sign} como firma solar y {pl} como voz de regencia.",
        "{nom}: {nac} queda como punto de partida; {an} como clima; {sign} y {pl} como brújula y timbre.",
        "Para {nom}, nacida/o en {nac}, el {an} susurra raíz mientras {sign} y {pl} marcan gesto y consecuencia.",
        "Este cierre honra a {nom}: {nac}, {an}, {sign}, {pl} — una sola vida, muchas capas.",
        "{nom} cierra el mapa con {sign} y {pl} en la mesa, y el {an} como memoria que no compite, completa.",
    )
    y = (
        "Llévalo como espejo, no como cadena: la carta más verdadera es la que te devuelve dignidad.",
        "No lo uses para justificar crueldad: úsalo para precisión compasiva.",
        "No es sentencia: es lenguaje para volver a casa en ti.",
        "No es promesa de perfección: es permiso para integrarte.",
        "No es adorno: es herramienta para nombrarte con respeto.",
    )
    z = (
        "Al cerrar, el universo deja una firma irrepetible: no es decoración, es sello.",
        "El sello final no es teatro: es frecuencia propia, escrita en tu combinación exacta.",
        "Cerrar con sello es recordarte que no eres reemplazable en tu propia lectura.",
        "La firma cierra el círculo: lo que empezó con tu nombre termina con evidencia.",
        "Este cierre es lujo porque es tuyo: no hay copia.",
    )
    origen = _pick(rng, x).format(nom=nombre, nac=nacimiento, an=animal, sign=sign, pl=planet)
    presente = _pick(rng, y)
    futuro = _pick(rng, z) + " Potencial futuro: volver a este mapa cuando el ruido externo te haga olvidar tu propia frecuencia."
    return _br(origen, presente, futuro)


# --- Mitos / sombras por elemento (pools de apoyo) ---

PLANET_MYTH: dict[str, tuple[str, ...]] = {
    "sol": (
        "El Sol pide congruencia: brilla lo que defiendes con el pecho abierto.",
        "Regencia solar: visibilidad interior, no fama vacía.",
        "El Sol enseña presencia sin performance eterna.",
        "Tu Sol pide honor a lo que eliges mostrar.",
        "Luz que no pide permiso: responsabilidad con lo que encendés.",
    ),
    "luna": (
        "La Luna enseña memoria y refugio emocional.",
        "Mundo lunar: información que aún no nombraste.",
        "La Luna traduce silencios ajenos en tu cuerpo.",
        "Ritmo y marea: lo que sientes antes que lo expliquen.",
        "Luna: cuidado como práctica, no como discurso.",
    ),
    "mercurio": (
        "Mercurio es puente: palabras, ideas, contratos emocionales.",
        "Verdad mercurial: el nombre correcto en el momento correcto.",
        "Mercurio corre, sí, pero puede ordenar el caos si lo entrenás.",
        "Mensaje y mente: lo que nombras cambia lo que sientes.",
        "Mercurio enseña precisión sin crueldad.",
    ),
    "venus": (
        "Venus: ética del placer y valor de lo que amás.",
        "Amor venusiano: arte y acuerdo, no fuga.",
        "Venus pide belleza honesta, no máscara.",
        "Placer con límites: Venus enseña ternura firme.",
        "Venus no es superficialidad: es dignidad afectiva.",
    ),
    "marte": (
        "Marte enseña no sin romperse: coraje limpio.",
        "Furia santa: límite defendido sin humillar.",
        "Marte: impulso con honor, no con destrucción.",
        "Deseo sano: Marte pide cuerpo y verdad.",
        "Marte: peleas por lo que merece piel.",
    ),
    "jupiter": (
        "Júpiter amplía sentido: fe sin ingenuidad.",
        "Horizonte: Júpiter pide más de lo que te enseñaron a pedir.",
        "Expansión ética: Júpiter no es exceso vacío.",
        "Risa y sentido: Júpiter cura con perspectiva.",
        "Júpiter: generosidad de mirar más allá del miedo.",
    ),
    "saturno": (
        "Saturno: tiempo, forma, promesa cumplida.",
        "Madurez que duele porque te hace real.",
        "Disciplina como amor sin poesía barata.",
        "Saturno no castiga: estructura para lo sagrado.",
        "Límite noble: Saturno enseña responsabilidad hermosa.",
    ),
}

SHADOW_BY_ELEM: dict[str, tuple[str, ...]] = {
    "Fuego": (
        "El miedo oculto suele ser quedarte sin testigos de tu intensidad real.",
        "La debilidad tierna es confundir impulso con identidad.",
        "Temor a ser demasiado: entonces domesticas el fuego y te dueles.",
        "Miedo a la visibilidad: prefieres versión domesticada.",
        "Herida: correr para no sentir, pelear para no llorar.",
    ),
    "Tierra": (
        "El miedo oculto suele ser el vacío si sueltas el control.",
        "La debilidad tierna es cargar todo para no pedir.",
        "Temor a que sin vigilancia todo se derrumbe.",
        "Miedo a la improvisación: llamas control a la angustia.",
        "Herida: soledad disfrazada de fuerza.",
    ),
    "Aire": (
        "El miedo oculto suele ser quedarte sin palabras justas cuando más las necesitas.",
        "La debilidad tierna es analizar hasta el infinito para no sentir el golpe.",
        "Temor al silencio incómodo: llenas de palabras.",
        "Miedo a equivocarte en público: te congelas o sobreactúas.",
        "Herida: frialdad defensiva que confundes con lucidez.",
    ),
    "Agua": (
        "El miedo oculto suele ser fusionarte para no estar sola o solo.",
        "La debilidad tierna es confundir sensibilidad con deuda emocional.",
        "Temor al abandono: entonces negocias tu línea.",
        "Miedo a la soledad: pagas precios altos por compañía.",
        "Herida: amar como factura eterna.",
    ),
}


def pick_planet_myth(rng: random.Random, planet_key: str) -> str:
    opts = PLANET_MYTH.get(planet_key, ("Tu regente marca un timbre único de decisión.",))
    return _pick(rng, opts)


def pick_shadow(rng: random.Random, elem_label: str) -> str:
    opts = SHADOW_BY_ELEM.get(elem_label, SHADOW_BY_ELEM["Agua"])
    return _pick(rng, opts)

def _prim(p: SoulProfile) -> str:
    t = (p.nombre_pila or "").strip()
    return t if t else "vos"


def _ap_txt(apellidos: str) -> str:
    a = (apellidos or "").strip()
    return a if a else ""


def _perfil_slug(p: SoulProfile) -> str:
    return (getattr(p, "perfil_psicologico", "") or "").strip().lower()


def _perfil_lineas(perfil: str) -> dict[str, str]:
    pool: dict[str, dict[str, str]] = {
        "controlador": {
            "nombre": "Tu nombre se vive como mandato de orden: necesitas prever, organizar y sostener resultados.",
            "elemento": "Patrón del perfil: intentas controlar cada variable antes de actuar, y eso te agota.",
            "hilo": "En tu hilo central aparece la misma tensión: anticipas todo para evitar errores y terminas sobrecargando tu sistema.",
            "sombra": "Sombra del perfil: confundes control con seguridad y te cuesta delegar incluso cuando estás saturada o saturado.",
            "accion": "delega una tarea concreta hoy y no la recuperes por ansiedad de hacerlo mejor",
        },
        "sobreanalitico": {
            "nombre": "Tu nombre activa mente estratégica: observas todo, comparas opciones y postergas el salto.",
            "elemento": "Patrón del perfil: piensas tanto el escenario que pierdes el momento de actuar.",
            "hilo": "En tu hilo central se repite esto: acumulas opciones, dudas del momento exacto y atrasas decisiones valiosas.",
            "sombra": "Sombra del perfil: dudas hasta congelarte y luego te culpas por no haberte movido antes.",
            "accion": "decide con 70 por ciento de certeza y protege esa decisión por 72 horas",
        },
        "evitador_emocional": {
            "nombre": "Tu nombre se protege evitando roce: eliges distancia antes que fricción, aunque a veces pagues con tensión que no nombraste a tiempo.",
            "elemento": "Patrón del perfil: pospones el choque, suavizas la superficie y después te sorprende la intensidad con la que reacciona tu cuerpo.",
            "hilo": "En tu hilo central aparece un dilema adulto: cuánta verdad tolera el vínculo sin romperse, y cuánta incomodidad toleras tú sin traicionarte.",
            "sombra": "Sombra del perfil: confundes paz con evitación, y terminas pagando con distancia, resentimiento o explosiones que no te reconocen.",
            "accion": "en una conversación pendiente, di una verdad corta sin justificarte",
        },
        "impulsivo": {
            "nombre": "Tu nombre empuja intensidad de inicio: actúas primero y ordenas consecuencias después.",
            "elemento": "Patrón del perfil: decides rápido para recuperar control emocional, aunque luego tengas que corregir.",
            "hilo": "En tu hilo central aparece el mismo pulso: velocidad alta al decidir y desgaste posterior en correcciones.",
            "sombra": "Sombra del perfil: reaccionas por urgencia y eso te mete en conflictos evitables.",
            "accion": "antes de responder bajo presión, pausa 90 segundos y define objetivo en una frase",
        },
        "adaptador": {
            "nombre": "Tu nombre se orienta a pertenecer: lees al entorno y te ajustas para no generar rechazo.",
            "elemento": "Patrón del perfil: te adaptas a todos y a veces pierdes tu propio criterio.",
            "hilo": "En tu hilo central se ve el mismo patrón: sostienes armonía externa mientras negocias demasiado tu centro.",
            "sombra": "Sombra del perfil: dices sí para sostener aceptación y luego te quedas sin energía ni dirección.",
            "accion": "hoy di un no claro donde normalmente cedes por quedar bien",
        },
        "independiente": {
            "nombre": "Tu nombre se vive desde autosuficiencia: lideras en silencio y prefieres resolver sola o solo.",
            "elemento": "Patrón del perfil: te cuesta pedir ayuda y conviertes fortaleza en aislamiento.",
            "hilo": "En tu hilo central se repite esta lógica: sostienes mucho en solitario y eso enfría tus vínculos sin notarlo.",
            "sombra": "Sombra del perfil: el orgullo te protege, pero también te desconecta afectivamente.",
            "accion": "pide apoyo específico en una tarea concreta antes de agotarte",
        },
    }
    return pool.get(perfil, pool["adaptador"])


def _accion_limpia(perfil: str, seccion: str) -> str:
    a = _accion_perfil(perfil, seccion).strip()
    a = re.sub(r"(?i)^hoy\s+", "", a)
    return a.rstrip(".")


def _accion_perfil(perfil: str, seccion: str) -> str:
    acciones: dict[str, dict[str, str]] = {
        "controlador": {
            "planeta": "elige una decisión que hoy ibas a controlar por completo y comparte responsabilidad con otra persona",
            "totem": "detén una reacción de supervisión excesiva y reemplázala por una pregunta clara de seguimiento",
            "arcangel": "escribe en dos líneas qué sí controlas y qué no, y actúa solo sobre lo primero",
            "gema": "en una tarea clave, define un estándar suficiente y evita rehacer por perfeccionismo",
            "sabiduria": "delega un tramo concreto de una meta semanal y sostén la incomodidad sin retomarlo",
            "numerologia": "cierra una prioridad sin revisar tres veces detalles que ya están listos",
            "signo": "pide apoyo en una parte concreta del día que hoy sueles cargar sola o solo",
            "mensaje": "en 24 horas, delega una decisión menor y cumple sin volver a tomar el control",
            "nombre": "pon límite a una responsabilidad heredada que no te corresponde sostener",
        },
        "sobreanalitico": {
            "planeta": "elige una decisión pendiente y resuélvela con 70 por ciento de certeza en menos de 20 minutos",
            "totem": "si detectas bucle mental, escribe una sola opción viable y ejecútala sin abrir más escenarios",
            "arcangel": "antes de dormir, define una decisión de mañana y comprométete a no reanalizarla",
            "gema": "en una conversación difícil, usa dos frases directas en lugar de explicaciones largas",
            "sabiduria": "cierra una meta semanal por ejecución, no por análisis adicional",
            "numerologia": "toma una decisión financiera pequeña hoy y no la reabras durante 72 horas",
            "signo": "reduce a una sola condición no negociable lo que normalmente sobreexplicas",
            "mensaje": "en 24 horas, ejecuta una decisión pendiente sin pedir tercera validación externa",
            "nombre": "deja de esperar claridad total y actúa con la mejor evidencia disponible hoy",
        },
        "evitador_emocional": {
            "planeta": "en el próximo conflicto, di una incomodidad concreta antes de que se acumule",
            "totem": "nombra un límite temprano en lugar de esperar a estallar por cansancio",
            "arcangel": "escribe una frase que hoy callas y compártela sin disculparte por sentir",
            "gema": "si notas silencio defensivo, pide una pausa breve y vuelve con un límite claro",
            "sabiduria": "esta semana no cierres temas con 'está bien' cuando en realidad no lo está",
            "numerologia": "habla una verdad breve en un vínculo donde sueles evitar roce",
            "signo": "sustituye una evasión por una frase honesta de diez palabras",
            "mensaje": "en 24 horas, di un no respetuoso donde normalmente callas por paz aparente",
            "nombre": "elige una conversación pendiente y abre con una verdad pequeña pero real",
        },
        "impulsivo": {
            "planeta": "cuando sientas urgencia de decidir, pausa 90 segundos y define objetivo antes de responder",
            "totem": "en una reacción caliente, quita intensidad al tono sin ceder el límite",
            "arcangel": "aplaza diez minutos una respuesta impulsiva y revisa si sigue siendo necesaria",
            "gema": "elige una sola prioridad del día y termina esa antes de abrir otra",
            "sabiduria": "esta semana evita decisiones grandes en estado de enojo o ansiedad",
            "numerologia": "cierra una decisión en dos pasos: intención clara y acción verificable",
            "signo": "cuando aparezca la urgencia, reemplázala por una pregunta concreta de contexto",
            "mensaje": "en 24 horas, toma una decisión importante solo después de escribir el costo de impulsarte",
            "nombre": "ordena una decisión pendiente por impacto real, no por intensidad del momento",
        },
        "adaptador": {
            "planeta": "en una interacción clave, expresa una preferencia personal antes de acomodarte al otro",
            "totem": "sostén un no breve en el primer pedido que cruce tu límite",
            "arcangel": "deja de justificarte al poner límites y repite tu posición con calma",
            "gema": "por cada sí externo, agenda un sí explícito para tu propia prioridad",
            "sabiduria": "no ajustes tu ritmo a comparaciones; mide avance por consistencia personal",
            "numerologia": "hoy elige una decisión que te represente aunque no agrade a todo el mundo",
            "signo": "en una conversación difícil, no cambies tu postura para evitar rechazo inmediato",
            "mensaje": "en 24 horas, marca un límite claro donde sueles ceder por aceptación",
            "nombre": "elige una conducta diaria que te devuelva identidad propia sin pedir permiso",
        },
        "independiente": {
            "planeta": "pide ayuda concreta en una tarea puntual y evita resolverla sola o solo por inercia",
            "totem": "en vez de aislarte, comparte una necesidad práctica con alguien de confianza",
            "arcangel": "sustituye orgullo defensivo por una petición directa y medible",
            "gema": "cuando aparezca cansancio, delega antes de llegar al agotamiento silencioso",
            "sabiduria": "esta semana practica una colaboración breve en lugar de sostener todo en solitario",
            "numerologia": "define una prioridad y resuélvela en equipo, no en aislamiento",
            "signo": "en el próximo reto, comunica una necesidad en voz alta antes de cerrarte",
            "mensaje": "en 24 horas, abre espacio para apoyo real en algo que vienes cargando solo",
            "nombre": "rompe una rutina de autosuficiencia y permite una colaboración pequeña",
        },
    }
    p = acciones.get(perfil, acciones["adaptador"])
    return p.get(seccion, p["mensaje"])


def _linea_espejo_identidad(p: SoulProfile, nombre: str, sign: str, elem: str) -> str:
    if p.camino_vida in (1, 8):
        return f"{nombre}: no naciste para obedecer tu miedo, naciste para dirigir tu energía {sign} {elem} con criterio."
    if p.camino_vida in (2, 6):
        return f"{nombre}: cuando dejas de salvar a todos, aparece tu versión más auténtica y más amada."
    if p.camino_vida in (3, 5):
        return f"{nombre}: tu libertad real empieza el día que sostienes una decisión aunque incomode."
    return f"{nombre}: no estás fallando; estás aprendiendo a usar tu intensidad sin castigarte."


def _linea_golpe_sombra(p: SoulProfile, nombre: str) -> str:
    if p.camino_vida in (1, 8):
        return f"{nombre}: tu poder se vuelve imparable cuando dejas de confundir dureza con liderazgo."
    if p.camino_vida in (2, 6):
        return f"{nombre}: poner límites no te vuelve distante, te vuelve confiable contigo."
    if p.camino_vida in (3, 5):
        return f"{nombre}: madurar no es perder libertad, es elegir sin escapar."
    return f"{nombre}: la paz que buscas empieza cuando te tratas con la misma firmeza que ofreces a otros."


def compose_despertar_nombre(
    rng: random.Random, p: SoulProfile, nombre_pila: str, sign: str, elem: str
) -> str:
    np = _prim(p)
    kind = rng.randint(0, 2)
    if kind == 0:
        abre = (
            f"Tu mayor miedo no es el fracaso: es quedar atrapada o atrapado en una vida que pronunciás con voz ajena "
            f"cuando decís <i>{np}</i>."
        )
    elif kind == 1:
        abre = (
            f"¿Cuántas veces suavizaste la verdad para no incomodar, aunque por dentro <i>{np}</i> pedía un límite distinto?"
        )
    else:
        abre = (
            f"<i>{np}</i> es la primera palabra que el mundo te devuelve en espejo: no es etiqueta, es contrato emocional "
            f"con tu propia voz."
        )
    cuerpo = _pick(
        rng,
        (
            f"En el trabajo, en la familia, en la cama: cuando te apuran, el nombre se te achica o se te afila. "
            f"Con {elem} como temperatura y {sign} como estilo, no sos “demasiado”: estás mal traducida o mal traducido.",
            f"Hay días en que <i>{np}</i> te protege y días en que te delata: cuando fingís estar bien para no explicar el cansancio, "
            f"el cuermo ya sabe la verdad.",
            f"Si alguien usa tu nombre para controlarte, no es drama: es robo de dignidad. Recuperar <i>{np}</i> es volver a decidir "
            f"quién manda en tu pecho.",
        ),
    )
    cierre = _pick(
        rng,
        (
            "Esta página no te salva: te nombra. Y nombrarte bien es empezar a no traicionarte en lo chico.",
            "Lo que sigue no te explica desde arriba: te acompaña en lo cotidiano, donde se te escapa la paciencia.",
            "Si algo aquí duele, suele ser porque acertó: la precisión duele distinto que el insulto.",
        ),
    )
    return _br(abre, cuerpo, cierre)


def compose_herencia_sangre(
    rng: random.Random, p: SoulProfile, apellidos: str, nombre_pila: str, elem: str
) -> str:
    _, bloque_apellido = compose_name_identity_blocks(
        p.nombre,
        nombre_pila,
        apellidos,
        camino_vida=p.camino_vida,
        expresion=p.expresion,
        alma=p.alma,
        perfil_psicologico=p.perfil_psicologico,
        rng=rng,
    )
    np = (nombre_pila or "").strip() or (p.nombre.split()[0] if p.nombre else "tú")
    puente = rng.choice(
        (
            f"No es etiqueta genealógica fría: es vínculo vivo. El elemento <b>{elem}</b> muestra cómo ese linaje late en tu cuerpo—"
            "defensa, ternura, distancia, apego—y qué te cuesta cuando repites lealtades que nadie te devuelve.",
            f"{np}: al pronunciar tu apellido, algo en el pecho se ordena o se tensa; no es casualidad. "
            f"<b>{elem}</b> describe la textura con la que sostienes o sueltas ese pacto silencioso con quienes vinieron antes.",
        )
    )
    cierre = rng.choice(
        (
            "La tarea adulta no es negar el apellido ni glorificarlo: es heredar la fuerza sin quedarte presa de un guion que agotó a otras generaciones.",
            "Llevar un apellido con honor no es clavar la espalda: es reconocer de dónde vienes y decidir, con nombre propio, qué sigues sosteniendo.",
            "Cuando el linaje pesa, la salida no es huir del apellido: es traducirlo en límites sanos, ternura consciente y criterio que tu cuerpo pueda firmar.",
        )
    )
    return _br(bloque_apellido, puente, cierre)


def compose_esencia_astral_humana(
    rng: random.Random, p: SoulProfile, nombre: str, sign: str, elem: str
) -> str:
    kind = rng.randint(0, 2)
    if kind == 0:
        abre = f"{sign} no es un meme de personalidad: es el patrón con el que te levantás cuando el día aprieta sin avisar."
    elif kind == 1:
        abre = f"¿Notás que repetís el mismo tipo de conflicto con distintas caras? {sign} tiene un estilo de defensa que a veces te salva y a veces te aísla."
    else:
        abre = f"Tu carta no es horóscopo de revista: es un mapa de gestos. {sign} describe cómo iniciás, cómo cerrás y qué te dispara la vergüenza."

    cuerpo = _pick(
        rng,
        (
            f"El elemento {elem} no es decoración: es la textura con la que negociás el mundo. "
            f"Si te comparás con gente de otro temperamento, te sentís “mal” sin entender que solo sos distinta.",
            f"En la vida real, {elem} aparece en cómo pedís espacio, cómo comés el estrés y cómo elegís refugio cuando ya no das más.",
            f"Cuando alguien te dice “exagerás”, muchas veces te está pidiendo silencio para no mover su propia culpa. "
            f"{sign} y {elem} juntos explican por qué no sos neutral: sos viva.",
        ),
    )
    cierre = _pick(
        rng,
        (
            "Leer esto como cartel te encasilla; leerlo como patrón te devuelve opciones en la mesa del día a día.",
            "Si integrás gesto y textura, dejás de pelear contra vos como si fueras el error del grupo.",
            "Tu signo no te absuelve de responsabilidad: te da idioma para elegir con menos vergüenza ajena.",
        ),
    )
    return _br(abre, cuerpo, cierre)


def compose_guias_silenciosos(
    rng: random.Random,
    p: SoulProfile,
    planet: str,
    totem_label: str,
    arch_label: str,
    myth: str,
) -> str:
    abre = _pick(
        rng,
        (
            f"A veces lo que te guía no es un discurso: es un timbre. {planet} aparece cuando el miedo quiere prisa y el corazón pide sentido.",
            f"¿Sentís que tu vida tiene un “tema central” que vuelve aunque cambies de ciudad? {planet} es parte de esa insistencia —no castigo, repetición hasta aprender.",
            f"Tu planeta regente, {planet}, no es adorno: es la voz que modula cómo pedís reconocimiento y cómo soltáis lo que ya no sostiene.",
        ),
    )
    cuerpo_a = (
        f"{myth} "
        f"En la práctica, eso se traduce en decisiones chicas: qué contestás cuando te ignoran, cuánto tolerás antes de que el cuerpo te cobre la cuenta en seco, "
        f"cómo pedís amor sin mendigar humillación."
    )
    cuerpo_b = _pick(
        rng,
        (
            f"El tótem —aquí {totem_label}— no es mascota: es instinto. Es la parte tuya que sabe defender sin discurso, "
            f"la que se enciende cuando alguien cruza una línea que ni vos habías nombrado.",
            f"Cuando te decís “reacciono demasiado”, a veces es {totem_label} pidiendo territorio emocional. No es drama: es información.",
        ),
    )
    cuerpo_c = _pick(
        rng,
        (
            f"El arcángel —{arch_label}— lo leemos como figura de protección con borde: bondad con límite. "
            f"Te sirve cuando confundís amor con aguante eterno.",
            f"{arch_label} aparece cuando necesitás cortar dinámicas que te achican sin convertirte en persona cruel. "
            f"Protección real es dignidad, no armadura falsa.",
        ),
    )
    cierre = _pick(
        rng,
        (
            "Tres guías distintas, una sola vida: si las escuchás por separado, te fragmentás; si las leés juntas, recuperás calma activa.",
            "Nada aquí te pide creer en lo externo primero: te pide coherencia entre lo que sentís y lo que hacés cuando nadie aplaude.",
            "Si una sola frase te describe entera, te mentís: sos conversación entre timbre, instinto y límite santo.",
        ),
    )
    return _br(abre, cuerpo_a, cuerpo_b, cuerpo_c, cierre)


def compose_medicina_tierra(
    rng: random.Random, p: SoulProfile, gema_label: str, sign: str, elem: str
) -> str:
    abre = _pick(
        rng,
        (
            f"La gema —{gema_label}— no es bisutería espiritual: es símbolo de peso. En la vida real, “peso” es lo que te costó sostener sin romper a nadie.",
            f"Tu piedra, {gema_label}, habla de cómo administrás el brillo: si lo das todo a todo, te quedás sin superficie para vos.",
        ),
    )
    cuerpo = _pick(
        rng,
        (
            f"Si tu conflicto actual es controlar lo incontrolable, {elem} y {sign} ya te mostraron el desgaste: la gema te recuerda "
            f"que la sanación también es decir no sin culpa performática.",
            f"Cuando el vínculo se vuelve ansiedad disfrazada de amor, {gema_label} aparece como ancla: no magia, recordatorio de reciprocidad.",
        ),
    )
    cierre = _pick(
        rng,
        (
            "Menos brillo para afuera y más verdad para adentro: eso es medicina de tierra, aunque suene poco romántico.",
            "Cuidar la piedra simbólica es cuidar promesas cumplidas contigo: sin eso, cualquier ritual queda vacío.",
        ),
    )
    return _br(abre, cuerpo, cierre)


def compose_sabiduria_tiempo(
    rng: random.Random, p: SoulProfile, animal: str, sign: str
) -> str:
    abre = _pick(
        rng,
        (
            f"El año del {animal} no te borra el mapa occidental: te agrega un clima de paciencia o audacia que convive con {sign} sin pedir permiso.",
            f"¿Sentís que tu generación te empujó a una velocidad que tu cuerpo no firmó? El {animal} habla de ritmo largo, no de carrera de ego.",
        ),
    )
    cuerpo = _pick(
        rng,
        (
            f"Energía generacional no es excusa: es contexto. Te explica por qué ciertas presiones te suenan a verdad aunque te destruyan.",
            f"En la mesa familiar, en el trabajo, en el país: el {animal} recuerda ciclos. No sos “rezagada” si sanás más lento que el feed.",
        ),
    )
    cierre = _pick(
        rng,
        (
            "Cruzar tiempo oriental y gesto solar es dejar de leerte como error de época.",
            "Lo que llamás ‘tarde’ a veces es maduración que no se apura por aplausos.",
        ),
    )
    return _br(abre, cuerpo, cierre)


def compose_vibracion_maestra(rng: random.Random, p: SoulProfile, sign: str, animal: str) -> str:
    cv, ex, alm, pers = p.camino_vida, p.expresion, p.alma, p.personalidad
    abre = _pick(
        rng,
        (
            f"Tus números no son amuleto: son fotografía del ritmo. Camino {cv}, expresión {ex}, alma {alm}, personalidad {pers} — cuatro micrófonos, una sola voz.",
            f"Si te peleás con el {cv}, te peleás con tu propio tempo de maduración. No es castigo: es insistencia.",
        ),
    )
    cuerpo = _pick(
        rng,
        (
            f"El {cv} narra el arco largo; el {ex} narra cómo nombrás lo que sentís; el {alm} susurra lo que necesitás recibir; "
            f"el {pers} es la puerta visible. Cuando uno miente, los otros compensan con síntomas.",
            f"En el trabajo y en el amor, repetís patrones hasta que el número deja de ser curiosidad y se vuelve responsabilidad.",
        ),
    )
    cierre = (
        f"Cruce final: {sign} con camino {cv} y año del {animal}. No es fórmula genérica: es una combinación que explica por qué "
        f"tu vida no entra en manual ajeno."
    )
    return _br(abre, cuerpo, cierre)


def compose_hilo_contradiccion(
    rng: random.Random,
    p: SoulProfile,
    sign: str,
    totem_label: str,
    nombre_pila: str,
    apellidos: str,
    nombre_completo: str,
) -> str:
    perfil = _perfil_lineas(_perfil_slug(p))
    np = _prim(p)
    ap = _ap_txt(apellidos)
    lin = f" y la exigencia heredada de <i>{ap}</i>" if ap else " y la historia familiar que todavía te condiciona"
    if p.camino_vida in (1, 8):
        conflicto = "querés resolver todo rápido, pero el cuerpo acumula tensión cuando el corazón no alcanza a nombrar lo que pasa"
        accion = "elige una sola batalla de esta semana y renuncia conscientemente a las demás"
    elif p.camino_vida in (2, 6):
        conflicto = "sostienes vínculos por lealtad incluso cuando ya no hay reciprocidad"
        accion = "pon una condición mínima de reciprocidad en un vínculo clave y cúmplela"
    elif p.camino_vida in (3, 5):
        conflicto = "saltas entre opciones para evitar sentir incomodidad sostenida"
        accion = "cierra una decisión pendiente y mantenla 7 días sin cambiarla"
    else:
        conflicto = "te rigidizas para no fallar y terminas sintiendo que todo depende de ti"
        accion = "define qué sí te corresponde y qué vas a devolver sin culpa"
    abre = rng.choice(
        (
            "<b>Hilo invisible</b> · lectura psicológica<br/>"
            "Esto no es misticismo barato: es la explicación de por qué brillás en una cosa y te trabás en otra.",
            "<b>Hilo invisible</b> · contradicción real<br/>"
            "No estás \"rota/o\": estás viviendo dos apuestas al mismo tiempo y el cuerpo cobra la diferencia.",
        )
    )
    cuerpo = (
        f"Qué te pasa realmente: <i>{np}</i>{lin}, tu patrón {sign} y el instinto de {totem_label} tiran de ti al mismo tiempo. "
        f"Resultado: {conflicto}."
    )
    ps = _perfil_slug(p)
    if ps == "adaptador":
        impacto = (
            "Consecuencia práctica: pagas con fatiga relacional cuando cedes demasiado para sostener equilibrio y luego te cuesta recuperar tu postura."
        )
    elif ps == "evitador_emocional":
        impacto = (
            "Consecuencia práctica: cuando posponés el roce, el vínculo queda \"lindo\" arriba y frío abajo… "
            "y después se prende por un detalle mínimo que no era el detalle."
        )
    elif ps == "independiente":
        impacto = (
            "Consecuencia práctica: la autosuficiencia extrema te deja eficiente por fuera y sola o solo por dentro, con menos apoyo del que podrías tener."
        )
    elif ps == "sobreanalitico":
        impacto = (
            "Consecuencia práctica: el análisis infinito te roba tiempo real y te deja con decisiones pospuestas mientras la vida sigue avanzando."
        )
    elif ps == "controlador":
        impacto = (
            "Consecuencia práctica: intentar cubrir cada detalle te deja agotamiento y vínculos donde otros se acostumbran a no responsabilizarse."
        )
    else:
        impacto = (
            "Consecuencia práctica: la urgencia repetida te deja correcciones constantes y vínculos donde el tono sube antes de que haya claridad."
        )
    cierre = (
        f"Paso de hoy: usa tu nombre completo —<i>{nombre_completo}</i>— como dirección, no como carga. {accion}"
    )
    return _br(abre, _lector_momento_wow(rng, "hilo"), perfil["hilo"], cuerpo, impacto, cierre)


def compose_sombra_honesta(rng: random.Random, p: SoulProfile, sign: str, elem: str, shadow_frag: str) -> str:
    abre = _pick(
        rng,
        (
            f"Tu sombra no es enemiga: es la parte que aún no recibió nombre sin vergüenza. {shadow_frag}",
            f"La honestidad que duele es la que te quita la fantasía de ser “fácil” para todos. {sign} y {elem} marcan cómo te defendés cuando tenés miedo.",
        ),
    )
    cuerpo = _pick(
        rng,
        (
            f"Si te controla el miedo al abandono, a veces das de más y después resentís en silencio: eso no te hace mala persona, te hace humana sin apoyo.",
            f"Cuando el cansancio te vuelve dura, no es “tu peor versión”: es protección torpe. Nombrarla baja la vergüenza.",
        ),
    )
    cierre = _pick(
        rng,
        (
            "Integrar sombra no es autoelogio: es dejar de pelearte como si fueras el error del mundo.",
            "Sanar duele distinto que herir: uno te devuelve lucidez, el otro te devuelve compañía en la culpa.",
        ),
    )
    return _br(abre, cuerpo, cierre)


def compose_pagina_poder_una_frase(rng: random.Random, p: SoulProfile, sign: str, elem: str) -> str:
    opts = (
        f"Tu mayor fortaleza no es aguantar en silencio: es volver a elegirte cuando nadie te mira, con {sign} y {elem} como testigos internos.",
        f"Lo que otros llaman terquedad, acá se llama lealtad a lo vivo: no negociar tu nombre por aplausos baratos.",
        f"Tu poder real es precisión emocional: decir basta antes de odiarte, y pedir ayuda antes de romperse en silencio.",
        f"No necesitás ser invencible: necesitás ser veraz. Eso es fuerza que no performa.",
        f"Si algo te sostiene hoy, que sea esto: podés cambiar el guion sin traicionar tu historia.",
    )
    return _pick(rng, opts)


def compose_vinculos_verdad(
    rng: random.Random, p: SoulProfile, sign: str, elem: str, planet: str
) -> str:
    abre = _pick(
        rng,
        (
            f"Amar no es fusionarte hasta desaparecer: es elegir cercanía sin entregar el timón. {elem} marca cómo pedís contención sin mendigar.",
            f"¿Cuántas veces protegiste al otro del malestar que vos necesitabas nombrar? {sign} tiene un estilo de vínculo que a veces confunde cuidado con control.",
        ),
    )
    cuerpo = _pick(
        rng,
        (
            f"Te protegés cerrando, anticipando, explicando demasiado —o entregando todo para que no se vayan. {planet} modula ese ritmo: "
            f"te muestra dónde pedís reconocimiento y dónde tenés miedo al rechazo.",
            f"En la intimidad, lo que duele no siempre es traición: a veces es haber dicho sí cuando el cuerpo pedía pausa.",
        ),
    )
    cierre = _pick(
        rng,
        (
            "Vínculo sano no es ausencia de fricción: es verdad sin humillar al corazón.",
            "Protección real incluye límites hermosos: no muros de miedo disfrazados de amor.",
        ),
    )
    return _br(abre, cuerpo, cierre)


def compose_mensaje_urgente(rng: random.Random, nombre: str) -> str:
    a = _pick(
        rng,
        (
            f"{nombre}: lo que tu alma necesita escuchar hoy no es una frase bonita; es permiso para no cargar solo lo que no empezó contigo.",
            f"{nombre}, si estás agotada o agotado, no es porque seas débil: es porque intentaste ser coherente en un mundo que premia la performance.",
            f"{nombre}: cerrar este mapa con dignidad es un acto de valentía. Nadie puede hacer el tramo íntimo por vos.",
        ),
    )
    b = _pick(
        rng,
        (
            "Hoy no necesitás tener claridad total: necesitás un paso honesto, aunque tiemble.",
            "Si algo aquí te partió, probablemente sea porque te nombró bien —y lo que nombra bien duele antes de aliviar.",
            "El clímax no es ruido: es el momento en que dejás de mentirte para sostenerte.",
        ),
    )
    c = _pick(
        rng,
        (
            "Lo urgente es humano: dormir, comer, pedir ayuda, decir no. Lo sagrado baja a eso o no baja.",
            "Tu historia no es castigo: es material para lucidez con ternura firme.",
        ),
    )
    return _br(a, b, c)


def compose_oraculo_minimo(rng: random.Random) -> str:
    return _pick(
        rng,
        (
            "Tres líneas siguen: no son magia. Son instrucciones nerviosas para volver a casa en vos.",
            "El oráculo aquí es sobrio: luz para no confundir dolor con derrota, ni amor con deuda.",
            "Cierra con tres afirmaciones secas. Léelas en voz baja: el cuerpo entiende antes que el ego.",
        ),
    )


def compose_afirmaciones_secas(
    rng: random.Random, p: SoulProfile, nombre: str, sign: str, elem: str
) -> tuple[str, str, str]:
    np = _prim(p)
    pool = [
        "Elijo no traicionarme en lo pequeño, aunque el día pida prisa.",
        f"Mi nombre —{np}— no es excusa: es responsabilidad.",
        f"{sign} y {elem} me alían: no me definen para encasillarme.",
        f"Camino {p.camino_vida}: integro ritmo sin castigarme por sanar lento.",
        f"Expresión {p.expresion}: digo lo que siento sin humillar al corazón.",
        "Hoy elijo límites hermosos antes que aplausos falsos.",
        "Si tiemblo, no me desprecio: me reconozco.",
        "Un paso honesto vale más que una vida coherente en Instagram.",
    ]
    rng.shuffle(pool)
    return pool[0], pool[1], pool[2]


def compose_back_cover_human(
    rng: random.Random,
    p: SoulProfile,
    nombre: str,
    sign: str,
    planet: str,
    animal: str,
    nacimiento: str,
) -> str:
    x = _pick(
        rng,
        (
            f"Este mapa quedó escrito para {nombre}, desde {nacimiento}, con {sign} como gesto recurrente, {planet} como timbre y el {animal} como memoria de tiempo largo.",
            f"{nombre}: {nacimiento} abre el libro; {animal}, {sign} y {planet} lo cierran como una sola conversación honesta.",
        ),
    )
    y = _pick(
        rng,
        (
            "Llévalo como espejo, no como cadena: la lectura más verdadera es la que te devuelve dignidad.",
            "No es promesa de perfección: es lenguaje para volver a casa en vos sin humillarte en el intento.",
        ),
    )
    z = _pick(
        rng,
        (
            f"Que no se te escape lo central: este mapa también es un acto de amor hacia el nombre que te habita —hacia <i>{nombre}</i> como palabra viva, "
            f"con historia, con derecho a ser pronunciada con respeto y conocida hasta el fondo.",
            f"El cielo y los símbolos acompañan, pero el eje sigue siendo humano: entender de verdad quién sos cuando decís tu nombre y lo sostenés con lucidez.",
        ),
    )
    return _br(x, y, z)


# --- Sección 2: el corazón onomástico del libro (mucho más que “vibración”) ---


def compose_codigo_nombre(
    rng: random.Random, p: SoulProfile, nombre_pila: str, sign: str, elem: str
) -> str:
    """
    Eje onomástico con base filológica real:
    raíz lingüística + etimón + trayectoria cultural + lectura psicohistórica aplicada.
    """
    bloque_nombre, _ = compose_name_identity_blocks(
        p.nombre,
        nombre_pila,
        p.apellidos,
        camino_vida=p.camino_vida,
        expresion=p.expresion,
        alma=p.alma,
        perfil_psicologico=p.perfil_psicologico,
        rng=rng,
    )
    perfil = _perfil_lineas(_perfil_slug(p))
    ps = _perfil_slug(p)
    if ps == "evitador_emocional":
        marco = (
            f"Traducción cotidiana: {nombre_pila}, cuando algo molesta, a veces respondes con distancia educada "
            f"—\"no pasa nada\"— aunque por dentro sí pase. Eso te protege al instante y te cobra después en sueño, apetito o irritación."
        )
    elif ps == "adaptador":
        marco = (
            f"Traducción cotidiana: {nombre_pila}, en WhatsApp, en familia y en trabajo, afinás el tono para no quedar mal. "
            f"El costo aparece cuando te olvidás de tu postura y solo queda la performance de \"estar bien\"."
        )
    elif ps == "independiente":
        marco = (
            f"Traducción cotidiana: {nombre_pila}, resolvés rápido y en solitario: banco, salud, vínculos. "
            f"Funciona… hasta que el cansancio no se explica con café y sí con falta de apoyo real."
        )
    else:
        marco = (
            f"Traducción cotidiana: {nombre_pila}, esta raíz aparece en decisiones pequeñas: qué contestás, qué tolerás y qué dejas pasar "
            f"en trabajo, pareja y familia."
        )
    metodo = (
        f"<b>Lectura del nombre + {sign} + {elem}.</b> {perfil['nombre']} "
        f"Acá no buscás \"una etiqueta bonita\": buscás coherencia entre lo que te dicen que sos y lo que vos sabés que te sostiene."
    )
    cierre = f"Acción de hoy: {_accion_limpia(_perfil_slug(p), 'nombre')}."
    return _br(bloque_nombre, marco, metodo, cierre)


def compose_eco_ancestros(
    rng: random.Random, p: SoulProfile, apellidos: str, nombre_pila: str, elem: str
) -> str:
    return compose_herencia_sangre(rng, p, apellidos, nombre_pila, elem)


def compose_esencia_signo(
    rng: random.Random, p: SoulProfile, nombre: str, nombre_pila: str, sign: str, elem: str
) -> str:
    del elem
    ps = _perfil_slug(p)
    accion = f"Qué hacer hoy: {_accion_limpia(ps, 'signo')}."
    if ps == "adaptador":
        plantilla = rng.choice(("lista", "carta", "micro"))
        if plantilla == "lista":
            return _br(
                f"<b>Signo {sign} — lectura en 3 líneas</b>",
                f"<b>1.</b> {nombre_pila}, buscás equilibrio, a veces a costa de tu postura.<br/>"
                f"<b>2.</b> En el día a día eso se ve en mensajes suavizados, acuerdos a medias y \"sí\" que no sentís.<br/>"
                f"<b>3.</b> El límite adulto: armonía sin autoboicot.",
                accion,
            )
        if plantilla == "carta":
            return _br(
                f"<b>Carta breve a {nombre_pila}</b> (firma: {sign})",
                f"Hola: cuando el ambiente se tensa, te volvés traductora del grupo. Eso es talento… y también cansancio si nadie traduce tu parte.",
                accion,
            )
        return _br(
            f"{nombre_pila}, {sign} en modo micro: equilibrio sí, pero no a cualquier precio.",
            "Si cada conversación termina en vos cediendo primero, no es paz: es hábito.",
            accion,
        )
    if ps == "evitador_emocional":
        plantilla = rng.choice(("escena", "lista", "carta"))
        if plantilla == "escena":
            return _br(
                f"<b>Escena real</b> · {sign}",
                f"{nombre}, alguien pisa un límite y vos respondés con frialdad educada: cambiás de tema, sonreís, cerrás el chat. "
                f"Funciona… y dos días después te molestás con vos por no haber dicho la frase simple que faltaba.",
                accion,
            )
        if plantilla == "lista":
            return _br(
                f"<b>Signo {sign} — lectura en 3 líneas</b>",
                f"<b>1.</b> Detectás roce antes que el otro.<br/>"
                f"<b>2.</b> Elegís aplazar el roce (mensaje corto, evasión, humor).<br/>"
                f"<b>3.</b> El cuerpo cobra la cuenta: sueño, apetito, irritación.",
                accion,
            )
        return _br(
            f"<b>Carta breve a {nombre_pila}</b> (firma: {sign})",
            f"Querés paz, sí. Pero si la paz es \"no tocar el tema\", termina siendo prisión con música zen.",
            accion,
        )
    if ps == "independiente":
        plantilla = rng.choice(("lista", "micro", "carta"))
        if plantilla == "lista":
            return _br(
                f"<b>Signo {sign} — lectura en 3 líneas</b>",
                f"<b>1.</b> {nombre}, resolvés rápido y en solitario.<br/>"
                f"<b>2.</b> Pedir ayuda se siente como perder control.<br/>"
                f"<b>3.</b> El límite adulto: autonomía con cooperación puntual.",
                accion,
            )
        if plantilla == "carta":
            return _br(
                f"<b>Carta breve a {nombre}</b> (firma: {sign})",
                "No sos fría o frío: sos eficiente. El problema empieza cuando la eficiencia se vuelve muro y el otro deja de intentar acercarse.",
                accion,
            )
        return _br(
            f"{nombre_pila}, {sign} en modo micro: podés sostener mucho… pero no infinito.",
            "Si el orgullo te protege, también te puede dejar sola o solo en lo que más importa.",
            accion,
        )
    if ps == "sobreanalitico":
        plantilla = rng.choice(("lista", "micro", "carta"))
        if plantilla == "lista":
            return _br(
                f"<b>Signo {sign} — lectura en 3 líneas</b>",
                f"<b>1.</b> {nombre_pila}, leés escenarios con lupa.<br/>"
                f"<b>2.</b> Tu miedo no es equivocarte: es equivocarte a la vista.<br/>"
                f"<b>3.</b> El límite adulto: decidir con información suficiente, no infinita.",
                accion,
            )
        if plantilla == "carta":
            return _br(
                f"<b>Carta breve a {nombre_pila}</b> (firma: {sign})",
                "Tu cabeza te salvó mil veces. Ahora te toca enseñarle a soltar cuando ya alcanzó.",
                accion,
            )
        return _br(
            f"{nombre_pila}, {sign} en modo micro: claridad sí, parálisis no.",
            "Si cada decisión necesita un comité interno, el mundo sigue mientras vos seguís deliberando.",
            accion,
        )
    if ps == "controlador":
        plantilla = rng.choice(("lista", "micro", "carta"))
        if plantilla == "lista":
            return _br(
                f"<b>Signo {sign} — lectura en 3 líneas</b>",
                f"<b>1.</b> {nombre}, ordenás el caos ajeno y el tuyo.<br/>"
                f"<b>2.</b> Cuando hay incertidumbre, sube el mando preventivo.<br/>"
                f"<b>3.</b> El límite adulto: liderar sin cargar el mundo entero.",
                accion,
            )
        if plantilla == "carta":
            return _br(
                f"<b>Carta breve a {nombre}</b> (firma: {sign})",
                "Tu estándar alto es virtud. Cuando se vuelve latigo interno, deja de ser virtud y empieza a ser castigo.",
                accion,
            )
        return _br(
            f"{nombre_pila}, {sign} en modo micro: previsión sí, hipervigilancia no.",
            "Si controlás todo, nadie aprende a responder… y vos no descansás nunca.",
            accion,
        )
    plantilla = rng.choice(("lista", "micro", "carta"))
    if plantilla == "lista":
        return _br(
            f"<b>Signo {sign} — lectura en 3 líneas</b>",
            f"<b>1.</b> {nombre_pila}, cuando sentís presión, acelerás.<br/>"
            f"<b>2.</b> La urgencia te hace sentir vivo/a… y también te mete en líos evitables.<br/>"
            f"<b>3.</b> El límite adulto: velocidad con dirección.",
            accion,
        )
    if plantilla == "carta":
        return _br(
            f"<b>Carta breve a {nombre_pila}</b> (firma: {sign})",
            "No estás \"demasiado\": estás mal regulada/o en intensidad. Eso se entrena, no se borra.",
            accion,
        )
    return _br(
        f"{nombre_pila}, {sign} en modo micro: impulso con brújula.",
        "Si respondés rápido para no sentirte vulnerable, después pagás con arrepentimiento o reparaciones.",
        accion,
    )


def compose_esencia_elemento(
    rng: random.Random, p: SoulProfile, nombre: str, sign: str, elem: str
) -> str:
    ps = _perfil_slug(p)
    inicio = (
        f"<b>Tu elemento en carne viva</b> · {elem} + {sign}<br/>"
        f"{nombre}: esto no es un manual frío; es el modo en que tu cuerpo ejecuta el día cuando el mundo exige una respuesta ya."
    )
    wow = _linea_espejo_identidad(p, nombre, sign, elem)
    if ps == "adaptador":
        real = "<b>Patrón.</b> Afinás el ambiente: cedés primero para que no se rompa el clima."
        valid = "<b>Raíz.</b> Asociás pertenencia con disponibilidad constante."
        limite = "<b>Costo.</b> Te quedás sin espacio propio y después resentís sin saber nombrarlo."
        accion = "<b>Práctica.</b> En una conversación clave, decí tu posición en una frase y recién después negociá detalles."
    elif ps == "evitador_emocional":
        real = "<b>Patrón.</b> Posponés el roce: suavizás, desviás, cerrás. La tensión no desaparece: se muda de lugar."
        valid = "<b>Raíz.</b> El roce te lee como amenaza de pérdida o desgaste extremo."
        limite = "<b>Costo.</b> Te quedás con la culpa encima y el otro a veces ni se enteró del límite que se pisó."
        accion = "<b>Práctica.</b> Escribí una frase de 12 palabras con el límite real y enviala (sin bloque de autojustificación)."
    elif ps == "independiente":
        real = "<b>Patrón.</b> Resolvés sola/o: pedir ayuda se siente como bajar el nivel."
        valid = "<b>Raíz.</b> Aprendiste que depender dolía, entonces cargás."
        limite = "<b>Costo.</b> Eficiencia con soledad: el vínculo se enfría sin drama visible."
        accion = "<b>Práctica.</b> Pedí ayuda en un tramo concreto y dejá que el otro responda imperfecto (sin retomarlo)."
    elif ps == "sobreanalitico":
        real = "<b>Patrón.</b> Abrís escenarios: más variables, más seguridad ficticia."
        valid = "<b>Raíz.</b> El error visible te pesa más que el error privado."
        limite = "<b>Costo.</b> Te quedás en el tablero mientras la vida ejecuta sin vos."
        accion = "<b>Práctica.</b> Decidí con 70% de certeza, comunicá en 2 frases y cerrá 72h sin reabrir."
    elif ps == "controlador":
        real = "<b>Patrón.</b> Anticipás: orden, checklist, correcciones."
        valid = "<b>Raíz.</b> El caos te dispara al mando preventivo."
        limite = "<b>Costo.</b> Te convertís en responsable universal y después resentís la falta de reciprocidad."
        accion = "<b>Práctica.</b> Delegá un tramo con entregable claro y no lo supervises microscópicamente."
    else:
        real = "<b>Patrón.</b> Acelerás: la urgencia te ordena el cuerpo antes que la cabeza."
        valid = "<b>Raíz.</b> La vulnerabilidad se siente como pérdida de control."
        limite = "<b>Costo.</b> Discusiones evitables y reparaciones caras."
        accion = "<b>Práctica.</b> 60 segundos: objetivo + límite + recién ahí respuesta."
    cierre_vivo = _pick(
        rng,
        (
            "<b>Reflexión.</b> Si esto te llegó al pecho, ya no es teoría: es memoria corporal pidiendo nombre.",
            "<b>Te queda una pregunta.</b> ¿Qué parte de tu elemento podés honrar hoy sin pedir permiso a nadie?",
            "<b>Cierre.</b> No tenés que explicar tu temperamento: tenés que habitarte con ternura firme.",
        ),
    )
    return _br(inicio, real, valid, limite, accion, wow, cierre_vivo)


def compose_planeta_regente(
    rng: random.Random,
    p: SoulProfile,
    nombre: str,
    planet: str,
    myth: str,
) -> str:
    ps = _perfil_slug(p)
    simbolo = rng.choice(
        (
            f"<b>Ritual simbólico</b> · {planet}<br/>"
            f"{nombre}: imaginá un trono que no es vanidad, es lugar. {myth}",
            f"<b>Imagen nocturna</b> · {planet}<br/>"
            f"{nombre}: esto no es \"astrología bonita\". Es un lenguaje para ver dónde te peleás con el deseo, el poder y el reconocimiento. {myth}",
        )
    )
    if ps == "adaptador":
        lectura = (
            f"<b>Traducción humana.</b> {planet} te muestra dónde cedés postura para sostener vínculo: "
            f"en el tono del mensaje, en lo que aceptás en voz baja aunque no estés de acuerdo, en lo que prometés para que no se enfríe el clima."
        )
        cierre = "<b>Clave.</b> Agradar no puede ser tu única estrategia de supervivencia."
    elif ps == "evitador_emocional":
        lectura = (
            f"<b>Traducción humana.</b> {planet} aparece cuando el cuerpo ya está en alerta y vos todavía estás en modo \"paso de largo\": "
            f"humor, trabajo extra, pantalla, mensaje corto. No es flojera: es sistema nervioso buscando salida sin choque."
        )
        cierre = "<b>Clave.</b> Si no nombrás el roce a tiempo, lo pagás con distancia o con una reacción que no te reconocés."
    elif ps == "independiente":
        lectura = (
            f"<b>Traducción humana.</b> {planet} refuerza tu modo \"yo lo arreglo\": banco, salud, decisiones. "
            f"Funciona… hasta que el cansancio no es físico: es emocional por falta de reciprocidad."
        )
        cierre = "<b>Clave.</b> Pedir ayuda no te baja de rango: te devuelve tiempo real."
    elif ps == "sobreanalitico":
        lectura = (
            f"<b>Traducción humana.</b> {planet} te mete en bucles de escenario: más variables, más \"seguridad\"… y menos cierre. "
            f"Ahí aparece la ansiedad de quedar mal si decidís."
        )
        cierre = "<b>Clave.</b> La decisión imperfecta hoy vale más que la perfecta nunca."
    elif ps == "controlador":
        lectura = (
            f"<b>Traducción humana.</b> {planet} te activa el mando preventivo: anticipás, corregís, supervisás. "
            f"Eso ordena… y también puede convertirte en responsable universal."
        )
        cierre = "<b>Clave.</b> Liderazgo es repartir peso, no cargarlo todo."
    else:
        lectura = (
            f"<b>Traducción humana.</b> {planet} acelera el impulso: querés respuesta ya para no sentirte expuesto/a. "
            f"El problema no es energía: es dirección."
        )
        cierre = "<b>Clave.</b> Primero intención, después palabra."
    accion = f"Movimiento: {_accion_limpia(ps, 'planeta')}."
    return _br(simbolo, _lector_momento_wow(rng, "planeta"), lectura, cierre, accion)


def compose_totem_pagina(
    rng: random.Random, p: SoulProfile, nombre: str, totem_label: str, sign: str
) -> str:
    ps = _perfil_slug(p)
    if ps == "adaptador":
        origen = (
            f"El tótem {totem_label} marca tu instinto de pertenencia: lees el grupo, ajustas tu ritmo y buscas equilibrio, aunque a veces pagues con tu centro."
        )
    elif ps == "evitador_emocional":
        origen = (
            f"El tótem {totem_label} marca instinto de defensa suave: leés tensión, cambiás de carril y posponés el choque… "
            f"hasta que el sistema nervioso pide salida con otra forma (irritación, aislamiento, cierre brusco)."
        )
    elif ps == "independiente":
        origen = (
            f"El tótem {totem_label} marca tu instinto de autosuficiencia: avanzas sola o solo, resuelves rápido y cuesta pedir apoyo antes de saturarte."
        )
    elif ps == "sobreanalitico":
        origen = (
            f"El tótem {totem_label} marca tu instinto de lectura fina: observas señales, comparas escenarios y a veces te quedas demasiado tiempo en la cabeza."
        )
    elif ps == "controlador":
        origen = (
            f"El tótem {totem_label} marca tu instinto de orden: anticipas riesgos, organizas el entorno y sostienes resultados con alta exigencia."
        )
    else:
        origen = (
            f"El tótem {totem_label} marca tu instinto de respuesta rápida: cuando sube la presión, actúas primero y ordenas consecuencias después."
        )
    estilo = rng.choice(("diario", "mito", "contrato"))
    if estilo == "diario":
        cuerpo = (
            f"<b>Diario de campo</b> · {totem_label}<br/>"
            f"{nombre}: hoy el instinto no te pide \"creer en magia\", te pide leer señales: "
            f"cuándo te achicás, cuándo te endurecés, cuándo elegís paz falsa para no pelear."
        )
    elif estilo == "mito":
        cuerpo = (
            f"<b>Mito corto</b> · {totem_label}<br/>"
            f"En la selva interna, {nombre}, este animal no es decoración: es el modo en que tu cuerpo dice "
            f"\"acá hay peligro\" antes que tu boca lo nombre."
        )
    else:
        cuerpo = (
            f"<b>Contrato contigo</b> · {totem_label}<br/>"
            f"{nombre}: si este tótem fuera un acuerdo, diría: \"te protejo, pero no te dejo esconderte para siempre\"."
        )
    if ps == "adaptador":
        leccion = f"Lección: {sign} te pide vínculo, {totem_label} te pide que el vínculo no te borre."
    elif ps == "evitador_emocional":
        leccion = f"Lección: {totem_label} no te premia por aguantar; te avisa cuando ya estás en rojo."
    elif ps == "independiente":
        leccion = f"Lección: {totem_label} te recuerda que la fortaleza sin apoyo se vuelve coraza."
    elif ps == "sobreanalitico":
        leccion = f"Lección: {totem_label} te saca de la cabeza y te devuelve al cuerpo (donde sí o sí se decide)."
    elif ps == "controlador":
        leccion = f"Lección: {totem_label} te pide liderar sin convertirte en vigilante de todo."
    else:
        leccion = f"Lección: {totem_label} te pide canal, no cañón."
    accion = (
        "<b>Protección real.</b> Nada de humillación disfrazada de humor, nada de control disfrazado de cuidado. "
        f"<b>Hoy.</b> {_accion_limpia(ps, 'totem')}."
    )
    return _br(origen, cuerpo, leccion, accion)


def compose_arcangel_pagina(
    rng: random.Random, p: SoulProfile, nombre: str, arch_label: str, planet: str
) -> str:
    ps = _perfil_slug(p)
    origen = rng.choice(
        (
            f"{arch_label} no es \"ángel de vitrina\": es límite santo. Protección sin consentimiento a humillación.",
            f"{arch_label} llega con regla simple: amor con respeto. Si falta uno, no es amor maduro: es acuerdo torcido.",
        )
    )
    if ps == "adaptador":
        personal = f"{nombre}: con {planet} prendido, te sale negociar el alma para que el ambiente no se enfríe."
        mision = "Crecimiento: límites serenos que no necesitan discurso largo."
    elif ps == "evitador_emocional":
        personal = f"{nombre}: con {planet} prendido, posponés el roce como si el tiempo lo resolviera. El cuerpo sabe que no."
        mision = "Crecimiento: verdad breve, sin performance de \"tranquila/o\"."
    elif ps == "independiente":
        personal = f"{nombre}: con {planet} prendido, te cerrás en autosuficiencia antes que en pedido."
        mision = "Crecimiento: apoyo real sin perder dirección."
    elif ps == "sobreanalitico":
        personal = f"{nombre}: con {planet} prendido, tu cabeza abre juicio, escenarios y defensa… y se te va el cierre."
        mision = "Crecimiento: síntesis y acción visible."
    elif ps == "controlador":
        personal = f"{nombre}: con {planet} prendido, sube el mando preventivo: querés que nada se salga."
        mision = "Crecimiento: orden con aire, no con miedo."
    else:
        personal = f"{nombre}: con {planet} prendido, la urgencia te gana la carrera antes que la claridad."
        mision = "Crecimiento: pausa con nombre propio."
    accion = (
        "<b>Prohibido.</b> Culpa por poner límites, paz comprada con humillación, y acuerdos donde solo vos cedés. "
        f"<b>Hoy.</b> {_accion_limpia(ps, 'arcangel')}."
    )
    return _br(origen, personal, mision, accion)


def compose_gema_poder_pagina(
    rng: random.Random, p: SoulProfile, nombre: str, gema_label: str, sign: str, elem: str
) -> str:
    ps = _perfil_slug(p)
    origen = rng.choice(
        (
            f"<b>Ancla</b> · {gema_label}<br/>"
            f"{nombre}: esto no es \"energía\" abstracta. Es objeto-ritual: te devuelve al cuerpo cuando la cabeza acelera.",
            f"<b>Piedra de trabajo</b> · {gema_label}<br/>"
            f"{nombre}: cuando {sign} y {elem} prenden el drama, esta imagen te pide una sola cosa: claridad con pies en la tierra.",
        )
    )
    if ps == "adaptador":
        personal = f"En tu historia, {nombre}, esta medicina aparece cuando cedes prioridades propias para sostener aceptación."
        mision = "La fortaleza aquí es equilibrio con reciprocidad."
    elif ps == "evitador_emocional":
        personal = f"{nombre}: aparece cuando posponés el roce y el malestar se muda de lugar (cuerpo, sueño, irritación)."
        mision = "Fortaleza: límite temprano, sin discurso de mártir."
    elif ps == "independiente":
        personal = f"En tu historia, {nombre}, aparece cuando resuelves sola o solo, no delegas y te aíslas del apoyo disponible."
        mision = "La fortaleza aquí es compartir carga sin perder autonomía."
    elif ps == "sobreanalitico":
        personal = f"En tu historia, {nombre}, aparece cuando dudas en exceso y buscas validación antes de decidir."
        mision = "La fortaleza aquí es criterio propio con cierre oportuno."
    elif ps == "controlador":
        personal = f"En tu historia, {nombre}, aparece cuando supervisas todo para evitar errores y terminas sobrecargada o sobrecargado."
        mision = "La fortaleza aquí es priorizar y delegar con método."
    else:
        personal = f"En tu historia, {nombre}, aparece cuando reaccionas por urgencia y luego gastas energía en correcciones."
        mision = "La fortaleza aquí es canalizar intensidad con foco."
    accion = (
        f"<b>Hoy.</b> {_accion_limpia(ps, 'gema')}."
    )
    return _br(origen, _lector_momento_wow(rng, "gema"), personal, mision, accion)


def compose_sabiduria_oriental_pagina(
    rng: random.Random, p: SoulProfile, nombre: str, animal: str, sign: str
) -> str:
    inicio = _pick(
        rng,
        (
            f"<b>Memoria larga</b> · {animal}<br/>"
            f"{nombre}: esto no compite con {sign}. Se sube al mismo carro: te explica por qué algunas cosas te llevan más tiempo… y más profundidad.",
            f"<b>Ritmo</b> · {animal}<br/>"
            f"{nombre}: el zodiaco chino no te insulta con \"vas tarde\": te recuerda que tu vida tiene fases, no sprint continuo.",
        ),
    )
    real = (
        f"<b>Hoy.</b> Con {sign} arriba, el mundo te empuja a compararte. {animal} te devuelve el contrapeso: "
        f"tu avance puede ser lento y serio, y aun así válido."
    )
    valid = "<b>Verdad simple.</b> Ir a tu ritmo no es flojera: es no repetir el mismo error por ansiedad."
    limite = "<b>Pará.</b> Dejá de medir tu vida con el cronómetro ajeno (redes, familia, \"lo que toca a esta edad\")."
    accion = f"<b>Movimiento.</b> {_accion_limpia(_perfil_slug(p), 'sabiduria')}."
    return _br(inicio, real, valid, limite, accion)


def _numerologia_cuatro_palancas_vivas(rng: random.Random, cv: int, ex: int, alm: int, pers: int) -> str:
    """Cómo se siente cada número en cuerpo y conflicto (no solo definición)."""
    camino = _pick(
        rng,
        (
            f"<b>Camino {cv} · sensación.</b> Es la música baja de tus años grandes: aparece cuando comparás tu vida, "
            "cuando sentís que el tiempo se te escapa o cuando elegís un camino largo aunque el cuerpo pida descanso.",
            f"<b>Camino {cv} · sensación.</b> Se vive como brújula seria: no siempre es cansancio visible; "
            "a veces es la urgencia de rendir cuentas contigo antes que con el escenario externo.",
        ),
    )
    expresion = _pick(
        rng,
        (
            f"<b>Expresión {ex} · sensación.</b> Es la temperatura de tu voz cuando el corazón aprieta: "
            "sale en mensajes, en la cama, en reuniones… cuando hablás demasiado pronto o demasiado tarde.",
            f"<b>Expresión {ex} · sensación.</b> Mostrás lo que creés seguro; el conflicto nace cuando lo que sentís pide otra forma y la reprimís por miedo al qué dirán.",
        ),
    )
    alma_b = _pick(
        rng,
        (
            f"<b>Alma {alm} · sensación.</b> Es lo que necesitás recibir para seguir humano: reconocimiento, ritmo, ternura o espacio… "
            "y aparece cuando skipeás eso y llamás necesidad a \"debilidad\".",
            f"<b>Alma {alm} · sensación.</b> Es hambre legítima: cuando no se cumple, no siempre llorás; a veces solo te endurecés y decís que \"estás bien\".",
        ),
    )
    persona_b = _pick(
        rng,
        (
            f"<b>Personalidad {pers} · sensación.</b> Es el piloto automático social cuando el sistema nervioso ya no da para más aristas.",
            f"<b>Personalidad {pers} · sensación.</b> Es la máscara útil con la que salís al mundo: te protege… y a veces te borra del mapa que vos querías recorrer.",
        ),
    )
    return _br(camino, expresion, alma_b, persona_b)


def compose_numerologia_sagrada_pagina(
    rng: random.Random, p: SoulProfile, nombre: str, sign: str, animal: str
) -> str:
    ps = _perfil_slug(p)
    cv, ex, alm, pers = p.camino_vida, p.expresion, p.alma, p.personalidad
    cabecera = rng.choice(
        (
            f"<b>Numerología sin discurso de manual</b><br/>"
            f"{nombre}: camino {cv}, expresión {ex}, alma {alm}, personalidad {pers}. "
            f"No son fórmula fría: son cuatro puertas del mismo corazón.",
            f"<b>Cuatro micrófonos</b><br/>"
            f"{nombre}: {cv} es tu arco largo; {ex} es cómo nombrás lo que sentís; {alm} es lo que necesitás recibir; "
            f"{pers} es lo que mostrás cuando tenés miedo.",
        )
    )
    palancas = _numerologia_cuatro_palancas_vivas(rng, cv, ex, alm, pers)
    vida = (
        f"<b>Vida real.</b> Esto se ve en banco (decisiones grandes), en salud (cuándo pedís ayuda) y en vínculos (cuánto tolerás antes de que el cuerpo te cobre con irritación, cierre o un \"basta\" que ni vos te esperabas). "
        f"Y sí: {sign} y {animal} meten presión social de comparación; tu tarea es volver a tu ritmo sin pedir perdón."
    )
    fuerza = "<b>Tu punto fuerte.</b> Cuando te escuchas de verdad, decides con más paz. No por perfección: por honestidad interna."
    limite = "<b>Pausa.</b> No compres ritmos ajenos solo para encajar: eso no es adaptación, es deuda emocional."
    accion = f"<b>Hoy.</b> {_accion_limpia(ps, 'numerologia')}."
    return _br(cabecera, palancas, vida, fuerza, limite, accion)


def compose_poder_y_sombra(
    rng: random.Random,
    p: SoulProfile,
    nombre: str,
    sign: str,
    elem: str,
    planet: str,
    shadow_frag: str,
) -> str:
    del planet
    perfil = _perfil_lineas(_perfil_slug(p))
    tono = rng.choice(("corte", "tierno"))
    inicio = (
        f"<b>Poder y sombra</b> · modo {'corte' if tono=='corte' else 'ternura firme'}<br/>"
        f"{nombre}: acá no te voy a halagar con adjetivos. Te voy a nombrar el truco que te sabotea… y el poder real que ya tenés."
    )
    wow = _linea_golpe_sombra(p, nombre)
    e = (elem or "").strip().lower()
    if e == "fuego":
        if tono == "corte":
            real = f"<b>Hecho.</b> Actuás rápido. Eso te salva… y también te mete en quilombos evitables. {shadow_frag}"
            valid = "<b>Defensa.</b> Preferís pelea a sentirte pequeña/o."
            limite = "<b>No.</b> Que te provoquen y después te culpen por reaccionar."
            accion = "<b>60s.</b> Calor en el cuerpo = pausa. Nombre del límite. Respuesta recién después."
        else:
            real = f"<b>Hecho.</b> Tenés coraje. A veces se te va el freno. {shadow_frag}"
            valid = "<b>Defensa.</b> El impulso te protege del vacío… por un rato."
            limite = "<b>No.</b> Discutir fuera del tema solo para descargar."
            accion = "<b>Práctica.</b> Una frase de necesidad + una frase de límite. Fin."
    elif e == "tierra":
        if tono == "corte":
            real = f"<b>Hecho.</b> Sostenés el mundo. Eso es adultez… hasta que es martirio con agenda. {shadow_frag}"
            valid = "<b>Defensa.</b> Si aflojás, sentís que se cae todo."
            limite = "<b>No.</b> Ser el archivo humano de problemas ajenos."
            accion = "<b>Práctica.</b> Delegación fea pero real: una tarea, un dueño, una fecha."
        else:
            real = f"<b>Hecho.</b> Sabés construir. Tu sombra es creer que descansar es traición. {shadow_frag}"
            valid = "<b>Defensa.</b> Endurecerse antes que pedir."
            limite = "<b>No.</b> Cargar lo que otros pueden sostener."
            accion = "<b>Práctica.</b> Pedí ayuda en algo chico y no la retomes."
    elif e == "aire":
        if tono == "corte":
            real = f"<b>Hecho.</b> Pensás demasiado para no sentir. {shadow_frag}"
            valid = "<b>Defensa.</b> Explicar para no quedar mal."
            limite = "<b>No.</b> Relaciones que te exigen juicio emocional eterno."
            accion = "<b>Práctica.</b> 12 palabras de límite. Silencio sostenido."
        else:
            real = f"<b>Hecho.</b> Tu mente es un instrumento brutal… cuando la usás a favor tuyo. {shadow_frag}"
            valid = "<b>Defensa.</b> Analizar para no exponerte."
            limite = "<b>No.</b> Autotribunal permanente."
            accion = "<b>Práctica.</b> Decisión con 70% de certeza y cierre."
    else:
        if tono == "corte":
            real = f"<b>Hecho.</b> Sentís mucho… y a veces pagás cuentas ajenas. {shadow_frag}"
            valid = "<b>Defensa.</b> Salvar vínculos a costa tuya."
            limite = "<b>No.</b> Culpa inducida cuando pedís reciprocidad."
            accion = "<b>Práctica.</b> No claro + alternativa concreta."
        else:
            real = f"<b>Hecho.</b> Tu sensibilidad es inteligencia emocional… si no la usás en contra tuya. {shadow_frag}"
            valid = "<b>Defensa.</b> Decir sí por miedo al abandono."
            limite = (
                "<b>No.</b> Normalizar carga injusta como \"amor\".<br/><br/>"
                "<b>Consecuencia.</b> Cuanto más lo llames con nombre bonito, más te entrenan a confundir dolor con prueba de entrega, "
                "y el vínculo se vuelve teatro de buenas intenciones con factura emocional a tu nombre.<br/><br/>"
                "<b>Impacto emocional.</b> Te quedas vacía o vacío por dentro aunque afuera \"todo esté bien\", "
                "y después culpas tu sensibilidad en vez del desequilibrio real."
            )
            accion = "<b>Práctica.</b> Sí por miedo → corregir con no + propuesta."
    directo = "<b>Verdad dura.</b> No es que no puedas: es que te entrenaron a no hacerlo."
    return _br(inicio, perfil["sombra"], directo, real, valid, limite, accion, wow)


def compose_pregunta_alma(rng: random.Random, p: SoulProfile, nombre: str, nombre_pila: str) -> str:
    np = _prim(p)
    opts = (
        f"¿Qué tendrías que dejar de sostener sola, {np}, para que tu vida deje de parecer un castigo por ser responsable?",
        f"{nombre}, si no hubiera miedo al qué dirán, ¿qué línea cruzarías hoy con amor firme y sin disculpa?",
        f"¿Qué parte de tu historia estás cargando como si fuera deuda, {np}, cuando en realidad es solo miedo a quedarte sin control?",
        f"{nombre}, ¿qué verdad pequeña podrías decir mañana que te devolviera aire sin destruir a nadie?",
        f"{np}, si hoy pudieras hablarle a tu nombre como a un ser vivo que te habita, ¿qué le pedirías perdón o qué le agradecerías primero?",
        f"¿Qué parte de vos —la que solo emerge cuando decís <i>{np}</i> con calma— necesita que dejes de negociarla por miedo a no encajar?",
        f"{nombre}: más allá del papel y del horóscopo, ¿qué promesa le harías a <i>{np}</i> para no volver a traicionarlo en lo chico?",
    )
    return _pick(rng, opts)


def compose_mensaje_personal_climax(
    rng: random.Random, p: SoulProfile, nombre: str, sign: str, elem: str
) -> str:
    perfil = _perfil_lineas(_perfil_slug(p))
    modo = rng.choice(("confrontacion", "calma", "decision", "liberacion"))
    if p.camino_vida in (1, 8):
        foco = "liderar tu vida sin convertir control en agotamiento"
        golpes = {
            "confrontacion": "Tu problema no es ser fuerte: es cargar lo que no te corresponde y llamarlo \"responsabilidad\".",
            "calma": "Podés mandar en tu vida sin mandar en la vida de todos. Eso también es liderazgo.",
            "decision": "Elegí un solo \"sí\" esta semana que valga tu fuerza… y tres \"no\" que te devuelvan tiempo.",
            "liberacion": "Soltar no es rendirse: es dejar de pagar cuentas que otros firmaron.",
        }
    elif p.camino_vida in (2, 6):
        foco = "amar sin perderte por sostener a todo el mundo"
        golpes = {
            "confrontacion": "Si para que te quieran tenés que anularte, no es amor: es contrato envenenado.",
            "calma": "Cuidar no es desaparecer. Aparecer también es un acto de amor.",
            "decision": "Hoy devolvés una responsabilidad emocional que no es tuya… con claridad, sin drama.",
            "liberacion": "Tu bondad no necesita prisión para ser real.",
        }
    elif p.camino_vida in (3, 5):
        foco = "canalizar tu energía en decisiones sostenidas y no en escapes elegantes"
        golpes = {
            "confrontacion": "No es que no puedas: es que no te permitís sostener lo que decidís.",
            "calma": "Tu libertad no necesita ruido: necesita dirección.",
            "decision": "Una decisión imperfecta hoy vale más que diez escapadas elegantes.",
            "liberacion": "Dejá de confundir movimiento con avance.",
        }
    else:
        foco = "convertir disciplina en paz interna y no en autoexigencia sin descanso"
        golpes = {
            "confrontacion": "Ser exigente está bien. Ser cruel con vos no.",
            "calma": "La disciplina madura descansa. La cruel no.",
            "decision": "Elegí un descanso real, no uno culposo.",
            "liberacion": "Podés ser seria/o sin ser castigo permanente.",
        }
    golpe_final = golpes[modo]
    aperturas = {
        "confrontacion": f"{nombre}, cierre sin maquillaje: {golpe_final}",
        "calma": f"{nombre}, cierre con aire: {golpe_final}",
        "decision": f"{nombre}, cierre con manos: {golpe_final}",
        "liberacion": f"{nombre}, cierre con peso suelto: {golpe_final}",
    }
    inicio = aperturas[modo]
    real = f"<b>Mapa.</b> {sign} + {elem}: tenés recursos enormes. La lectura te pide {foco}."
    valid = "<b>Humanidad.</b> Lo que te costó no te define como \"defectuosa/o\": te dejó pistas para elegir distinto."
    limite = "<b>Límite.</b> Respeto, claridad y reciprocidad no se renegocian por aplausos."
    sorpresa = rng.choice(
        (
            f"<b>Verdad incómoda.</b> {nombre}, a veces preferís tener la razón antes que tener paz… y eso también es miedo.",
            f"<b>Verdad incómoda.</b> {nombre}, podés leer esto perfecto y seguir igual… o podés elegir una vergüenza pequeña hoy y cambiar el rumbo.",
        )
    )
    accion = f"<b>Acción final.</b> {_accion_limpia(_perfil_slug(p), 'mensaje')}."
    cierre = f"<b>Frase para guardar.</b> {golpe_final}"
    firma = (
        "<b>Para llevar.</b> Tu nombre no es solo lo que te dieron: es lo que decides sostener cada vez que lo pronuncias con intención."
    )
    return _br(inicio, real, valid, sorpresa, limite, accion, cierre, firma, perfil["nombre"])


def compose_respira_intercalada(rng: random.Random, nombre: str) -> str:
    """Una sola frase potente para página de respiración (sin caja)."""
    opts = (
        f"{nombre}, lo sagrado no grita: late en lo cotidiano.",
        f"{nombre}, no eres fondo: eres figura.",
        f"{nombre}, tu cuerpo ya sabe lo que tu mente aún negocia.",
        "La coherencia es una forma de amor que no necesita aplauso.",
        f"{nombre}, irrepetible no es ego: es precisión.",
    )
    return _pick(rng, opts)


