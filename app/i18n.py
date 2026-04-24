from __future__ import annotations

DEFAULT_LANG = "es"
SUPPORTED_LANGS = ("es",)

LANG_LABELS = {
    "es": "Español",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "site.name": {
        "es": "El Nombre Que Me Habita",
        "en": "The Name That Lives In Me",
        "pt": "O Nome Que Habita Em Mim",
    },
    "nav.home": {"es": "Inicio", "en": "Home", "pt": "Início"},
    "nav.reviews": {"es": "Reseñas", "en": "Reviews", "pt": "Avaliações"},
    "nav.cta": {
        "es": "Quiero descubrir mi mapa",
        "en": "I want to discover my map",
        "pt": "Quero descobrir meu mapa",
    },
    "nav.lang_label": {"es": "Idioma", "en": "Language", "pt": "Idioma"},
    "ticker.top": {
        "es": "Mapa del Alma personalizado · Pago seguro · Entrega digital por correo · Revisa Spam/Promociones si no lo encuentras",
        "en": "Personalized Soul Map · Secure payment · Digital delivery by email · Check Spam/Promotions if you cannot find it",
        "pt": "Mapa da Alma personalizado · Pagamento seguro · Entrega digital por e-mail · Verifique Spam/Promoções se não encontrar",
    },
    "ticker.bottom": {
        "es": "Más de 20 páginas personalizadas · Código de confirmación en tu pedido · Soporte por correo · Experiencia premium",
        "en": "20+ personalized pages · Confirmation code in your order · Email support · Premium experience",
        "pt": "Mais de 20 páginas personalizadas · Código de confirmação no seu pedido · Suporte por e-mail · Experiência premium",
    },
    "footer.product": {
        "es": "Producto digital personalizado · Mapa del Alma",
        "en": "Personalized digital product · Soul Map",
        "pt": "Produto digital personalizado · Mapa da Alma",
    },
    "index.title": {
        "es": "Inicio · El Nombre Que Me Habita",
        "en": "Home · The Name That Lives In Me",
        "pt": "Início · O Nome Que Habita Em Mim",
    },
    "index.hero.badge": {
        "es": "Experiencia premium personalizada",
        "en": "Premium personalized experience",
        "pt": "Experiência premium personalizada",
    },
    "index.hero.title": {
        "es": "No es solo tu nombre: es la historia emocional que llevas dentro",
        "en": "It is not just your name: it is the emotional story you carry inside",
        "pt": "Não é apenas o seu nome: é a história emocional que você carrega dentro de si",
    },
    "index.hero.subline": {
        "es": "Recibe un Mapa del Alma único (más de 20 páginas en PDF, con extensión variable según cada persona) para comprender tu esencia, reconectar contigo y regalarte una mirada profunda que no encontrarás en ningún otro lugar.",
        "en": "Receive a unique Soul Map (20+ PDF pages, with variable length for each person) to understand your essence, reconnect with yourself, and gift yourself a deep perspective you will not find anywhere else.",
        "pt": "Receba um Mapa da Alma único (mais de 20 páginas em PDF, com extensão variável para cada pessoa) para compreender sua essência, reconectar-se consigo e se presentear com um olhar profundo que você não encontrará em nenhum outro lugar.",
    },
    "index.hero.price.name": {
        "es": "Mapa del Alma personalizado",
        "en": "Personalized Soul Map",
        "pt": "Mapa da Alma personalizado",
    },
    "index.hero.price.delivery": {
        "es": "Entrega digital en 24–48 horas",
        "en": "Digital delivery in 24-48 hours",
        "pt": "Entrega digital em 24-48 horas",
    },
    "index.hero.benefit1": {"es": "100% personalizado", "en": "100% personalized", "pt": "100% personalizado"},
    "index.hero.benefit2": {"es": "Entrega digital por email", "en": "Digital delivery by email", "pt": "Entrega digital por e-mail"},
    "index.hero.benefit3": {"es": "Diseño premium", "en": "Premium design", "pt": "Design premium"},
    "index.hero.cta.primary": {
        "es": "Quiero descubrir lo que mi nombre revela",
        "en": "I want to discover what my name reveals",
        "pt": "Quero descobrir o que meu nome revela",
    },
    "index.hero.cta.secondary": {
        "es": "Ver cómo se ve por dentro",
        "en": "See how it looks inside",
        "pt": "Ver como é por dentro",
    },
    "index.hero.urgency": {
        "es": "Creación personalizada. Cupos limitados por día.",
        "en": "Personalized creation. Limited slots per day.",
        "pt": "Criação personalizada. Vagas limitadas por dia.",
    },
    "index.delivery.pin": {
        "es": "Recibirás tu Mapa del Alma en formato PDF directamente en tu correo.",
        "en": "You will receive your Soul Map in PDF format directly in your email.",
        "pt": "Você receberá seu Mapa da Alma em formato PDF diretamente no seu e-mail.",
    },
    "index.how.title": {"es": "¿Cómo funciona?", "en": "How does it work?", "pt": "Como funciona?"},
    "index.how.lead": {
        "es": "Todo el proceso es digital: pedido, creación personalizada y envío del PDF a tu email.",
        "en": "The whole process is digital: order, personalized creation, and PDF delivery to your email.",
        "pt": "Todo o processo é digital: pedido, criação personalizada e envio do PDF para o seu e-mail.",
    },
    "index.how.step1": {
        "es": "Completa tu pedido con tus datos",
        "en": "Complete your order with your details",
        "pt": "Preencha seu pedido com seus dados",
    },
    "index.how.step2": {
        "es": "Creamos tu Mapa del Alma personalizado",
        "en": "We create your personalized Soul Map",
        "pt": "Criamos seu Mapa da Alma personalizado",
    },
    "index.how.step3": {
        "es": "Lo recibes en tu correo en formato PDF",
        "en": "You receive it in your email as PDF",
        "pt": "Você recebe no seu e-mail em formato PDF",
    },
    "index.how.step4": {
        "es": "Puedes guardarlo, imprimirlo o regalarlo",
        "en": "You can save it, print it, or gift it",
        "pt": "Você pode salvar, imprimir ou presentear",
    },
    "index.audience.title": {
        "es": "Esto no es para todo el mundo",
        "en": "This is not for everyone",
        "pt": "Isto não é para todo mundo",
    },
    "index.audience.lead": {
        "es": "Este proceso está hecho para personas que valoran lo emocional, lo simbólico y lo profundamente personal.",
        "en": "This process is designed for people who value the emotional, symbolic, and deeply personal.",
        "pt": "Este processo foi feito para pessoas que valorizam o emocional, o simbólico e o profundamente pessoal.",
    },
    "index.audience.not_for": {"es": "No es para ti si...", "en": "It is not for you if...", "pt": "Não é para você se..."},
    "index.audience.for_you": {"es": "Sí es para ti si...", "en": "It is for you if...", "pt": "É para você se..."},
    "index.audience.n1": {
        "es": "Buscas una lectura rápida sin profundidad emocional",
        "en": "You are looking for a quick read without emotional depth",
        "pt": "Você procura uma leitura rápida sem profundidade emocional",
    },
    "index.audience.n2": {
        "es": "Solo quieres comprar algo y ya",
        "en": "You only want to buy something and move on",
        "pt": "Você só quer comprar algo e pronto",
    },
    "index.audience.n3": {
        "es": "No te interesa explorar tu historia interior",
        "en": "You are not interested in exploring your inner story",
        "pt": "Você não tem interesse em explorar sua história interior",
    },
    "index.audience.y1": {
        "es": "Quieres comprenderte desde una mirada más íntima",
        "en": "You want to understand yourself from a more intimate perspective",
        "pt": "Você quer se compreender a partir de um olhar mais íntimo",
    },
    "index.audience.y2": {
        "es": "Sientes que tu nombre tiene un mensaje para ti",
        "en": "You feel your name has a message for you",
        "pt": "Você sente que seu nome tem uma mensagem para você",
    },
    "index.audience.y3": {
        "es": "Deseas regalar algo verdaderamente significativo",
        "en": "You want to give something truly meaningful",
        "pt": "Você deseja presentear algo verdadeiramente significativo",
    },
    "index.preview.title": {
        "es": "Así se ve por dentro tu Mapa del Alma",
        "en": "This is how your Soul Map looks inside",
        "pt": "Assim é por dentro o seu Mapa da Alma",
    },
    "index.preview.lead": {
        "es": "Un diseño limpio, sensible y elegante para que cada página se sienta como una experiencia. Explora ejemplos reales de estilo y estructura.",
        "en": "A clean, sensitive, and elegant design so each page feels like an experience. Explore real examples of style and structure.",
        "pt": "Um design limpo, sensível e elegante para que cada página pareça uma experiência. Explore exemplos reais de estilo e estrutura.",
    },
    "index.preview.disclaimer": {
        "es": "Ejemplo ilustrativo. El contenido final se adapta a cada persona.",
        "en": "Illustrative example. Final content is adapted to each person.",
        "pt": "Exemplo ilustrativo. O conteúdo final se adapta a cada pessoa.",
    },
    "index.preview.prev": {"es": "Anterior", "en": "Previous", "pt": "Anterior"},
    "index.preview.next": {"es": "Siguiente", "en": "Next", "pt": "Próximo"},
    "index.preview.what": {"es": "Qué estás viendo", "en": "What you are seeing", "pt": "O que você está vendo"},
    "index.preview.thumb1": {"es": "Portada personalizada", "en": "Personalized cover", "pt": "Capa personalizada"},
    "index.preview.thumb2": {"es": "Interpretación inicial", "en": "Initial interpretation", "pt": "Interpretação inicial"},
    "index.preview.thumb3": {"es": "Lectura simbólica", "en": "Symbolic reading", "pt": "Leitura simbólica"},
    "index.preview.thumb4": {"es": "Cierre y propósito", "en": "Closure and purpose", "pt": "Fechamento e propósito"},
    "index.mockup.title": {
        "es": "Así se vería tu Mapa del Alma en formato libro",
        "en": "This is how your Soul Map would look in book format",
        "pt": "Assim seu Mapa da Alma ficaria em formato de livro",
    },
    "index.mockup.lead": {
        "es": "Este es un ejemplo visual del diseño aplicado a formato físico. Actualmente el producto se entrega en formato digital (PDF).",
        "en": "This is a visual example of the design in physical format. Currently, the product is delivered digitally (PDF).",
        "pt": "Este é um exemplo visual do design aplicado ao formato físico. Atualmente, o produto é entregue em formato digital (PDF).",
    },
    "index.mockup.tagline": {
        "es": "Un diseño pensado para sentirse como un libro real, creado exclusivamente para ti.",
        "en": "A design made to feel like a real book, created exclusively for you.",
        "pt": "Um design pensado para parecer um livro real, criado exclusivamente para você.",
    },
    "index.mockup.digital": {
        "es": "Producto digital. No incluye versión impresa.",
        "en": "Digital product. No printed version included.",
        "pt": "Produto digital. Não inclui versão impressa.",
    },
    "index.includes.title": {
        "es": "¿Qué incluye tu Mapa del Alma?",
        "en": "What does your Soul Map include?",
        "pt": "O que inclui o seu Mapa da Alma?",
    },
    "index.includes.i1": {
        "es": "Significado profundo de tu nombre",
        "en": "Deep meaning of your name",
        "pt": "Significado profundo do seu nome",
    },
    "index.includes.i2": {"es": "Energía y esencia personal", "en": "Personal energy and essence", "pt": "Energia e essência pessoal"},
    "index.includes.i3": {"es": "Numerología", "en": "Numerology", "pt": "Numerologia"},
    "index.includes.i4": {"es": "Interpretación simbólica", "en": "Symbolic interpretation", "pt": "Interpretação simbólica"},
    "index.includes.i5": {"es": "Propósito y camino personal", "en": "Purpose and personal path", "pt": "Propósito e caminho pessoal"},
    "index.includes.i6": {"es": "Diseño premium en PDF", "en": "Premium PDF design", "pt": "Design premium em PDF"},
    "index.includes.i7": {"es": "Entrega digital por email", "en": "Digital delivery by email", "pt": "Entrega digital por e-mail"},
    "index.includes.i8": {
        "es": "Más de 20 páginas personalizadas (puede variar según cada persona)",
        "en": "20+ personalized pages (may vary for each person)",
        "pt": "Mais de 20 páginas personalizadas (pode variar para cada pessoa)",
    },
    "index.reviews.title": {
        "es": "Lo que dicen quienes ya lo tienen",
        "en": "What people who already have it say",
        "pt": "O que dizem quem já o tem",
    },
    "index.reviews.empty": {
        "es": "Aún no hay reseñas publicadas. En cuanto revisemos las primeras, aparecerán aquí.",
        "en": "There are no published reviews yet. As soon as we review the first ones, they will appear here.",
        "pt": "Ainda não há avaliações publicadas. Assim que revisarmos as primeiras, elas aparecerão aqui.",
    },
    "index.reviews.lead": {
        "es": "Reseñas verificadas de clientes que ya recibieron su Mapa del Alma.",
        "en": "Verified reviews from clients who already received their Soul Map.",
        "pt": "Avaliações verificadas de clientes que já receberam seu Mapa da Alma.",
    },
    "index.reviews.verified_order": {
        "es": "Pedido verificado",
        "en": "Verified order",
        "pt": "Pedido verificado",
    },
    "index.quotes.title": {
        "es": "Frases que resumen lo que se siente",
        "en": "Quotes that summarize what it feels like",
        "pt": "Frases que resumem o que se sente",
    },
    "index.quotes.q1": {
        "es": "\"Sentí que alguien puso en palabras algo que yo no sabía explicar.\"",
        "en": "\"I felt like someone put into words what I could not explain.\"",
        "pt": "\"Senti que alguém colocou em palavras algo que eu não sabia explicar.\"",
    },
    "index.quotes.q2": {
        "es": "\"No fue un archivo más en mi correo, fue un regalo para volver a mí.\"",
        "en": "\"It was not just another file in my inbox; it was a gift to reconnect with myself.\"",
        "pt": "\"Não foi apenas mais um arquivo no meu e-mail; foi um presente para voltar a mim.\"",
    },
    "index.quotes.q3": {
        "es": "\"Lo compré por curiosidad y terminé llorando con varias páginas.\"",
        "en": "\"I bought it out of curiosity and ended up crying with several pages.\"",
        "pt": "\"Comprei por curiosidade e terminei chorando com várias páginas.\"",
    },
    "index.final.cta": {
        "es": "Sí, quiero empezar mi Mapa del Alma",
        "en": "Yes, I want to start my Soul Map",
        "pt": "Sim, quero começar meu Mapa da Alma",
    },
    "index.final.text": {
        "es": "Tal vez este sea el momento de leer tu historia con otros ojos.",
        "en": "Maybe this is the moment to read your story with new eyes.",
        "pt": "Talvez este seja o momento de ler sua história com novos olhos.",
    },
    "index.final.subtext": {
        "es": "Si sentiste que este mensaje te habló, no lo dejes pasar. Tu Mapa del Alma se crea para ti, no para alguien más.",
        "en": "If this message spoke to you, do not let it pass. Your Soul Map is created for you, not for someone else.",
        "pt": "Se você sentiu que esta mensagem falou com você, não deixe passar. Seu Mapa da Alma é criado para você, e não para outra pessoa.",
    },
    "index.final.trust": {
        "es": "Pago seguro. Entrega digital. Sin envío físico.",
        "en": "Secure payment. Digital delivery. No physical shipping.",
        "pt": "Pagamento seguro. Entrega digital. Sem envio físico.",
    },
    "pedido.title": {"es": "Pedido · Mapa del Alma", "en": "Order · Soul Map", "pt": "Pedido · Mapa da Alma"},
    "pedido.header": {"es": "Tu pedido", "en": "Your order", "pt": "Seu pedido"},
    "pedido.intro": {
        "es": "Solo unos datos esenciales. Te responderemos por correo.",
        "en": "Only a few essential details. We will reply by email.",
        "pt": "Apenas alguns dados essenciais. Responderemos por e-mail.",
    },
    "pedido.name": {"es": "Nombre", "en": "First name", "pt": "Nome"},
    "pedido.lastname": {"es": "Apellidos", "en": "Last name", "pt": "Sobrenome"},
    "pedido.email": {"es": "Correo electrónico", "en": "Email", "pt": "E-mail"},
    "pedido.email_confirm": {"es": "Confirmar correo", "en": "Confirm email", "pt": "Confirmar e-mail"},
    "pedido.birthdate": {"es": "Fecha de nacimiento", "en": "Birth date", "pt": "Data de nascimento"},
    "pedido.optional": {"es": "(opcional)", "en": "(optional)", "pt": "(opcional)"},
    "pedido.form_of_address": {
        "es": "¿Cómo quieres que nos dirijamos a ti?",
        "en": "How would you like us to address you?",
        "pt": "Como você prefere que nos dirijamos a você?",
    },
    "pedido.form_of_address_optional": {
        "es": "Opcional — elige si quieres",
        "en": "Optional - choose if you want",
        "pt": "Opcional - escolha se quiser",
    },
    "pedido.confirm_data": {
        "es": "Confirmo que los datos son correctos y entiendo que este formulario es el primer paso del pedido de mi Mapa del Alma en El Nombre Que Me Habita. Autorizo el uso de esta información para la creación de mi contenido personalizado.",
        "en": "I confirm the data is correct and understand this form is the first step of my Soul Map order at The Name That Lives In Me. I authorize the use of this information to create my personalized content.",
        "pt": "Confirmo que os dados estão corretos e entendo que este formulário é o primeiro passo do meu pedido de Mapa da Alma em O Nome Que Habita Em Mim. Autorizo o uso dessas informações para criar meu conteúdo personalizado.",
    },
    "pedido.confirm_digital": {
        "es": "Entiendo que se trata de un producto digital personalizado, por lo que no se aceptan cambios, cancelaciones ni reembolsos una vez confirmado el pedido e iniciado el proceso de creación.",
        "en": "I understand this is a personalized digital product, so changes, cancellations, or refunds are not accepted once the order is confirmed and creation has started.",
        "pt": "Entendo que se trata de um produto digital personalizado, portanto não são aceitas alterações, cancelamentos ou reembolsos após a confirmação do pedido e início do processo de criação.",
    },
    "pedido.submit": {"es": "Enviar pedido", "en": "Submit order", "pt": "Enviar pedido"},
    "pedido.back": {"es": "Volver al inicio", "en": "Back to home", "pt": "Voltar ao início"},
    "gracias.title": {"es": "Gracias · El Nombre Que Me Habita", "en": "Thank You · The Name That Lives In Me", "pt": "Obrigado · O Nome Que Habita Em Mim"},
    "gracias.confirmed": {"es": "Pedido confirmado", "en": "Order confirmed", "pt": "Pedido confirmado"},
    "gracias.header": {"es": "Gracias por tu pedido", "en": "Thank you for your order", "pt": "Obrigado pelo seu pedido"},
    "gracias.msg": {
        "es": "Hemos registrado tu solicitud de Mapa del Alma. Si el pago queda confirmado, procesaremos tu pedido y recibirás el PDF en tu correo.",
        "en": "We have registered your Soul Map request. If payment is confirmed, we will process your order and you will receive the PDF by email.",
        "pt": "Registramos sua solicitação do Mapa da Alma. Se o pagamento for confirmado, processaremos seu pedido e você receberá o PDF por e-mail.",
    },
    "gracias.ref": {"es": "Referencia interna del pedido", "en": "Internal order reference", "pt": "Referência interna do pedido"},
    "gracias.code": {"es": "Código de confirmación", "en": "Confirmation code", "pt": "Código de confirmação"},
    "gracias.home": {"es": "Volver al inicio", "en": "Back to home", "pt": "Voltar ao início"},
    "gracias.new_order": {"es": "Hacer otro pedido", "en": "Place another order", "pt": "Fazer outro pedido"},
}


def normalize_lang(value: str | None) -> str:
    raw = (value or "").strip().lower()
    return DEFAULT_LANG if raw != DEFAULT_LANG else raw


def get_current_lang() -> str:
    return DEFAULT_LANG


def set_current_lang(lang: str) -> str:
    return normalize_lang(lang)


def tr(key: str, **kwargs) -> str:
    lang = get_current_lang()
    entry = TRANSLATIONS.get(key)
    if not entry:
        text = key
    else:
        text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
