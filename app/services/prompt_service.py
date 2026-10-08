import json
from typing import Any

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


def construir_system_prompt(modulo: Modulo) -> str:
    rol = ROLES_POR_MODULO[modulo]
    return (
        f"Eres un {rol} para la UPTAEB.\n"
        "Tu objetivo es redactar un informe claro, profesional, riguroso y formal basado "
        "EXCLUSIVAMENTE en los datos estadísticos procesados que te son suministrados por la "
        "capa analítica en Pandas.\n"
        "Debes emplear la terminología técnica adecuada para la naturaleza de este módulo y "
        "responder en formato Markdown limpio usando encabezados, listas con viñetas y negritas "
        "para resaltar métricas clave.\n"
        "No inventes cifras: si un dato no aparece en los datos procesados, no lo menciones."
    )


def _json_resumen(resumen: dict[str, Any]) -> str:
    return json.dumps(resumen, ensure_ascii=False, indent=1, default=str)


def construir_user_prompt(
    modulo: Modulo,
    intencion: Intencion,
    resumen: dict[str, Any],
    observacion_usuario: str | None,
) -> str:
    periodo = resumen.get("periodo", {}) or {}
    fecha_inicio = periodo.get("fecha_inicio") or "inicio de los registros"
    fecha_fin = periodo.get("fecha_fin") or "la fecha actual"
    observacion = (
        observacion_usuario.strip() if observacion_usuario else "Ninguna indicación adicional."
    )
    enfoque = ENFOQUE_POR_INTENCION[intencion]
    return (
        f"Módulo Analizado: {modulo.value}\n"
        f"Intención del Informe: {intencion.value}\n"
        f"Periodo de Análisis: {fecha_inicio} a {fecha_fin}\n"
        f"Enfoque solicitado: {enfoque}\n\n"
        "DATOS PROCESADOS (Métricas, Agregaciones y Alertas detectadas por Pandas):\n"
        f"{_json_resumen(resumen)}\n\n"
        "INSTRUCCIONES ADICIONALES DEL USUARIO:\n"
        f"{observacion}\n\n"
        "Estructura requerida para la respuesta en Markdown:\n"
        "1. Resumen Ejecutivo\n"
        "2. Hallazgos Clave y Puntos Críticos\n"
        "3. Recomendaciones Operativas para la Toma de Decisiones"
    )


def construir_prompts(
    modulo: Modulo,
    intencion: Intencion,
    resumen: dict[str, Any],
    observacion_usuario: str | None,
) -> tuple[str, str]:
    return (
        construir_system_prompt(modulo),
        construir_user_prompt(modulo, intencion, resumen, observacion_usuario),
    )
