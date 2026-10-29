import json
import time
from typing import Any

from app.knowledge.dirpoles4.directrices import sanitizar_observacion_usuario
from app.schemas.response import MetaDTO
from app.schemas.v2 import AnalisisRequestV2DTO, AnalisisResponseV2DTO
from app.services import gemini_service


def _calcular_distribuciones(
    distribuciones_raw: dict[str, list[Any]],
    umbral_concentracion: float,
    alertas: list[dict[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    resultado: dict[str, list[dict[str, Any]]] = {}

    for clave, items in distribuciones_raw.items():
        total_categoria = sum(it.cantidad for it in items)
        lista_saneada: list[dict[str, Any]] = []

        for it in items:
            pct = (
                round((it.cantidad / total_categoria) * 100.0, 2)
                if total_categoria > 0 and it.porcentaje is None
                else (it.porcentaje or 0.0)
            )
            lista_saneada.append(
                {
                    "valor": it.valor,
                    "cantidad": it.cantidad,
                    "porcentaje": pct,
                }
            )
            if pct >= umbral_concentracion and total_categoria > 0:
                alertas.append(
                    {
                        "nivel": "advertencia",
                        "mensaje": (
                            f"La categoría '{it.valor}' en la distribución '{clave}' "
                            f"concentra el {pct}% del total ({it.cantidad}/{total_categoria})."
                        ),
                    }
                )

        resultado[clave] = lista_saneada

    return resultado


def _calcular_comparativa_serie(
    serie: list[Any],
    umbral_variacion: float,
    alertas: list[dict[str, str]],
) -> dict[str, Any] | None:
    if len(serie) < 2:
        return None

    penultimo = serie[-2]
    ultimo = serie[-1]
    cant_anterior = penultimo.cantidad
    cant_actual = ultimo.cantidad

    if cant_anterior > 0:
        variacion_pct = round(((cant_actual - cant_anterior) / cant_anterior) * 100.0, 1)
    else:
        variacion_pct = 100.0 if cant_actual > 0 else 0.0

    if abs(variacion_pct) >= umbral_variacion:
        direccion = "aumento" if variacion_pct > 0 else "disminución"
        alertas.append(
            {
                "nivel": "advertencia" if abs(variacion_pct) < 50.0 else "critico",
                "mensaje": (
                    f"Se detectó un {direccion} del {abs(variacion_pct)}% en la actividad "
                    f"({penultimo.mes}: {cant_anterior} → {ultimo.mes}: {cant_actual})."
                ),
            }
        )

    return {
        "mes_anterior": {"mes": penultimo.mes, "total": cant_anterior},
        "mes_actual": {"mes": ultimo.mes, "total": cant_actual},
        "variacion_pct": variacion_pct,
    }


def ejecutar_analisis_v2(peticion: AnalisisRequestV2DTO) -> AnalisisResponseV2DTO:
    """Ejecuta el pipeline analítico universal en modo Push (sin base de datos)."""
    inicio = time.perf_counter()

    alertas: list[dict[str, str]] = [
        {"nivel": a.nivel, "mensaje": a.mensaje} for a in peticion.metricas.alertas
    ]

    distribuciones = _calcular_distribuciones(
        peticion.metricas.distribuciones,
        peticion.reglas_analiticas.umbral_concentracion_pct,
        alertas,
    )

    comparativa = _calcular_comparativa_serie(
        peticion.metricas.serie_mensual,
        peticion.reglas_analiticas.umbral_variacion_mensual_pct,
        alertas,
    )

    totales_calc = dict(peticion.metricas.totales)
    registros_procesados = sum(totales_calc.values())
    if registros_procesados == 0 and distribuciones:
        primer_dist = next(iter(distribuciones.values()))
        registros_procesados = sum(d["cantidad"] for d in primer_dist)

    resumen: dict[str, Any] = {
        "modulo": peticion.dominio,
        "periodo": {
            "fecha_inicio": peticion.periodo.fecha_inicio or "inicio del periodo",
            "fecha_fin": peticion.periodo.fecha_fin or "cierre del periodo",
        },
        "totales": totales_calc,
        "distribuciones": distribuciones,
        "serie_mensual": [
            {"mes": p.mes, "cantidad": p.cantidad} for p in peticion.metricas.serie_mensual
        ],
        "comparativa": comparativa,
        "indicadores": peticion.metricas.indicadores,
        "alertas": alertas,
        "registros_procesados": registros_procesados,
    }

    # Construcción del prompt especializado
    rol = (
        peticion.rol_analista.strip()
        if peticion.rol_analista
        else f"Analista Experto en Datos y Gestión del Dominio '{peticion.dominio}'"
    )

    system_prompt = (
        f"Eres un {rol}.\n"
        "Tu objetivo es redactar un informe ejecutivo de alto nivel, altamente visual, "
        "estructurado y profesional basado EXCLUSIVAMENTE en las métricas suministradas.\n\n"
        "REGLAS OBLIGATORIAS DE FORMATO VISUAL:\n"
        "1. Estructura el informe con encabezados claros (### y ####).\n"
        "2. NUNCA presentes métricas como simples listas: incluye TABLAS MARKDOWN bien formateadas.\n"
        "3. DEBES INCLUIR AL MENOS UN GRÁFICO VISUAL MERMAID.JS (```mermaid ... ``` con 'pie title ...' o "
        "'xychart-beta') representando la distribución o tendencia más relevante.\n"
        "4. Usa bloques de cita (> ⚠️ **Punto Crítico:** ...) para resaltar alertas prioritarias.\n"
        "5. No inventes datos ni asumas información ajena a las métricas recibidas."
    )

    observacion = (
        sanitizar_observacion_usuario(peticion.observacion_usuario)
        if peticion.observacion_usuario
        else "Ninguna indicación adicional."
    )

    user_prompt = (
        f"Dominio Analizado: {peticion.dominio}\n"
        f"Intención del Informe: {peticion.intencion.value}\n"
        f"Periodo: {resumen['periodo']['fecha_inicio']} a {resumen['periodo']['fecha_fin']}\n\n"
        "DATOS PROCESADOS (Métricas y Alertas):\n"
        f"{json.dumps(resumen, ensure_ascii=False, indent=1, default=str)}\n\n"
        "INSTRUCCIONES ADICIONALES DEL CONSUMIDOR:\n"
        f"{observacion}\n\n"
        "ESTRUCTURA DEL INFORME:\n"
        "1. Resumen Ejecutivo (con totales y tabla resumen).\n"
        "2. Hallazgos Clave y Puntos Críticos (con tabla, alertas > ⚠️ y bloque ```mermaid nativo).\n"
        "3. Recomendaciones Operativas para la Toma de Decisiones (lista priorizada)."
    )

    contexto = {
        "resumen": resumen,
        "intencion": peticion.intencion.value,
        "modulo": peticion.dominio,
    }

    cliente = gemini_service.obtener_cliente()
    try:
        informe = cliente.generar_informe(system_prompt, user_prompt, contexto)
        modo = cliente.modo
    except Exception:
        informe = gemini_service.ClienteSimulado().generar_informe(
            system_prompt, user_prompt, contexto
        )
        modo = "simulado_fallback"

    transcurrido = time.perf_counter() - inicio

    return AnalisisResponseV2DTO(
        exito=True,
        dominio=peticion.dominio,
        intencion=peticion.intencion,
        informe_markdown=informe,
        meta=MetaDTO(
            registros_procesados=registros_procesados,
            tiempo_procesamiento_seg=round(transcurrido, 2),
            modo_informe=modo,
        ),
    )
