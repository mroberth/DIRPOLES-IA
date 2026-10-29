import re

# Catálogo de directrices canónicas preaprobadas para el LLM externo.
# Como DIRPOLES-4 no dispone actualmente de un catálogo formal de opciones predefinidas
# para observacion_usuario y envía texto libre desde un textarea, este diccionario
# permanece como catálogo de referencia extensible para directrices institucionales formalmente autorizadas.
DIRECTRICES_CANONICAS: dict[str, str] = {}


def resolver_observacion_para_prompt(texto: str | None) -> str:
    """Resuelve la directriz autorizada para incluir en el prompt del LLM externo.

    Política de Privacidad y Cumplimiento de PII:
    - El texto libre no estructurado NO se transmite al proveedor externo de LLM,
      debido a que los filtros heurísticos no pueden garantizar la erradicación
      total de nombres propios, descripciones o datos sensibles en prosa libre.
    - Si el texto recibido coincide exactamente con una clave de directriz canónica
      en DIRECTRICES_CANONICAS, se inyecta su representación interna predefinida y
      autorizada, NUNCA el texto original del usuario.
    - Si el texto no es reconocido, es texto libre o es nulo/vacío, se omite
      completamente y se sustituye por la directriz neutral por defecto.
    """
    if not texto:
        return "Ninguna indicación adicional."

    clave = texto.strip()
    if clave in DIRECTRICES_CANONICAS:
        return DIRECTRICES_CANONICAS[clave]

    # Omisión estricta de texto libre no canónico hacia el LLM externo
    return "Ninguna indicación adicional."


def sanitizar_observacion_usuario(texto: str | None) -> str:
    """Sanea y valida la observación del usuario antes de incorporarla al prompt.

    Aplica filtros de seguridad y redacción de patrones identificables (cédulas,
    identificadores, correos, teléfonos y marcas de PII) para mitigar la fuga de datos.
    """
    if not texto or not texto.strip():
        return "Ninguna indicación adicional."

    limpio = texto.strip()[:1000]

    # 1. Eliminar etiquetas HTML o scripts
    limpio = re.sub(r"<[^>]+>", " ", limpio)

    # 2. Redactar centinelas sintéticos de prueba
    limpio = re.sub(r"SENTINEL_[A-Za-z0-9_]+", "[REDACTADO]", limpio)

    # 3. Redactar cédulas venezolanas y documentos de identidad
    limpio = re.sub(r"\b[VvEeJjGg]-?\d{5,9}\b", "[DOCUMENTO_REDACTADO]", limpio)
    limpio = re.sub(r"\b\d{1,2}\.\d{3}\.\d{3}\b", "[DOCUMENTO_REDACTADO]", limpio)
    limpio = re.sub(
        r"(?i)\b(c[eé]dula|identificaci[oó]n|ci|dni)\s*[:=]?\s*\S+",
        "[DOCUMENTO_REDACTADO]",
        limpio,
    )

    # 4. Redactar correos electrónicos
    limpio = re.sub(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[CORREO_REDACTADO]", limpio)

    # 5. Redactar números telefónicos
    limpio = re.sub(
        r"\b(\+?58|0)?[24]\d{2}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "[TELEFONO_REDACTADO]",
        limpio,
    )

    # 6. Redactar menciones etiquetadas a beneficiarios/estudiantes/pacientes
    limpio = re.sub(
        r"(?i)\b(paciente|estudiante|beneficiario|chofer|doctor|usuario)\s*[:=]?\s*([A-ZÁÉÍÓÚÑa-záéíóúñ]+(\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+){1,3})",
        r"\1 [NOMBRE_REDACTADO]",
        limpio,
    )

    # 7. Redactar diagnósticos y tratamientos individuales en observaciones
    limpio = re.sub(
        r"(?i)\b(diagn[oó]stico|patolog[ií]a|tratamiento|enfermedad|medicamento)\s*[:=]?\s*([^,.\n]+)",
        r"\1 [CLINICO_REDACTADO]",
        limpio,
    )

    return " ".join(limpio.split())
