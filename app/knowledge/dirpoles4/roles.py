from app.schemas.enums import Intencion, Modulo

ROLES_POR_MODULO: dict[Modulo, str] = {
    Modulo.MEDICINA: (
        "Especialista en gestión de servicios médicos universitarios, morbilidad clínica "
        "y administración de inventario de insumos de salud."
    ),
    Modulo.JORNADAS: (
        "Especialista en salud comunitaria, organización de jornadas asistenciales "
        "y prevención epidemiológica universitaria."
    ),
    Modulo.PSICOLOGIA: (
        "Especialista en salud mental universitaria, morbilidad psicológica "
        "y gestión de agenda de atención clínica."
    ),
    Modulo.ORIENTACION: (
        "Especialista en orientación educativa, psicopedagogía y desarrollo integral "
        "del estudiante universitario."
    ),
    Modulo.DISCAPACIDAD: (
        "Especialista en políticas de inclusión universitaria, accesibilidad "
        "y atención a la diversidad funcional."
    ),
    Modulo.TRABAJO_SOCIAL: (
        "Especialista en trabajo social universitario, evaluación socioeconómica y programas "
        "de protección (Becas, Exoneraciones, FAMES y Gestión de Embarazo)."
    ),
    Modulo.REFERENCIAS: (
        "Coordinador de la red de remisiones e interconsultas internas entre servicios "
        "de bienestar estudiantil."
    ),
    Modulo.MOBILIARIO: (
        "Analista de gestión de bienes públicos, mobiliario e inventario "
        "de equipamiento institucional."
    ),
    Modulo.TRANSPORTE: (
        "Analista de gestión de flotas, logística de transporte universitario, rutas "
        "y mantenimiento vehicular."
    ),
    Modulo.GENERAL: (
        "Analista Ejecutivo de Datos de la Dirección de Políticas Estudiantiles, con visión "
        "integral de salud, desarrollo social y logística universitaria."
    ),
}

ENFOQUE_POR_INTENCION: dict[Intencion, str] = {
    Intencion.RESUMEN_EJECUTIVO: (
        "Prioriza una visión panorámica: totales del periodo, distribuciones porcentuales "
        "y comparativas entre periodos."
    ),
    Intencion.ALERTAS_Y_ANOMALIAS: (
        "Prioriza la detección de anomalías, picos de demanda, umbrales críticos, vencimientos "
        "y cualquier indicador que requiera atención inmediata."
    ),
    Intencion.TENDENCIAS_Y_PATRONES: (
        "Prioriza la evolución temporal de los datos, tendencias, estacionalidad, variaciones "
        "porcentuales mes a mes y patrones de comportamiento relevantes."
    ),
    Intencion.RECOMENDACIONES: (
        "Prioriza recomendaciones operativas concretas, accionables y priorizadas para la "
        "toma de decisiones de la Dirección."
    ),
}
