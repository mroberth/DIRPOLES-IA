from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from app.core.config import obtener_ajustes
from app.db import queries, session
from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO

Resumen = dict[str, Any]


@dataclass
class Extraccion:
    datos: dict[str, pd.DataFrame]
    totales: dict[str, int]


def extraer(
    modulo: Modulo,
    filtros: FiltrosDTO,
    id_empleado: int | None,
    limit: int,
) -> Extraccion:
    consultas = queries.obtener_consultas(modulo, filtros, id_empleado)
    datos: dict[str, pd.DataFrame] = {}
    totales: dict[str, int] = {}
    for nombre, consulta in consultas.items():
        sql_filas, params_filas = queries.sql_con_limit(consulta, limit)
        datos[nombre] = session.consultar_dataframe(sql_filas, params_filas)
        sql_total, params_total = queries.sql_total(consulta)
        totales[nombre] = session.contar(sql_total, params_total)
    return Extraccion(datos=datos, totales=totales)


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


def _muestra(df: pd.DataFrame, columnas: list[str], cantidad: int = 5) -> list[dict[str, Any]]:
    if df.empty:
        return []
    presentes = [col for col in columnas if col in df.columns]
    if not presentes:
        presentes = list(df.columns)[:6]
    muestra = df[presentes].head(cantidad).copy()
    for col in presentes:
        if pd.api.types.is_datetime64_any_dtype(muestra[col]):
            muestra[col] = muestra[col].dt.strftime("%Y-%m-%d")
    return [
        {str(clave): (None if pd.isna(valor) else str(valor)) for clave, valor in fila.items()}
        for fila in muestra.to_dict(orient="records")
    ]


def _montos_truncados(extraccion: Extraccion, alertas: list[dict[str, str]]) -> None:
    for nombre, total in extraccion.totales.items():
        obtenidos = len(extraccion.datos.get(nombre, []))
        if total > obtenidos:
            alertas.append(
                _alerta(
                    "advertencia",
                    f"La colección '{nombre}' tiene {total} registros pero solo se analizaron "
                    f"{obtenidos} por el límite de filas configurado.",
                )
            )


def _insumos_alertas(insumos: pd.DataFrame, alertas: list[dict[str, str]]) -> dict[str, Any]:
    ajustes = obtener_ajustes()
    if insumos.empty:
        return {"vencidos": 0, "por_vencer_30_dias": 0, "stock_critico": []}
    vencidos = 0
    por_vencer = 0
    for fecha in insumos.get("fecha_vencimiento", pd.Series(dtype=object)):
        dias = _dias_hasta(fecha)
        if dias is None:
            continue
        if dias < 0:
            vencidos += 1
        elif dias <= 30:
            por_vencer += 1
    critico = insumos[
        insumos.get("cantidad", pd.Series(dtype=object)).fillna(0).astype(int)
        < ajustes.umbral_stock_critico_insumos
    ]
    if vencidos:
        alertas.append(
            _alerta("critico", f"{vencidos} insumo(s) con fecha de vencimiento vencida.")
        )
    if por_vencer:
        alertas.append(
            _alerta("advertencia", f"{por_vencer} insumo(s) vencen en los próximos 30 días.")
        )
    if len(critico):
        nombres = (
            ", ".join(str(n) for n in critico["nombre_insumo"].head(5))
            if "nombre_insumo" in critico
            else ""
        )
        alertas.append(
            _alerta(
                "critico",
                f"{len(critico)} insumo(s) por debajo del umbral crítico "
                f"({ajustes.umbral_stock_critico_insumos} unidades): {nombres}.",
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


def _transformar_general(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
    del filtros
    df = extraccion.datos.get("atenciones", pd.DataFrame())
    por_area = _distribucion(df, "area")
    if por_area:
        concentrada = por_area[0]
        if concentrada["porcentaje"] >= 40.0:
            alertas.append(
                _alerta(
                    "advertencia",
                    f"El área '{concentrada['valor']}' concentra el "
                    f"{concentrada['porcentaje']}% de las atenciones del periodo.",
                )
            )
    serie = _serie_mensual(df, "fecha")
    top = _top_concentracion(df, "diagnostico") if "diagnostico" in df.columns else []
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
        "ejemplos": _muestra(df, ["fecha", "nombres", "apellidos", "area", "nombre_pnf"]),
    }


def _transformar_medicina(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
    del filtros
    consultas = extraccion.datos.get("consultas", pd.DataFrame())
    insumos = extraccion.datos.get("insumos", pd.DataFrame())
    indicadores_insumos = _insumos_alertas(insumos, alertas)
    serie = _serie_mensual(consultas, "fecha")
    comp = _comparativa(serie)
    if comp and isinstance(comp.get("variacion_pct"), float) and comp["variacion_pct"] >= 25.0:
        alertas.append(
            _alerta(
                "advertencia",
                f"Las consultas médicas aumentaron un {comp['variacion_pct']}% "
                "respecto al mes anterior.",
            )
        )
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_genero": _distribucion(consultas, "genero", {"M": "Masculino", "F": "Femenino"}),
            "por_pnf": _distribucion(consultas, "nombre_pnf", limite=8),
            "top_diagnosticos": _distribucion(consultas, "diagnostico", limite=8),
            "top_motivos": _distribucion(consultas, "motivo", limite=8),
            "insumos_por_estatus": _distribucion(insumos, "estatus"),
        },
        "comparativa": comp,
        "serie_mensual": serie,
        "indicadores": {"insumos": indicadores_insumos},
        "ejemplos": _muestra(consultas, ["fecha", "nombres", "apellidos", "motivo", "diagnostico"]),
    }


def _transformar_psicologia(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
    del filtros
    morbilidad = extraccion.datos.get("morbilidad", pd.DataFrame())
    citas = extraccion.datos.get("citas", pd.DataFrame())
    por_estado = _distribucion(citas, "estado")
    pendientes = next((e["cantidad"] for e in por_estado if e["valor"] == "Pendiente"), 0)
    no_asistio = next((e["cantidad"] for e in por_estado if e["valor"] == "No asistió"), 0)
    total_citas = extraccion.totales.get("citas", 0)
    if pendientes:
        alertas.append(
            _alerta("advertencia", f"{pendientes} cita(s) en estado Pendiente sin atender.")
        )
    if total_citas and no_asistio and _porcentaje(no_asistio, total_citas) >= 15.0:
        alertas.append(
            _alerta(
                "critico",
                f"El {_porcentaje(no_asistio, total_citas)}% de las citas terminó en 'No asistió'.",
            )
        )
    top = _top_concentracion(morbilidad, "diagnostico")
    if top and top[0]["porcentaje"] >= 30.0:
        alertas.append(
            _alerta(
                "advertencia",
                f"El diagnóstico '{top[0]['valor']}' representa el {top[0]['porcentaje']}% "
                "de la morbilidad psicológica.",
            )
        )
    serie = _serie_mensual(morbilidad, "fecha")
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "morbilidad_por_tipo_consulta": _distribucion(morbilidad, "tipo_consulta"),
            "top_diagnosticos": _distribucion(morbilidad, "diagnostico", limite=8),
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
        "ejemplos": _muestra(
            morbilidad, ["fecha", "nombres", "apellidos", "tipo_consulta", "diagnostico"]
        ),
    }


def _transformar_orientacion(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
    del filtros, alertas
    df = extraccion.datos.get("casos", pd.DataFrame())
    serie = _serie_mensual(df, "fecha")
    return {
        "totales": extraccion.totales,
        "distribuciones": {
            "por_genero": _distribucion(df, "genero", {"M": "Masculino", "F": "Femenino"}),
            "por_pnf": _distribucion(df, "nombre_pnf", limite=8),
            "top_motivos": _distribucion(df, "motivo_consulta", limite=8),
        },
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
        "ejemplos": _muestra(df, ["fecha", "nombres", "apellidos", "motivo_consulta"]),
    }


def _transformar_trabajo_social(
    extraccion: Extraccion, filtros: FiltrosDTO, alertas: list
) -> Resumen:
    del filtros, alertas
    df = extraccion.datos.get("registros", pd.DataFrame())
    por_submodulo = _distribucion(df, "submodulo")
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
        "ejemplos": _muestra(df, ["fecha", "submodulo", "nombres", "apellidos", "detalle_extra"]),
    }


def _transformar_discapacidad(
    extraccion: Extraccion, filtros: FiltrosDTO, alertas: list
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
        alertas.append(_alerta("advertencia", f"{graves} caso(s) de discapacidad con grado Grave."))
    if total and con_carnet < total:
        faltantes = total - con_carnet
        alertas.append(
            _alerta("advertencia", f"{faltantes} registro(s) sin carnet de discapacidad asociado.")
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
        "ejemplos": _muestra(df, ["fecha", "nombres", "apellidos", "tipo_discapacidad", "grado"]),
    }


def _transformar_referencias(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
    del filtros
    df = extraccion.datos.get("remisiones", pd.DataFrame())
    por_estado = _distribucion(df, "estado")
    pendientes = next((e["cantidad"] for e in por_estado if e["valor"] == "Pendiente"), 0)
    total = extraccion.totales.get("remisiones", 0)
    if pendientes:
        alertas.append(
            _alerta(
                "advertencia",
                f"{pendientes} referencia(s) pendientes de resolución "
                f"({_porcentaje(pendientes, total)}% del total).",
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
        "ejemplos": _muestra(
            df,
            ["fecha", "nombres_benef", "apellidos_benef", "servicio_destino", "estado", "motivo"],
        ),
    }


def _transformar_jornadas(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
    del filtros
    df = extraccion.datos.get("jornadas", pd.DataFrame())
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
        completa = [o for o in ocupacion if o["ocupacion_pct"] >= 100.0]
        if completa:
            alertas.append(
                _alerta(
                    "advertencia",
                    f"{len(completa)} jornada(s) alcanzaron o superaron el 100% del aforo.",
                )
            )
    if sin_finalizar:
        alertas.append(
            _alerta("info", f"{sin_finalizar} jornada(s) aún no están en estatus Finalizada.")
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
        "ejemplos": _muestra(
            df,
            [
                "nombre_jornada",
                "tipo_jornada",
                "fecha_inicio",
                "estatus",
                "aforo_maximo",
                "total_asistentes",
            ],
        ),
    }


def _transformar_mobiliario(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
    del filtros
    df = extraccion.datos.get("bienes", pd.DataFrame())
    por_estatus = _distribucion(df, "estatus")
    inactivos = next((e["cantidad"] for e in por_estatus if e["valor"] == "Inactivo"), 0)
    if inactivos:
        alertas.append(
            _alerta("info", f"{inactivos} bien(es) marcados como Inactivo en el inventario.")
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
        "ejemplos": _muestra(df, ["tipo_bien", "nombre_item", "categoria", "cantidad", "estatus"]),
    }


def _transformar_transporte(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
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
                        "advertencia", f"{en_mantenimiento} vehículo(s) en estado Mantenimiento."
                    )
                )
        elif nombre == "repuestos":
            umbral = obtener_ajustes().umbral_stock_critico_repuestos
            columna_cantidad = (
                df["cantidad"] if "cantidad" in df.columns else pd.Series(dtype=float)
            )
            bajos = df[pd.to_numeric(columna_cantidad, errors="coerce").fillna(0) < umbral]
            resumen_secciones[nombre]["bajo_stock"] = len(bajos)
            resumen_secciones[nombre]["por_estatus"] = _distribucion(df, "estatus")
            if len(bajos):
                nombres = (
                    ", ".join(str(n) for n in bajos["nombre"].head(5)) if "nombre" in bajos else ""
                )
                alertas.append(
                    _alerta(
                        "critico",
                        f"{len(bajos)} repuesto(s) con cantidad menor a {umbral}: {nombres}.",
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
        "ejemplos": {},
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
) -> Resumen:
    alertas: list[dict[str, str]] = []
    _montos_truncados(extraccion, alertas)
    transformador = _TRANSFORMADORES[modulo]
    resumen: Resumen = transformador(extraccion, filtros, alertas)
    if not any(extraccion.totales.values()):
        alertas.append(
            _alerta("info", "No se encontraron registros que cumplan los filtros seleccionados.")
        )
    resumen["modulo"] = modulo.value
    resumen["periodo"] = _fechas_periodo(filtros)
    resumen["alertas"] = alertas
    resumen["registros_procesados"] = int(sum(extraccion.totales.values()))
    return resumen


def procesar(
    modulo: Modulo,
    filtros: FiltrosDTO,
    id_empleado: int | None,
    limit: int | None = None,
) -> Resumen:
    limite = limit or obtener_ajustes().limite_registros
    extraccion = extraer(modulo, filtros, id_empleado, limite)
    return transformar(modulo, extraccion, filtros)
