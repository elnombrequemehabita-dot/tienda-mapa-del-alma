"""
Estados posibles del pedido (flujo pago → PDF → email → completado).

Estos valores se guardan en SQLite en la columna `estado`. Sirven para integrar
luego el generador PDF real y el envío por correo sin ambigüedades.
"""

from typing import Final, Tuple

# Valor inicial al crear un pedido desde el formulario público
ESTADO_PENDIENTE_PAGO: Final[str] = "pendiente_pago"
ESTADO_PAGADO: Final[str] = "pagado"
ESTADO_GENERANDO_PDF: Final[str] = "generando_pdf"
ESTADO_ERROR_GENERACION: Final[str] = "error_generacion"
ESTADO_PDF_GENERADO: Final[str] = "pdf_generado"
ESTADO_ENVIANDO_EMAIL: Final[str] = "enviando_email"
ESTADO_ERROR_ENVIO: Final[str] = "error_envio"
ESTADO_COMPLETADO: Final[str] = "completado"
ESTADO_REVISION_MANUAL: Final[str] = "revision_manual"

# Orden legible para desplegables en admin (tu flujo de negocio)
ORDER_STATES: Tuple[str, ...] = (
    ESTADO_PENDIENTE_PAGO,
    ESTADO_PAGADO,
    ESTADO_GENERANDO_PDF,
    ESTADO_ERROR_GENERACION,
    ESTADO_PDF_GENERADO,
    ESTADO_ENVIANDO_EMAIL,
    ESTADO_ERROR_ENVIO,
    ESTADO_COMPLETADO,
    ESTADO_REVISION_MANUAL,
)

ORDER_STATE_LABELS: dict[str, str] = {
    ESTADO_PENDIENTE_PAGO: "Pendiente de pago",
    ESTADO_PAGADO: "Pagado",
    ESTADO_GENERANDO_PDF: "Generando PDF",
    ESTADO_ERROR_GENERACION: "Error al generar PDF",
    ESTADO_PDF_GENERADO: "PDF generado",
    ESTADO_ENVIANDO_EMAIL: "Enviando email",
    ESTADO_ERROR_ENVIO: "Error al enviar email",
    ESTADO_COMPLETADO: "Completado",
    ESTADO_REVISION_MANUAL: "Revisión manual",
}


def estado_valido(valor: str) -> bool:
    """True si el string es uno de los estados permitidos."""
    return valor in ORDER_STATES


def etiqueta_estado(valor: str) -> str:
    """Etiqueta humana para mostrar en la interfaz."""
    return ORDER_STATE_LABELS.get(valor, valor)
