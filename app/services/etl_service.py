from datetime import date
from typing import Any

import pandas as pd

from app.adapters.base import AdaptadorFuenteDatos, Extraccion
from app.adapters.dirpoles4 import AdaptadorDirpoles4SQL
from app.core.config import obtener_ajustes
from app.knowledge import obtener_conocimiento_por_defecto
from app.knowledge.base import BaseConocimiento
from app.knowledge.dirpoles4.parametros import (
    MENSAJES_POR_DEFECTO,
    UMBRALES_POR_DEFECTO,
)
from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO
from app.services.ml_service import predecir_demanda

Resumen = dict[str, Any]

_ADAPTADOR_DEFAULT: AdaptadorFuenteDatos = AdaptadorDirpoles4SQL()


def _kb(conocimiento: BaseConocimiento | None = None) -> BaseConocimiento:
    """Resuelve la base de conocimiento activa (MariaDB o fallback estático)."""
    return conocimiento or obtener_conocimiento_por_defecto()


def _umbral(kb: BaseConocimiento, codigo_hecho: str) -> float:
    """Lee un umbral declarativo de la base de conocimiento."""
    por_defecto = UMBRALES_POR_DEFECTO.get(codigo_hecho, 0.0)
    return float(kb.obtener_umbral(codigo_hecho, por_defecto))


def _mensaje(kb: BaseConocimiento, codigo_conclusion: str, **valores: Any) -> str:
    """Lee y formatea una plantilla de mensaje declarativa."""
    por_defecto = MENSAJES_POR_DEFECTO.get(codigo_conclusion, "")
    return kb.obtener_mensaje(codigo_conclusion, por_defecto, **valores)


def extraer(
    modulo: Modulo,
    filtros: FiltrosDTO,
    id_empleado: int | None,
    limit: int,
    adaptador: AdaptadorFuenteDatos | None = None,
) -> Extraccion:
    fuente = adaptador or _ADAPTADOR_DEFAULT
    return fuente.extraer(modulo, filtros, id_empleado, limit)


def _porcentaje(cantidad: int, total: int) -> float:
    return round(100.0 * cantidad / total, 1) if total else 0.0


def _distribucion(
    df: pd.DataFrame,
    columna: str,
    mapeo: dict[str, str] | None = None,
    limite: int = 10,
) -> list[dict[str, Any]]:
    if df.empty or columna not in df.columns:
        return []
    serie = df[columna].fillna("No especificado").astype(str)
    if mapeo:
        serie = serie.map(lambda valor: mapeo.get(valor, valor))
    conteos = serie.value_counts().head(limite)
    total = len(df)
    return [
        {
            "valor": str(valor),
            "cantidad": int(cantidad),
            "porcentaje": _porcentaje(int(cantidad), total),
        }
        for valor, cantidad in conteos.items()
    ]


def _serie_mensual(df: pd.DataFrame, columna_fecha: str) -> list[dict[str, Any]]:
    if df.empty or columna_fecha not in df.columns:
        return []
    fechas = pd.to_datetime(df[columna_fecha], errors="coerce")
    validas = fechas.dropna()
    if validas.empty:
        return []
    meses = validas.dt.to_period("M").astype(str)
    conteos = meses.value_counts().sort_index()
    return [{"mes": str(mes), "cantidad": int(cantidad)} for mes, cantidad in conteos.items()]


def _comparativa(serie: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(serie) < 2:
        return None
    anterior = serie[-2]
    actual = serie[-1]
    v1 = int(anterior["cantidad"])
    v2 = int(actual["cantidad"])
    variacion = round(100.0 * (v2 - v1) / v1, 1) if v1 else None
    return {
        "mes_anterior": anterior,
        "mes_actual": actual,
        "variacion_pct": variacion,
        "nota": None if v1 else "Sin base de comparación (mes anterior en cero)",
    }


def _alerta(nivel: str, mensaje: str) -> dict[str, str]:
    return {"nivel": nivel, "mensaje": mensaje}


def _fechas_periodo(filtros: FiltrosDTO) -> dict[str, str | None]:
    return {
        "fecha_inicio": filtros.fecha_inicio.isoformat() if filtros.fecha_inicio else None,
        "fecha_fin": filtros.fecha_fin.isoformat() if filtros.fecha_fin else None,
    }


def _top_concentracion(
    df: pd.DataFrame, columna: str, umbral: float = 20.0
) -> list[dict[str, Any]]:
    if df.empty or columna not in df.columns:
        return []
    serie = df[columna].dropna().astype(str)
    if serie.empty:
        return []
    conteos = serie.value_counts()
    total = int(conteos.sum())
    acumulado = 0.0
    seleccion: list[dict[str, Any]] = []
    for valor, cantidad in conteos.items():
        porcentaje = _porcentaje(int(cantidad), total)
        if porcentaje < umbral and seleccion:
            break
        seleccion.append({"valor": str(valor), "cantidad": int(cantidad), "porcentaje": porcentaje})
        acumulado += porcentaje
        if acumulado >= umbral:
            break
    return seleccion


def _dias_hasta(vencimiento: Any) -> int | None:
    try:
        fecha = pd.to_datetime(vencimiento, errors="coerce")
    except (TypeError, ValueError):
        return None
    if pd.isna(fecha):
        return None
    return int((fecha.date() - date.today()).days)


def _montos_truncados(
    extraccion: Extraccion,
    alertas: list[dict[str, str]],
    conocimiento: BaseConocimiento,
) -> None:
    for nombre, total in extraccion.totales.items():
        obtenidos = len(extraccion.datos.get(nombre, []))
        if total > obtenidos:
            alertas.append(
                _alerta(
                    "advertencia",
                    _mensaje(
                        conocimiento,
                        "ALERTA_TRUNCAMIENTO",
                        coleccion=nombre,
                        total=total,
                        analizados=obtenidos,
                    ),
                )
            )


def _insumos_alertas(
    insumos: pd.DataFrame,
    alertas: list[dict[str, str]],
    conocimiento: BaseConocimiento,
) -> dict[str, Any]:
    if insumos.empty:
        return {"vencidos": 0, "por_vencer_30_dias": 0, "stock_critico": []}
    umbral_stock = _umbral(conocimiento, "STOCK_INSUMO_MEDICO")
    umbral_vencido = _umbral(conocimiento, "DIAS_VENCIMIENTO_VENCIDO")
    umbral_proximo = _umbral(conocimiento, "DIAS_VENCIMIENTO_PROXIMO")
    vencidos = 0
    por_vencer = 0
    for fecha in insumos.get("fecha_vencimiento", pd.Series(dtype=object)):
        dias = _dias_hasta(fecha)
        if dias is None:
            continue
        if dias < umbral_vencido:
            vencidos += 1
        elif dias <= umbral_proximo:
            por_vencer += 1
    critico = insumos[
        insumos.get("cantidad", pd.Series(dtype=object)).fillna(0).astype(int) < umbral_stock
    ]
    if vencidos:
        alertas.append(
            _alerta(
                "critico",
                _mensaje(conocimiento, "ALERTA_INSUMOS_VENCIDOS", cantidad=vencidos),
            )
        )
    if por_vencer:
        alertas.append(
            _alerta(
                "advertencia",
                _mensaje(conocimiento, "ALERTA_INSUMOS_POR_VENCER", cantidad=por_vencer),
            )
        )
    if len(critico):
        alertas.append(
            _alerta(
                "critico",
                _mensaje(
                    conocimiento,
                    "ALERTA_INSUMOS_STOCK_CRITICO",
                    cantidad=len(critico),
                    umbral=int(umbral_stock),
                ),
            )
        )
    return {
        "vencidos": vencidos,
        "por_vencer_30_dias": por_vencer,
        "stock_critico": [
            {
                "nombre": str(fila.get("nombre_insumo", "")),
                "cantidad": int(fila.get("cantidad", 0) or 0),
                "vencimiento": str(fila.get("fecha_vencimiento", "")),
            }
            for _, fila in critico.head(5).iterrows()
        ],
    }


def _transformar_general(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    df = extraccion.datos.get("atenciones", pd.DataFrame())
    por_area = _distribucion(df, "area")
    if por_area:
        concentrada = por_area[0]
        umbral_area = _umbral(conocimiento, "CONCENTRACION_AREA_GENERAL")
        if concentrada["porcentaje"] >= umbral_area:
            alertas.append(
                _alerta(
                    "advertencia",
                    _mensaje(
                        conocimiento,
                        "ALERTA_AREA_CONCENTRADA",
                        valor=concentrada["valor"],
                        porcentaje=concentrada["porcentaje"],
                    ),
                )
            )
    serie = _serie_mensual(df, "fecha")
    top = _top_concentracion(df, "area") if "area" in df.columns else []
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_area": por_area,
            "por_genero": _distribucion(df, "genero", {"M": "Masculino", "F": "Femenino"}),
            "por_pnf": _distribucion(df, "nombre_pnf", limite=8),
        },
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
        "top_areas_concentracion": top,
    }


def _transformar_medicina(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    consultas = extraccion.datos.get("consultas", pd.DataFrame())
    insumos = extraccion.datos.get("insumos", pd.DataFrame())
    indicadores_insumos = _insumos_alertas(insumos, alertas, conocimiento)
    serie = _serie_mensual(consultas, "fecha")
    comp = _comparativa(serie)
    umbral_variacion = _umbral(conocimiento, "VARIACION_CONSULTAS_MEDICAS")
    if (
        comp
        and isinstance(comp.get("variacion_pct"), float)
        and comp["variacion_pct"] >= umbral_variacion
    ):
        alertas.append(
            _alerta(
                "advertencia",
                _mensaje(
                    conocimiento,
                    "ALERTA_CONSULTAS_AUMENTO",
                    variacion=comp["variacion_pct"],
                ),
            )
        )
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_genero": _distribucion(consultas, "genero", {"M": "Masculino", "F": "Femenino"}),
            "por_pnf": _distribucion(consultas, "nombre_pnf", limite=8),
            "insumos_por_estatus": _distribucion(insumos, "estatus"),
        },
        "comparativa": comp,
        "serie_mensual": serie,
        "indicadores": {"insumos": indicadores_insumos},
    }


def _transformar_psicologia(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    morbilidad = extraccion.datos.get("morbilidad", pd.DataFrame())
    citas = extraccion.datos.get("citas", pd.DataFrame())
    por_estado = _distribucion(citas, "estado")
    pendientes = next((e["cantidad"] for e in por_estado if e["valor"] == "Pendiente"), 0)
    no_asistio = next((e["cantidad"] for e in por_estado if e["valor"] == "No asistió"), 0)
    total_citas = extraccion.totales.get("citas", 0)
    umbral_inasistencia = _umbral(conocimiento, "TASA_AUSENTISMO_CITA_PSI")
    umbral_diagnostico = _umbral(conocimiento, "CONCENTRACION_DIAGNOSTICO_PSI")
    if pendientes:
        alertas.append(
            _alerta(
                "advertencia",
                _mensaje(conocimiento, "ALERTA_CITAS_PENDIENTES", cantidad=pendientes),
            )
        )
    if total_citas and no_asistio and _porcentaje(no_asistio, total_citas) >= umbral_inasistencia:
        alertas.append(
            _alerta(
                "critico",
                _mensaje(
                    conocimiento,
                    "ALERTA_CITAS_NO_ASISTIO",
                    porcentaje=_porcentaje(no_asistio, total_citas),
                ),
            )
        )
    top = _top_concentracion(morbilidad, "diagnostico")
    if top and top[0]["porcentaje"] >= umbral_diagnostico:
        alertas.append(
            _alerta(
                "advertencia",
                _mensaje(
                    conocimiento,
                    "ALERTA_MORBILIDAD_CONCENTRADA",
                    porcentaje=top[0]["porcentaje"],
                ),
            )
        )
    serie = _serie_mensual(morbilidad, "fecha")
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "morbilidad_por_tipo_consulta": _distribucion(morbilidad, "tipo_consulta"),
            "por_pnf": _distribucion(morbilidad, "nombre_pnf", limite=8),
            "citas_por_estado": por_estado,
        },
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
        "indicadores": {
            "citas_pendientes": pendientes,
            "citas_no_asistio": no_asistio,
            "porcentaje_atendidas": _porcentaje(
                next((e["cantidad"] for e in por_estado if e["valor"] == "Atendida"), 0),
                total_citas,
            ),
        },
    }


def _transformar_orientacion(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros, alertas, conocimiento
    df = extraccion.datos.get("casos", pd.DataFrame())
    serie = _serie_mensual(df, "fecha")
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_genero": _distribucion(df, "genero", {"M": "Masculino", "F": "Femenino"}),
            "por_pnf": _distribucion(df, "nombre_pnf", limite=8),
        },
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
    }


def _transformar_trabajo_social(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    df = extraccion.datos.get("registros", pd.DataFrame())
    por_submodulo = _distribucion(df, "submodulo")
    umbral_becas = _umbral(conocimiento, "CONCENTRACION_SOLICITUD_BECA")
    if por_submodulo:
        primera = por_submodulo[0]
        if primera["valor"] == "Becas" and primera["porcentaje"] >= umbral_becas:
            alertas.append(
                _alerta(
                    "advertencia",
                    _mensaje(
                        conocimiento,
                        "ALERTA_BECAS_CONCENTRADAS",
                        porcentaje=primera["porcentaje"],
                    ),
                )
            )
    serie = _serie_mensual(df, "fecha")
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_submodulo": por_submodulo,
            "por_pnf": _distribucion(df, "nombre_pnf", limite=8),
            "por_genero": _distribucion(df, "genero", {"M": "Masculino", "F": "Femenino"}),
        },
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
    }


def _transformar_discapacidad(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    df = extraccion.datos.get("registros", pd.DataFrame())
    total = extraccion.totales.get("registros", 0)
    con_carnet = 0
    con_asistencia = 0
    graves = 0
    if not df.empty:
        if "carnet_discapacidad" in df:
            con_carnet = int(
                df["carnet_discapacidad"].fillna("").astype(str).str.strip().ne("").sum()
            )
        if "requiere_asistencia" in df:
            con_asistencia = int(
                df["requiere_asistencia"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .ne("no")
                .sum()
            )
        if "grado" in df:
            graves = int((df["grado"].astype(str) == "Grave").sum())
    if graves:
        alertas.append(
            _alerta(
                "advertencia",
                _mensaje(conocimiento, "ALERTA_DISCAPACIDAD_GRAVE", cantidad=graves),
            )
        )
    if total and con_carnet < total:
        faltantes = total - con_carnet
        alertas.append(
            _alerta(
                "advertencia",
                _mensaje(conocimiento, "ALERTA_SIN_CARNET", cantidad=faltantes),
            )
        )
    serie = _serie_mensual(df, "fecha")
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_tipo": _distribucion(df, "tipo_discapacidad"),
            "por_grado": _distribucion(df, "grado"),
            "por_pnf": _distribucion(df, "nombre_pnf", limite=8),
        },
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
        "indicadores": {
            "con_carnet": con_carnet,
            "sin_carnet": max(total - con_carnet, 0),
            "requiere_asistencia": con_asistencia,
            "grado_grave": graves,
        },
    }


def _transformar_referencias(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    df = extraccion.datos.get("remisiones", pd.DataFrame())
    por_estado = _distribucion(df, "estado")
    pendientes = next((e["cantidad"] for e in por_estado if e["valor"] == "Pendiente"), 0)
    total = extraccion.totales.get("remisiones", 0)
    if pendientes:
        alertas.append(
            _alerta(
                "advertencia",
                _mensaje(
                    conocimiento,
                    "ALERTA_REFERENCIAS_PENDIENTES",
                    cantidad=pendientes,
                    porcentaje=_porcentaje(pendientes, total),
                ),
            )
        )
    serie = _serie_mensual(df, "fecha")
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_estado": por_estado,
            "por_servicio_destino": _distribucion(df, "servicio_destino", limite=8),
        },
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
        "indicadores": {"pendientes": pendientes},
    }


def _transformar_jornadas(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    df = extraccion.datos.get("jornadas", pd.DataFrame())
    umbral_ocupacion = _umbral(conocimiento, "OCUPACION_JORNADA")
    por_estatus = _distribucion(df, "estatus")
    asistentes = (
        int(df["total_asistentes"].sum())
        if "total_asistentes" in df.columns and not df.empty
        else 0
    )
    diagnosticos = (
        int(df["total_diagnosticos"].sum())
        if "total_diagnosticos" in df.columns and not df.empty
        else 0
    )
    ocupacion: list[dict[str, Any]] = []
    sin_finalizar = 0
    if not df.empty and "aforo_maximo" in df.columns:
        for _, fila in df.iterrows():
            aforo = int(fila.get("aforo_maximo") or 0)
            asist = int(fila.get("total_asistentes") or 0)
            if str(fila.get("estatus", "")) != "Finalizada":
                sin_finalizar += 1
            if aforo > 0:
                ocupacion.append(
                    {
                        "jornada": str(fila.get("nombre_jornada", "")),
                        "estatus": str(fila.get("estatus", "")),
                        "aforo": aforo,
                        "asistentes": asist,
                        "ocupacion_pct": _porcentaje(asist, aforo),
                    }
                )
        completa = [o for o in ocupacion if o["ocupacion_pct"] >= umbral_ocupacion]
        if completa:
            alertas.append(
                _alerta(
                    "advertencia",
                    _mensaje(conocimiento, "ALERTA_JORNADAS_AFORO", cantidad=len(completa)),
                )
            )
    if sin_finalizar:
        alertas.append(
            _alerta(
                "info",
                _mensaje(
                    conocimiento,
                    "ALERTA_JORNADAS_SIN_FINALIZAR",
                    cantidad=sin_finalizar,
                ),
            )
        )
    serie = _serie_mensual(df, "fecha_inicio")
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_estatus": por_estatus,
            "por_tipo": _distribucion(df, "tipo_jornada"),
        },
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
        "indicadores": {
            "asistentes_totales": asistentes,
            "diagnosticos_totales": diagnosticos,
            "jornadas_sin_finalizar": sin_finalizar,
            "ocupacion_por_jornada": ocupacion[:5],
        },
    }


def _transformar_mobiliario(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    df = extraccion.datos.get("bienes", pd.DataFrame())
    por_estatus = _distribucion(df, "estatus")
    inactivos = next((e["cantidad"] for e in por_estatus if e["valor"] == "Inactivo"), 0)
    if inactivos:
        alertas.append(
            _alerta(
                "info",
                _mensaje(conocimiento, "ALERTA_BIENES_INACTIVOS", cantidad=inactivos),
            )
        )
    suma_mobiliario = 0
    if not df.empty and "cantidad" in df.columns:
        solo_mob = (
            df[df["tipo_bien"].astype(str) == "Mobiliario"] if "tipo_bien" in df.columns else df
        )
        suma_mobiliario = int(pd.to_numeric(solo_mob["cantidad"], errors="coerce").fillna(0).sum())
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_tipo_bien": _distribucion(df, "tipo_bien"),
            "por_categoria": _distribucion(df, "categoria", limite=8),
            "por_estatus": por_estatus,
        },
        "comparativa": None,
        "serie_mensual": [],
        "indicadores": {"unidades_mobiliario": suma_mobiliario, "bienes_inactivos": inactivos},
    }


def _transformar_transporte(
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    alertas: list,
    conocimiento: BaseConocimiento,
) -> Resumen:
    del filtros
    resumen_secciones: dict[str, Any] = {}
    for nombre, df in extraccion.datos.items():
        resumen_secciones[nombre] = {"total_registros": extraccion.totales.get(nombre, 0)}
        if df.empty:
            continue
        if nombre == "vehiculos":
            por_estado = _distribucion(df, "estado")
            resumen_secciones[nombre]["por_estado"] = por_estado
            en_mantenimiento = next(
                (e["cantidad"] for e in por_estado if e["valor"] == "Mantenimiento"), 0
            )
            if en_mantenimiento:
                alertas.append(
                    _alerta(
                        "advertencia",
                        _mensaje(
                            conocimiento,
                            "ALERTA_VEHICULOS_MANTENIMIENTO",
                            cantidad=en_mantenimiento,
                        ),
                    )
                )
        elif nombre == "repuestos":
            umbral = _umbral(conocimiento, "STOCK_REPUESTOS_TRANSPORTE")
            columna_cantidad = (
                df["cantidad"] if "cantidad" in df.columns else pd.Series(dtype=float)
            )
            bajos = df[pd.to_numeric(columna_cantidad, errors="coerce").fillna(0) < umbral]
            resumen_secciones[nombre]["bajo_stock"] = len(bajos)
            resumen_secciones[nombre]["por_estatus"] = _distribucion(df, "estatus")
            if len(bajos):
                alertas.append(
                    _alerta(
                        "critico",
                        _mensaje(
                            conocimiento,
                            "ALERTA_REPUESTOS_BAJO_STOCK",
                            cantidad=len(bajos),
                            umbral=int(umbral),
                        ),
                    )
                )
        elif nombre == "rutas":
            resumen_secciones[nombre]["por_estatus"] = _distribucion(df, "estatus")
        elif nombre == "mantenimientos":
            resumen_secciones[nombre]["por_tipo"] = _distribucion(df, "tipo")
        elif nombre == "asignaciones" or nombre == "proveedores":
            resumen_secciones[nombre]["por_estatus"] = _distribucion(df, "estatus")
    return {
        "totales": extraccion.totales,
        "secciones": resumen_secciones,
        "distribuciones": {},
        "comparativa": None,
        "serie_mensual": [],
    }


_TRANSFORMADORES: dict[Modulo, Any] = {
    Modulo.GENERAL: _transformar_general,
    Modulo.MEDICINA: _transformar_medicina,
    Modulo.PSICOLOGIA: _transformar_psicologia,
    Modulo.ORIENTACION: _transformar_orientacion,
    Modulo.TRABAJO_SOCIAL: _transformar_trabajo_social,
    Modulo.DISCAPACIDAD: _transformar_discapacidad,
    Modulo.REFERENCIAS: _transformar_referencias,
    Modulo.JORNADAS: _transformar_jornadas,
    Modulo.MOBILIARIO: _transformar_mobiliario,
    Modulo.TRANSPORTE: _transformar_transporte,
}


def transformar(
    modulo: Modulo,
    extraccion: Extraccion,
    filtros: FiltrosDTO,
    conocimiento: BaseConocimiento | None = None,
) -> Resumen:
    kb = _kb(conocimiento)
    alertas: list[dict[str, str]] = []
    _montos_truncados(extraccion, alertas, kb)
    transformador = _TRANSFORMADORES[modulo]
    resumen: Resumen = transformador(extraccion, filtros, alertas, kb)
    if not any(extraccion.totales.values()):
        alertas.append(
            _alerta(
                "info",
                _mensaje(kb, "ALERTA_SIN_REGISTROS"),
            )
        )
    resumen["modulo"] = modulo.value
    resumen["periodo"] = _fechas_periodo(filtros)
    resumen["alertas"] = alertas
    resumen["registros_procesados"] = int(sum(extraccion.totales.values()))
    resumen["prediccion_ml"] = predecir_demanda(resumen.get("serie_mensual") or [])
    return resumen


def procesar(
    modulo: Modulo,
    filtros: FiltrosDTO,
    id_empleado: int | None,
    limit: int | None = None,
    adaptador: AdaptadorFuenteDatos | None = None,
    conocimiento: BaseConocimiento | None = None,
) -> Resumen:
    limite = limit or obtener_ajustes().limite_registros
    if adaptador is not None:
        extraccion = extraer(modulo, filtros, id_empleado, limite, adaptador)
    else:
        extraccion = extraer(modulo, filtros, id_empleado, limite)
    return transformar(modulo, extraccion, filtros, conocimiento=conocimiento)
