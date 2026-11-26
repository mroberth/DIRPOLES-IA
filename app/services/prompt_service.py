import json
import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.knowledge.base import BaseConocimiento
from app.knowledge.dirpoles4 import (
    DIRECTRICES_CANONICAS,
    DOMINIOS_DISTRIBUCIONES,
    ENFOQUE_POR_INTENCION,
    ESTADOS_JORNADA_VALIDOS,
    ROLES_POR_MODULO,
    es_alerta_autorizada,
    resolver_observacion_para_prompt,
    sanitizar_observacion_usuario,
)
from app.schemas.enums import Intencion, Modulo


def construir_system_prompt(modulo: Modulo, conocimiento: BaseConocimiento | None = None) -> str:
    from app.knowledge import obtener_conocimiento_por_defecto

    kb = conocimiento or obtener_conocimiento_por_defecto()
    rol = kb.obtener_rol(modulo)

    # Las instrucciones y directrices son conocimiento declarativo: viven en la
    # base de datos y se leen a través del protocolo BaseConocimiento. Se usa
    # getattr para mantener compatibilidad con bases de conocimiento externas
    # que solo implementan el contrato mínimo (rol, enfoque, dominios, alertas).
    obtener_instrucciones = getattr(kb, "obtener_instrucciones_sistema", None)
    instrucciones = obtener_instrucciones(modulo) if callable(obtener_instrucciones) else ""
    obtener_privacidad = getattr(kb, "obtener_directrices_privacidad", None)
    privacidad = obtener_privacidad(modulo) if callable(obtener_privacidad) else ""

    bloque_instrucciones = f"{instrucciones}\n\n" if instrucciones else ""
    bloque_privacidad = (
        f"DIRECTRICES DE PRIVACIDAD Y DEONTOLOGÍA:\n{privacidad}\n\n" if privacidad else ""
    )

    return (
        f"Eres un {rol} para la UPTAEB.\n"
        f"{bloque_instrucciones}"
        "Tu objetivo es redactar un informe ejecutivo de alto nivel, altamente visual, "
        "estructurado y profesional basado EXCLUSIVAMENTE en los datos estadísticos "
        "procesados suministrados por la capa analítica en Pandas.\n\n"
        f"{bloque_privacidad}"
        "REGLAS OBLIGATORIAS DE FORMATO VISUAL:\n"
        "1. Estructura el informe con encabezados claros (### y ####).\n"
        "2. NUNCA presentes distribuciones o métricas comparativas como simples listas de texto: "
        "OBLIGATORIAMENTE debes incluir TABLAS MARKDOWN bien formateadas "
        "(`| Categoría | Cantidad | Porcentaje (%) |`).\n"
        "3. DEBES INCLUIR AL MENOS UN GRÁFICO VISUAL MERMAID.JS "
        "(usando el bloque ```mermaid ... ``` con 'pie title ...' para gráficos de pastel o "
        "'xychart-beta' para gráficos de barras) "
        "representando la distribución de datos más importante.\n"
        "4. Usa bloques de cita (> ⚠️ **Punto Crítico:** ...) para resaltar alertas u "
        "observaciones que requieran atención inmediata.\n"
        "5. LENGUAJE CLARO Y ACCESIBLE: Si incluyes proyecciones o métricas de Machine "
        "Learning (R², MAE, RMSE), exprésalas en lenguaje comprensible para personal de "
        "salud o directivo (ej: 'Pronóstico para el próximo mes', 'Confiabilidad del "
        "Pronóstico (R²)', 'Margen de Variación Esperado (MAE: ±X casos)'). NUNCA uses "
        "símbolos de dólar $ en las siglas.\n"
        "6. No inventes cifras: cíñete estrictamente a los datos recibidos."
    )


# Lista estricta de claves analíticas agregadas autorizadas para transmisión al LLM
CAMPOS_PERMITIDOS_LLM: frozenset[str] = frozenset(
    {
        "modulo",
        "periodo",
        "registros_procesados",
        "totales",
        "distribuciones",
        "comparativa",
        "serie_mensual",
        "top_areas_concentracion",
        "indicadores",
        "secciones",
        "alertas",
        "prediccion_ml",
    }
)


# Modelos Pydantic estrictos para validación recursiva de la frontera de privacidad
class PeriodoContexto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha_inicio: str | None = None
    fecha_fin: str | None = None


class DistribucionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valor: str = Field(max_length=150)
    cantidad: int = Field(ge=0)
    porcentaje: float = Field(ge=0.0)


class PuntoMes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mes: str = Field(max_length=30)
    cantidad: int = Field(ge=0)


class ComparativaContexto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mes_anterior: PuntoMes | None = None
    mes_actual: PuntoMes | None = None
    variacion_pct: float | None = None
    nota: str | None = None


class AlertaContexto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nivel: str = Field(max_length=30)
    mensaje: str = Field(max_length=500)

    @field_validator("nivel")
    @classmethod
    def validar_nivel(cls, v: str) -> str:
        v_str = str(v).strip().lower()
        if v_str in {"critico", "advertencia", "info"}:
            return v_str
        return "info"


class ItemStockCritico(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(max_length=150)
    cantidad: int = Field(ge=0)
    vencimiento: str = Field(max_length=40)

    @field_validator("nombre")
    @classmethod
    def validar_nombre_insumo(cls, v: str) -> str:
        v_str = str(v).strip()
        if re.match(r"^Insumo\s*#\d+$", v_str):
            return v_str
        return "Insumo Genérico"

    @field_validator("vencimiento")
    @classmethod
    def validar_vencimiento_insumo(cls, v: str) -> str:
        v_str = str(v).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", v_str):
            return v_str[:10]
        return "N/A"


class IndicadoresInsumos(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vencidos: int = Field(default=0, ge=0)
    por_vencer_30_dias: int = Field(default=0, ge=0)
    stock_critico: list[ItemStockCritico] = Field(default_factory=list)


class ItemOcupacionJornada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jornada: str = Field(max_length=200)
    estatus: str = Field(max_length=50)
    aforo: int = Field(ge=0)
    asistentes: int = Field(ge=0)
    ocupacion_pct: float = Field(ge=0.0)

    @field_validator("jornada")
    @classmethod
    def validar_jornada_generica(cls, v: str) -> str:
        v_str = str(v).strip()
        if re.match(r"^Jornada\s*#\d+$", v_str):
            return v_str
        return "Jornada Genérica"

    @field_validator("estatus")
    @classmethod
    def validar_estatus_jornada(cls, v: str, info: ValidationInfo) -> str:
        v_str = str(v).strip()
        catalogos = (info.context or {}).get("catalogos", {})
        estados_validos = catalogos.get("estado_jornada", ESTADOS_JORNADA_VALIDOS)
        if v_str in estados_validos:
            return v_str
        return "No especificado"


class IndicadoresContexto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    insumos: IndicadoresInsumos | None = None
    citas_pendientes: int | None = None
    citas_no_asistio: int | None = None
    porcentaje_atendidas: float | None = None
    con_carnet: int | None = None
    sin_carnet: int | None = None
    requiere_asistencia: int | None = None
    grado_grave: int | None = None
    pendientes: int | None = None
    asistentes_totales: int | None = None
    diagnosticos_totales: int | None = None
    jornadas_sin_finalizar: int | None = None
    ocupacion_por_jornada: list[ItemOcupacionJornada] = Field(default_factory=list)
    unidades_mobiliario: int | None = None
    bienes_inactivos: int | None = None


class SeccionTransporteContexto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_registros: int = Field(default=0, ge=0)
    por_estado: list[DistribucionItem] = Field(default_factory=list)
    por_estatus: list[DistribucionItem] = Field(default_factory=list)
    por_tipo: list[DistribucionItem] = Field(default_factory=list)
    bajo_stock: int | None = None


class MetricasEvaluacionMLContexto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    r2_score: float = Field(ge=0.0, le=1.0)
    mae: float = Field(ge=0.0)
    mse: float = Field(ge=0.0)
    rmse: float = Field(ge=0.0)


class PrediccionMLContexto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disponible: bool
    motivo: str | None = None
    algoritmo: str | None = None
    periodos_entrenados: int | None = None
    proximo_mes: str | None = None
    prediccion_estimada: int | None = None
    margen_error_mae: float | None = None
    tendencia: str | None = None
    tasa_cambio_mensual: float | None = None
    metricas_evaluacion: MetricasEvaluacionMLContexto | None = None


class ContextoAnaliticoSeguro(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modulo: str = Field(max_length=50)
    periodo: PeriodoContexto = Field(default_factory=PeriodoContexto)
    registros_procesados: int = Field(default=0, ge=0)
    totales: dict[str, int] = Field(default_factory=dict)
    distribuciones: dict[str, list[DistribucionItem]] = Field(default_factory=dict)
    comparativa: ComparativaContexto | None = None
    serie_mensual: list[PuntoMes] = Field(default_factory=list)
    top_areas_concentracion: list[DistribucionItem] = Field(default_factory=list)
    indicadores: IndicadoresContexto = Field(default_factory=IndicadoresContexto)
    secciones: dict[str, SeccionTransporteContexto] = Field(default_factory=dict)
    alertas: list[AlertaContexto] = Field(default_factory=list)
    prediccion_ml: PrediccionMLContexto | None = None

    @field_validator("distribuciones")
    @classmethod
    def validar_distribuciones_autorizadas(
        cls,
        v: dict[str, list[DistribucionItem]],
        info: ValidationInfo,
    ) -> dict[str, list[DistribucionItem]]:
        contexto = info.context or {}
        dominios: dict[str, frozenset[str]] = contexto.get("dominios", DOMINIOS_DISTRIBUCIONES)
        dist_filtradas: dict[str, list[DistribucionItem]] = {}
        for k, items in v.items():
            if k not in dominios:
                continue
            dominio = dominios[k]
            if all(item.valor in dominio for item in items):
                dist_filtradas[k] = items
        return dist_filtradas

    @field_validator("alertas")
    @classmethod
    def validar_alertas_autorizadas(
        cls,
        v: list[AlertaContexto],
        info: ValidationInfo,
    ) -> list[AlertaContexto]:
        contexto = info.context or {}
        validador = contexto.get("validador_alerta", es_alerta_autorizada)
        return [alt for alt in v if validador(alt.mensaje, alt.nivel)]


def _sanitizar_estructura_anidada(
    resumen: dict[str, Any],
    dominios: dict[str, frozenset[str]] | None = None,
    validador_alerta: Callable[[str, str], bool] | None = None,
    catalogos: dict[str, frozenset[str]] | None = None,
) -> dict[str, Any]:
    """Prefiltra estructuras anidadas para retener exclusivamente campos tipados conocidos."""
    dominios_autorizados = dominios if dominios is not None else DOMINIOS_DISTRIBUCIONES
    catalogos_autorizados = catalogos or {}
    validar_alerta = validador_alerta or es_alerta_autorizada
    salida: dict[str, Any] = {}

    if "modulo" in resumen and isinstance(resumen["modulo"], (str, Modulo)):
        salida["modulo"] = str(
            resumen["modulo"].value if isinstance(resumen["modulo"], Modulo) else resumen["modulo"]
        )
    else:
        salida["modulo"] = "desconocido"

    if "periodo" in resumen and isinstance(resumen["periodo"], dict):
        p = resumen["periodo"]
        salida["periodo"] = {
            "fecha_inicio": str(p["fecha_inicio"]) if p.get("fecha_inicio") is not None else None,
            "fecha_fin": str(p["fecha_fin"]) if p.get("fecha_fin") is not None else None,
        }
    else:
        salida["periodo"] = {"fecha_inicio": None, "fecha_fin": None}

    salida["registros_procesados"] = int(resumen.get("registros_procesados", 0) or 0)

    # Totales: estrictamente dict[str, int]
    totales: dict[str, int] = {}
    if "totales" in resumen and isinstance(resumen["totales"], dict):
        for k, v in resumen["totales"].items():
            if isinstance(k, str) and isinstance(v, (int, float)):
                totales[k] = int(v)
    salida["totales"] = totales

    # Distribuciones: extracción positiva estricta contra los dominios autorizados
    distribuciones: dict[str, list[dict[str, Any]]] = {}
    if "distribuciones" in resumen and isinstance(resumen["distribuciones"], dict):
        raw_dist = resumen["distribuciones"]
        for dist_clave, dominio_autorizado in dominios_autorizados.items():
            if dist_clave in raw_dist and isinstance(raw_dist[dist_clave], list):
                items_candidatos = raw_dist[dist_clave]
                items_validos: list[dict[str, Any]] = []
                todos_validos = True

                for item in items_candidatos:
                    if not (isinstance(item, dict) and "valor" in item and "cantidad" in item):
                        todos_validos = False
                        break

                    valor_candidato = str(item["valor"]).strip()
                    if valor_candidato not in dominio_autorizado:
                        todos_validos = False
                        break

                    try:
                        cant = int(item["cantidad"])
                        pct = float(item.get("porcentaje", 0.0))
                    except (ValueError, TypeError):
                        todos_validos = False
                        break

                    items_validos.append(
                        {
                            "valor": valor_candidato,
                            "cantidad": cant,
                            "porcentaje": pct,
                        }
                    )

                # Regla innegociable de privacidad e integridad analítica:
                # No presentar distribuciones parciales como si fueran completas.
                # Si algún elemento posee una etiqueta ajena al dominio autorizado,
                # toda la distribución se excluye del contexto externo.
                if todos_validos:
                    distribuciones[dist_clave] = items_validos

    salida["distribuciones"] = distribuciones

    # Comparativa
    if "comparativa" in resumen and isinstance(resumen["comparativa"], dict):
        comp = resumen["comparativa"]
        salida["comparativa"] = {
            "mes_anterior": (
                {
                    "mes": str(comp["mes_anterior"].get("mes", "")),
                    "cantidad": int(comp["mes_anterior"].get("cantidad", 0)),
                }
                if isinstance(comp.get("mes_anterior"), dict)
                else None
            ),
            "mes_actual": (
                {
                    "mes": str(comp["mes_actual"].get("mes", "")),
                    "cantidad": int(comp["mes_actual"].get("cantidad", 0)),
                }
                if isinstance(comp.get("mes_actual"), dict)
                else None
            ),
            "variacion_pct": (
                float(comp["variacion_pct"]) if comp.get("variacion_pct") is not None else None
            ),
            "nota": str(comp["nota"]) if comp.get("nota") is not None else None,
        }
    else:
        salida["comparativa"] = None

    # Serie mensual
    serie_mensual: list[dict[str, Any]] = []
    if "serie_mensual" in resumen and isinstance(resumen["serie_mensual"], list):
        for pto in resumen["serie_mensual"]:
            if isinstance(pto, dict) and "mes" in pto and "cantidad" in pto:
                try:
                    serie_mensual.append(
                        {"mes": str(pto["mes"])[:30], "cantidad": int(pto["cantidad"])}
                    )
                except (ValueError, TypeError):
                    continue
    salida["serie_mensual"] = serie_mensual

    # Top areas concentracion (solo admitir categorias de area aprobadas)
    top_areas: list[dict[str, Any]] = []
    areas_aprobadas = catalogos_autorizados.get(
        "area", dominios_autorizados.get("por_area", frozenset())
    )
    if "top_areas_concentracion" in resumen and isinstance(
        resumen["top_areas_concentracion"], list
    ):
        for item in resumen["top_areas_concentracion"]:
            if isinstance(item, dict) and "valor" in item and "cantidad" in item:
                val = str(item["valor"])[:150]
                if val in areas_aprobadas:
                    try:
                        top_areas.append(
                            {
                                "valor": val,
                                "cantidad": int(item["cantidad"]),
                                "porcentaje": float(item.get("porcentaje", 0.0)),
                            }
                        )
                    except (ValueError, TypeError):
                        continue
    salida["top_areas_concentracion"] = top_areas

    # Indicadores
    indicadores_saneados: dict[str, Any] = {}
    if "indicadores" in resumen and isinstance(resumen["indicadores"], dict):
        ind = resumen["indicadores"]
        for ik, iv in ind.items():
            if ik == "insumos" and isinstance(iv, dict):
                criticos = []
                for idx, sc in enumerate(iv.get("stock_critico", []), start=1):
                    if isinstance(sc, dict):
                        venc_candidato = str(sc.get("vencimiento", "")).strip()
                        venc_seguro = (
                            venc_candidato[:10]
                            if re.match(r"^\d{4}-\d{2}-\d{2}", venc_candidato)
                            else "N/A"
                        )
                        criticos.append(
                            {
                                "nombre": f"Insumo #{idx}",
                                "cantidad": int(sc.get("cantidad", 0)),
                                "vencimiento": venc_seguro,
                            }
                        )
                indicadores_saneados["insumos"] = {
                    "vencidos": int(iv.get("vencidos", 0)),
                    "por_vencer_30_dias": int(iv.get("por_vencer_30_dias", 0)),
                    "stock_critico": criticos,
                }
            elif ik == "ocupacion_por_jornada" and isinstance(iv, list):
                ocup = []
                for idx, oj in enumerate(iv, start=1):
                    if isinstance(oj, dict):
                        estatus_candidato = str(oj.get("estatus", "")).strip()
                        estados_jornada = catalogos_autorizados.get(
                            "estado_jornada", ESTADOS_JORNADA_VALIDOS
                        )
                        estatus_seguro = (
                            estatus_candidato
                            if estatus_candidato in estados_jornada
                            else "No especificado"
                        )
                        ocup.append(
                            {
                                "jornada": f"Jornada #{idx}",
                                "estatus": estatus_seguro,
                                "aforo": int(oj.get("aforo", 0)),
                                "asistentes": int(oj.get("asistentes", 0)),
                                "ocupacion_pct": float(oj.get("ocupacion_pct", 0.0)),
                            }
                        )
                indicadores_saneados["ocupacion_por_jornada"] = ocup
            elif ik in {
                "citas_pendientes",
                "citas_no_asistio",
                "con_carnet",
                "sin_carnet",
                "requiere_asistencia",
                "grado_grave",
                "pendientes",
                "asistentes_totales",
                "diagnosticos_totales",
                "jornadas_sin_finalizar",
                "unidades_mobiliario",
                "bienes_inactivos",
            } and isinstance(iv, (int, float)):
                indicadores_saneados[ik] = int(iv)
            elif ik == "porcentaje_atendidas" and isinstance(iv, (int, float)):
                indicadores_saneados[ik] = float(iv)
    salida["indicadores"] = indicadores_saneados

    # Secciones (Transporte)
    secciones_saneadas: dict[str, Any] = {}
    if "secciones" in resumen and isinstance(resumen["secciones"], dict):
        for sk, sv in resumen["secciones"].items():
            if isinstance(sk, str) and isinstance(sv, dict):
                sec_dict: dict[str, Any] = {
                    "total_registros": int(sv.get("total_registros", 0) or 0)
                }
                # Solo por_tipo tiene dominio controlado demostrado en transporte (TipoVehiculo)
                if "por_tipo" in sv and isinstance(sv["por_tipo"], list):
                    dominio_tipo = dominios_autorizados["por_tipo"]
                    items_tipo = []
                    todos_tipo_validos = True
                    for d in sv["por_tipo"]:
                        if isinstance(d, dict) and "valor" in d and "cantidad" in d:
                            val = str(d["valor"]).strip()
                            if val in dominio_tipo:
                                try:
                                    items_tipo.append(
                                        {
                                            "valor": val,
                                            "cantidad": int(d["cantidad"]),
                                            "porcentaje": float(d.get("porcentaje", 0.0)),
                                        }
                                    )
                                except (ValueError, TypeError):
                                    todos_tipo_validos = False
                                    break
                            else:
                                todos_tipo_validos = False
                                break
                        else:
                            todos_tipo_validos = False
                            break
                    if todos_tipo_validos:
                        sec_dict["por_tipo"] = items_tipo
                if "bajo_stock" in sv and isinstance(sv["bajo_stock"], (int, float)):
                    sec_dict["bajo_stock"] = int(sv["bajo_stock"])
                secciones_saneadas[sk] = sec_dict
    salida["secciones"] = secciones_saneadas

    # Alertas: validación basada exclusivamente en plantillas canónicas autorizadas del sistema
    alertas_saneadas: list[dict[str, Any]] = []
    if "alertas" in resumen and isinstance(resumen["alertas"], list):
        for alt in resumen["alertas"]:
            if isinstance(alt, dict) and "nivel" in alt and "mensaje" in alt:
                nivel_raw = str(alt["nivel"]).strip().lower()
                nivel_seguro = (
                    nivel_raw if nivel_raw in {"critico", "advertencia", "info"} else "info"
                )
                mensaje_raw = str(alt["mensaje"]).strip()
                # Cuando una alerta no pueda vincularse a un mensaje autorizado,
                # no se transmite su texto original hacia el contexto externo.
                if validar_alerta(mensaje_raw, nivel_seguro):
                    alertas_saneadas.append(
                        {
                            "nivel": nivel_seguro,
                            "mensaje": mensaje_raw,
                        }
                    )
    salida["alertas"] = alertas_saneadas

    # Predicción Machine Learning (series temporales)
    pml = resumen.get("prediccion_ml")
    if isinstance(pml, dict):
        if pml.get("disponible") is True:
            metricas_candidato = pml.get("metricas_evaluacion")
            me = metricas_candidato if isinstance(metricas_candidato, dict) else {}
            salida["prediccion_ml"] = {
                "disponible": True,
                "algoritmo": str(pml.get("algoritmo", "Regresión Lineal OLS"))[:100],
                "periodos_entrenados": int(pml.get("periodos_entrenados", 0)),
                "proximo_mes": str(pml.get("proximo_mes", "Periodo Siguiente"))[:20],
                "prediccion_estimada": max(0, int(pml.get("prediccion_estimada", 0))),
                "margen_error_mae": float(pml.get("margen_error_mae", 0.0)),
                "tendencia": str(pml.get("tendencia", "Estable"))[:30],
                "tasa_cambio_mensual": float(pml.get("tasa_cambio_mensual", 0.0)),
                "metricas_evaluacion": {
                    "r2_score": max(0.0, min(1.0, float(me.get("r2_score", 0.0)))),
                    "mae": max(0.0, float(me.get("mae", 0.0))),
                    "mse": max(0.0, float(me.get("mse", 0.0))),
                    "rmse": max(0.0, float(me.get("rmse", 0.0))),
                },
            }
        else:
            salida["prediccion_ml"] = {
                "disponible": False,
                "motivo": str(pml.get("motivo", ""))[:200],
            }

    return salida


def filtrar_contexto_seguro(
    resumen: dict[str, Any],
    conocimiento: BaseConocimiento | None = None,
) -> dict[str, Any]:
    """Frontera explícita de privacidad recursiva para el LLM.

    Sanea y valida recursivamente tanto las claves de primer nivel como
    todas las estructuras anidadas (alertas, distribuciones, indicadores,
    secciones, comparativas). Emplea validación estricta Pydantic para
    asegurar que ningún dato crudo, centinela o clave ajena sobreviva.

    Los dominios cerrados y las plantillas de alertas provienen de la base de
    conocimiento activa (MariaDB o fallback estático), no de listas duplicadas
    en el motor.
    """
    from app.knowledge import obtener_conocimiento_por_defecto

    if not isinstance(resumen, dict):
        return {}

    kb = conocimiento or obtener_conocimiento_por_defecto()
    dominios = kb.obtener_dominios_distribuciones()
    obtener_catalogo = getattr(kb, "obtener_catalogo", None)
    catalogos = (
        {tipo: obtener_catalogo(tipo) for tipo in ("area", "estado_jornada")}
        if callable(obtener_catalogo)
        else {}
    )
    validador_alerta = kb.es_alerta_autorizada
    prefiltrado = _sanitizar_estructura_anidada(resumen, dominios, validador_alerta, catalogos)
    modelo = ContextoAnaliticoSeguro.model_validate(
        prefiltrado,
        context={
            "dominios": dominios,
            "catalogos": catalogos,
            "validador_alerta": validador_alerta,
        },
    )
    return modelo.model_dump(exclude_none=False)


def _json_resumen(
    resumen: dict[str, Any],
    conocimiento: BaseConocimiento | None = None,
) -> str:
    contexto_seguro = filtrar_contexto_seguro(resumen, conocimiento=conocimiento)
    return json.dumps(contexto_seguro, ensure_ascii=False, indent=1, default=str)


def resolver_tipo_grafico(
    observacion: str | None = None,
    distribuciones: dict[str, Any] | None = None,
) -> str:
    """Regla de inferencia simbólica para selección del tipo de gráfico Mermaid.js.

    1. Si el usuario solicita explícitamente barras ('barra', 'barras', 'columnas',
       'histograma') -> 'barras'.
    2. Si el usuario solicita líneas / tendencia ('linea', 'lineas', 'tendencia',
       'historico') -> 'lineas'.
    3. Si el usuario solicita combinado ('combinado', 'comparativa', 'mixto') -> 'combinado'.
    4. Si el usuario solicita pastel ('pastel', 'dona', 'torta', 'circular', 'pie') -> 'pie'.
    5. Heurística experta (por defecto): Si alguna distribución principal tiene más
       de 4 categorías -> 'barras'
       (para evitar saturación visual); si tiene 4 o menos -> 'pie'.
    """
    if observacion and isinstance(observacion, str):
        obs_lower = observacion.lower()
        if any(
            term in obs_lower
            for term in ("barra", "barras", "columna", "columnas", "histograma", "xychart")
        ):
            return "barras"
        if any(term in obs_lower for term in ("linea", "lineas", "tendencia", "historico")):
            return "lineas"
        if any(term in obs_lower for term in ("combinado", "comparativa", "mixto")):
            return "combinado"
        if any(term in obs_lower for term in ("pastel", "dona", "torta", "circular", "pie")):
            return "pie"

    if distribuciones and isinstance(distribuciones, dict):
        for filas in distribuciones.values():
            if isinstance(filas, list) and len(filas) > 4:
                return "barras"

    return "pie"


def construir_user_prompt(
    modulo: Modulo,
    intencion: Intencion,
    resumen: dict[str, Any],
    observacion_usuario: str | None,
    conocimiento: BaseConocimiento | None = None,
) -> str:
    from app.knowledge import obtener_conocimiento_por_defecto

    kb = conocimiento or obtener_conocimiento_por_defecto()
    contexto_seguro = filtrar_contexto_seguro(resumen, conocimiento=kb)
    periodo = contexto_seguro.get("periodo", {}) or {}
    fecha_inicio = periodo.get("fecha_inicio") or "inicio de los registros"
    fecha_fin = periodo.get("fecha_fin") or "la fecha actual"
    observacion = kb.resolver_directriz(observacion_usuario)
    enfoque = kb.obtener_enfoque(intencion)
    tipo_grafico = resolver_tipo_grafico(observacion_usuario, contexto_seguro.get("distribuciones"))

    if tipo_grafico == "barras":
        instruccion_grafico = (
            "AL MENOS UN GRÁFICO VISUAL Mermaid.js OBLIGATORIAMENTE DE BARRAS "
            "usando la sintaxis 'xychart-beta' "
            "(ejemplo: ```mermaid\nxychart-beta\n"
            '    title "..."\n    x-axis ["A", "B"]\n'
            "    bar [10, 20]\n```). "
            "Regla de inferencia: el usuario solicitó barras o la cardinalidad supera "
            "4 categorías; NO uses gráfico de pastel (pie). "
            "REGLA CRÍTICA DE LEGIBILIDAD EN BARRAS: En el x-axis NUNCA coloques "
            "nombres largos ni el prefijo redundante 'PNF '; "
            "usa etiquetas cortas de máximo 12 caracteres (ej: 'Informática', "
            "'Admin.', 'Agroalim.', 'Contaduría') "
            "para que las etiquetas no se solapen ni se lean pegadas"
        )
    elif tipo_grafico == "lineas":
        instruccion_grafico = (
            "AL MENOS UN GRÁFICO VISUAL Mermaid.js OBLIGATORIAMENTE DE LÍNEAS / "
            "TENDENCIA usando la sintaxis 'xychart-beta' "
            "(ejemplo: ```mermaid\nxychart-beta\n"
            '    title "..."\n    x-axis ["Ene", "Feb"]\n'
            "    line [10, 20]\n```). "
            "Regla de inferencia: el usuario solicitó gráfico de líneas/tendencia; "
            "usa 'line [...]' en xychart-beta"
        )
    elif tipo_grafico == "combinado":
        instruccion_grafico = (
            "AL MENOS UN GRÁFICO VISUAL Mermaid.js COMBINADO DE BARRAS Y LÍNEAS "
            "usando la sintaxis 'xychart-beta' "
            "(ejemplo: ```mermaid\nxychart-beta\n"
            '    title "..."\n    x-axis ["A", "B"]\n'
            "    bar [10, 20]\n    line [8, 15]\n```). "
            "Regla de inferencia: el usuario solicitó gráfico combinado; "
            "incluye tanto 'bar [...]' como 'line [...]'"
        )
    else:
        instruccion_grafico = "AL MENOS UN GRÁFICO VISUAL ```mermaid pie o xychart-beta)"

    return (
        f"Módulo Analizado: {modulo.value}\n"
        f"Intención del Informe: {intencion.value}\n"
        f"Periodo de Análisis: {fecha_inicio} a {fecha_fin}\n"
        f"Enfoque solicitado: {enfoque}\n\n"
        "DATOS PROCESADOS (Métricas, Agregaciones y Alertas detectadas por Pandas):\n"
        f"{_json_resumen(contexto_seguro, conocimiento=kb)}\n\n"
        "INSTRUCCIONES ADICIONALES DEL USUARIO:\n"
        f"{observacion}\n\n"
        "REQUISITOS OBLIGATORIOS DE ESTRUCTURA Y FORMATO VISUAL:\n"
        "1. Resumen Ejecutivo (Visión general con métricas destacadas y tabla resumen).\n"
        "2. Hallazgos Clave y Puntos Críticos (Incluye tablas de distribución, "
        f"citas de alertas > ⚠️ y {instruccion_grafico}).\n"
        "3. Recomendaciones Operativas para la Toma de Decisiones (Lista numerada priorizada "
        "y concreta)."
    )


def construir_prompts(
    modulo: Modulo,
    intencion: Intencion,
    resumen: dict[str, Any],
    observacion_usuario: str | None,
    conocimiento: BaseConocimiento | None = None,
) -> tuple[str, str]:
    from app.knowledge import obtener_conocimiento_por_defecto

    kb = conocimiento or obtener_conocimiento_por_defecto()
    return (
        construir_system_prompt(modulo, conocimiento=kb),
        construir_user_prompt(modulo, intencion, resumen, observacion_usuario, conocimiento=kb),
    )


__all__ = [
    "CAMPOS_PERMITIDOS_LLM",
    "DIRECTRICES_CANONICAS",
    "ENFOQUE_POR_INTENCION",
    "ROLES_POR_MODULO",
    "construir_prompts",
    "construir_system_prompt",
    "construir_user_prompt",
    "filtrar_contexto_seguro",
    "resolver_observacion_para_prompt",
    "resolver_tipo_grafico",
    "sanitizar_observacion_usuario",
]
