"""
Estados posibles del pedido (flujo pago → PDF digital → impresión/envío opcional).

Estos valores se guardan en SQLite en la columna `estado`. Sirven para integrar
luego el generador PDF real y el envío por correo sin ambigüedades.
"""

from typing import Final, Tuple

# Valor inicial al crear un pedido desde el formulario público
ESTADO_PENDIENTE_PAGO: Final[str] = "pendiente_pago"
ESTADO_PAGADO: Final[str] = "pagado"
ESTADO_GENERANDO_CONTENIDO: Final[str] = "generando_contenido"
ESTADO_REPARANDO_JSON: Final[str] = "reparando_json"
ESTADO_COMPLETANDO_SECCIONES: Final[str] = "completando_secciones"
ESTADO_GENERANDO_PDF: Final[str] = "generando_pdf"
ESTADO_SUBIENDO_DRIVE: Final[str] = "subiendo_drive"
ESTADO_ERROR_OPENAI: Final[str] = "error_openai"
ESTADO_ERROR_JSON: Final[str] = "error_json"
ESTADO_ERROR_PDF: Final[str] = "error_pdf"
ESTADO_ERROR_DRIVE: Final[str] = "error_drive"
ESTADO_ERROR_EMAIL: Final[str] = "error_email"
ESTADO_ERROR_GENERACION: Final[str] = "error_generacion"
ESTADO_PDF_GENERADO: Final[str] = "pdf_generado"
ESTADO_PDF_GENERADO_PENDIENTE_DE_LINK: Final[str] = "pdf_generado_pendiente_de_link"
ESTADO_ENVIANDO_EMAIL: Final[str] = "enviando_email"
ESTADO_PDF_ENTREGADO: Final[str] = "pdf_entregado"
ESTADO_PENDIENTE_IMPRESION: Final[str] = "pendiente_impresion"
ESTADO_IMPRESO: Final[str] = "impreso"
ESTADO_ENVIADO: Final[str] = "enviado"
ESTADO_ENTREGADO: Final[str] = "entregado"
ESTADO_ERROR_ENVIO: Final[str] = "error_envio"
ESTADO_COMPLETADO: Final[str] = "completado"
ESTADO_REVISION_MANUAL: Final[str] = "revision_manual"
ESTADO_NEEDS_ADMIN_REVIEW: Final[str] = "needs_admin_review"

# Orden legible para desplegables en admin (tu flujo de negocio)
ORDER_STATES: Tuple[str, ...] = (
    ESTADO_PENDIENTE_PAGO,
    ESTADO_PAGADO,
    ESTADO_GENERANDO_CONTENIDO,
    ESTADO_REPARANDO_JSON,
    ESTADO_COMPLETANDO_SECCIONES,
    ESTADO_GENERANDO_PDF,
    ESTADO_SUBIENDO_DRIVE,
    ESTADO_ERROR_OPENAI,
    ESTADO_ERROR_JSON,
    ESTADO_ERROR_PDF,
    ESTADO_ERROR_DRIVE,
    ESTADO_ERROR_EMAIL,
    ESTADO_ERROR_GENERACION,
    ESTADO_PDF_GENERADO,
    ESTADO_PDF_GENERADO_PENDIENTE_DE_LINK,
    ESTADO_ENVIANDO_EMAIL,
    ESTADO_PDF_ENTREGADO,
    ESTADO_PENDIENTE_IMPRESION,
    ESTADO_IMPRESO,
    ESTADO_ENVIADO,
    ESTADO_ENTREGADO,
    ESTADO_ERROR_ENVIO,
    ESTADO_COMPLETADO,
    ESTADO_REVISION_MANUAL,
    ESTADO_NEEDS_ADMIN_REVIEW,
)

ORDER_STATE_LABELS: dict[str, str] = {
    ESTADO_PENDIENTE_PAGO: "Pendiente de pago",
    ESTADO_PAGADO: "Pagado",
    ESTADO_GENERANDO_CONTENIDO: "Generando contenido",
    ESTADO_REPARANDO_JSON: "Reparando JSON",
    ESTADO_COMPLETANDO_SECCIONES: "Completando secciones",
    ESTADO_GENERANDO_PDF: "Generando PDF",
    ESTADO_SUBIENDO_DRIVE: "Subiendo a Drive",
    ESTADO_ERROR_OPENAI: "Error de OpenAI",
    ESTADO_ERROR_JSON: "Error de JSON",
    ESTADO_ERROR_PDF: "Error al generar PDF",
    ESTADO_ERROR_DRIVE: "Error de Drive",
    ESTADO_ERROR_EMAIL: "Error de email",
    ESTADO_ERROR_GENERACION: "Error al generar PDF",
    ESTADO_PDF_GENERADO: "PDF generado",
    ESTADO_PDF_GENERADO_PENDIENTE_DE_LINK: "PDF generado, enlace pendiente",
    ESTADO_ENVIANDO_EMAIL: "Enviando email",
    ESTADO_PDF_ENTREGADO: "PDF entregado",
    ESTADO_PENDIENTE_IMPRESION: "Pendiente de impresión",
    ESTADO_IMPRESO: "Impreso",
    ESTADO_ENVIADO: "Enviado",
    ESTADO_ENTREGADO: "Entregado",
    ESTADO_ERROR_ENVIO: "Error al enviar email",
    ESTADO_COMPLETADO: "Completado",
    ESTADO_REVISION_MANUAL: "Revisión manual",
    ESTADO_NEEDS_ADMIN_REVIEW: "Necesita revisión admin",
}


def estado_valido(valor: str) -> bool:
    """True si el string es uno de los estados permitidos."""
    return valor in ORDER_STATES


def etiqueta_estado(valor: str) -> str:
    """Etiqueta humana para mostrar en la interfaz."""
    return ORDER_STATE_LABELS.get(valor, valor)
