import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.knowledge.base import BaseConocimiento
from app.knowledge.dirpoles4 import (
    CAMPOS_PERMITIDOS_LLM,
    CATALOGO_PNF_OFICIAL,
    DIRECTRICES_CANONICAS,
    DISTRIBUCIONES_PERMITIDAS_LLM,
    DOMINIOS_DISTRIBUCIONES,
    ENFOQUE_POR_INTENCION,
    ESTADOS_JORNADA_VALIDOS,
    PLANTILLAS_ALERTAS_AUTORIZADAS,
    ROLES_POR_MODULO,
    es_alerta_autorizada,
    resolver_observacion_para_prompt,
    sanitizar_observacion_usuario,
)
from app.schemas.enums import (
    AreaGeneral,
    EstadoCita,
    EstadoInventario,
    EstadoJornada,
    EstadoReferencia,
    Genero,
    GradoDiscapacidad,
    Intencion,
    Modulo,
    SubmoduloTrabajoSocial,
    TipoBien,
    TipoConsultaPsicologica,
    TipoDiscapacidad,
    TipoVehiculo,
)


def construir_system_prompt(modulo: Modulo, conocimiento: BaseConocimiento | None = None) -> str:
    from app.knowledge import obtener_conocimiento_por_defecto

    kb = conocimiento or obtener_conocimiento_por_defecto()
    rol = kb.obtener_rol(modulo)
    return (
        f"Eres un {rol} para la UPTAEB.\n"
        "Tu objetivo es redactar un informe ejecutivo de alto nivel, altamente visual, "
        "estructurado y profesional basado EXCLUSIVAMENTE en los datos estadísticos "
        "procesados suministrados por la capa analítica en Pandas.\n\n"
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
        "5. No inventes cifras: cíñete estrictamente a los datos recibidos."
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
    def validar_estatus_jornada(cls, v: str) -> str:
        v_str = str(v).strip()
        if v_str in ESTADOS_JORNADA_VALIDOS:
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

    @field_validator("distribuciones")
    @classmethod
    def validar_distribuciones_autorizadas(
        cls, v: dict[str, list[DistribucionItem]]
    ) -> dict[str, list[DistribucionItem]]:
        dist_filtradas: dict[str, list[DistribucionItem]] = {}
        for k, items in v.items():
            if k not in DOMINIOS_DISTRIBUCIONES:
                continue
            dominio = DOMINIOS_DISTRIBUCIONES[k]
            if all(item.valor in dominio for item in items):
                dist_filtradas[k] = items
        return dist_filtradas

    @field_validator("alertas")
    @classmethod
    def validar_alertas_autorizadas(
        cls, v: list[AlertaContexto]
    ) -> list[AlertaContexto]:
        return [alt for alt in v if es_alerta_autorizada(alt.mensaje, alt.nivel)]



def _sanitizar_estructura_anidada(resumen: dict[str, Any]) -> dict[str, Any]:
    """Prefiltra estructuras anidadas para retener exclusivamente campos tipados conocidos."""
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

    # Distribuciones: extracción positiva estricta contra DOMINIOS_DISTRIBUCIONES
    distribuciones: dict[str, list[dict[str, Any]]] = {}
    if "distribuciones" in resumen and isinstance(resumen["distribuciones"], dict):
        raw_dist = resumen["distribuciones"]
        for dist_clave, dominio_autorizado in DOMINIOS_DISTRIBUCIONES.items():
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
    areas_aprobadas = frozenset(
        {"Becas", "Exoneración", "FAMES", "Medicina", "Orientación", "Discapacidad", "Psicología"}
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
                        estatus_seguro = (
                            estatus_candidato
                            if estatus_candidato in ESTADOS_JORNADA_VALIDOS
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
                    dominio_tipo = DOMINIOS_DISTRIBUCIONES["por_tipo"]
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
                if es_alerta_autorizada(mensaje_raw, nivel_seguro):
                    alertas_saneadas.append(
                        {
                            "nivel": nivel_seguro,
                            "mensaje": mensaje_raw,
                        }
                    )
    salida["alertas"] = alertas_saneadas

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
    """
    del conocimiento
    if not isinstance(resumen, dict):
        return {}

    prefiltrado = _sanitizar_estructura_anidada(resumen)
    modelo = ContextoAnaliticoSeguro.model_validate(prefiltrado)
    return modelo.model_dump(exclude_none=False)


def _json_resumen(resumen: dict[str, Any]) -> str:
    contexto_seguro = filtrar_contexto_seguro(resumen)
    return json.dumps(contexto_seguro, ensure_ascii=False, indent=1, default=str)


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
    return (
        f"Módulo Analizado: {modulo.value}\n"
        f"Intención del Informe: {intencion.value}\n"
        f"Periodo de Análisis: {fecha_inicio} a {fecha_fin}\n"
        f"Enfoque solicitado: {enfoque}\n\n"
        "DATOS PROCESADOS (Métricas, Agregaciones y Alertas detectadas por Pandas):\n"
        f"{_json_resumen(contexto_seguro)}\n\n"
        "INSTRUCCIONES ADICIONALES DEL USUARIO:\n"
        f"{observacion}\n\n"
        "REQUISITOS OBLIGATORIOS DE ESTRUCTURA Y FORMATO VISUAL:\n"
        "1. Resumen Ejecutivo (Visión general con métricas destacadas y tabla resumen).\n"
        "2. Hallazgos Clave y Puntos Críticos (Incluye tablas de distribución, citas de alertas "
        "> ⚠️ y AL MENOS UN GRÁFICO VISUAL ```mermaid pie o xychart-beta).\n"
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
