from app.core.config import obtener_ajustes
from app.db.queries._comunes import (
    Consulta,
    Parametros,
    agregar_fechas,
    agregar_igual,
    clausula_where,
)
from app.db.queries.general_queries import puro
from app.schemas.enums import SeccionTransporte
from app.schemas.request import FiltrosDTO


def transporte(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    del id_empleado
    seguridad = obtener_ajustes().db_name_security
    seccion = filtros.seccion_transporte
    consultas: dict[str, Consulta] = {}

    if seccion in (None, SeccionTransporte.VEHICULOS):
        cond: list[str] = ["1 = 1"]
        params: Parametros = {}
        agregar_fechas(cond, params, "v.fecha_adquisicion", filtros)
        agregar_igual(cond, params, "v.estado", "f_estado", filtros.estado)
        agregar_igual(cond, params, "v.tipo", "f_tipo_vehiculo", puro(filtros.tipo_vehiculo))
        base = (
            "SELECT v.id_vehiculo, v.placa, v.modelo, v.tipo, v.estado, v.fecha_adquisicion, "
            "(SELECT COUNT(*) FROM asignaciones_rutas ar "
            "WHERE ar.id_vehiculo = v.id_vehiculo AND ar.estatus = 'Activa') "
            "AS asignaciones_activas, "
            "(SELECT COUNT(*) FROM mantenimiento_vehiculos mv "
            "WHERE mv.id_vehiculo = v.id_vehiculo) AS total_mantenimientos "
            "FROM vehiculos v" + clausula_where(cond)
        )
        consultas["vehiculos"] = Consulta(base=base, orden="v.placa ASC", params=params)

    if seccion in (None, SeccionTransporte.RUTAS):
        cond = ["1 = 1"]
        params = {}
        agregar_fechas(cond, params, "r.fecha_creacion", filtros)
        agregar_igual(cond, params, "r.estatus", "f_estado", filtros.estado)
        base = (
            "SELECT r.id_ruta, r.nombre_ruta, r.tipo_ruta, r.punto_partida, r.punto_destino, "
            "r.estatus, r.fecha_creacion, "
            "(SELECT COUNT(*) FROM asignaciones_rutas ar "
            "WHERE ar.id_ruta = r.id_ruta AND ar.estatus = 'Activa') AS asignaciones_activas "
            "FROM rutas r" + clausula_where(cond)
        )
        consultas["rutas"] = Consulta(base=base, orden="r.nombre_ruta ASC", params=params)

    if seccion in (None, SeccionTransporte.PROVEEDORES):
        cond = ["1 = 1"]
        params = {}
        agregar_fechas(cond, params, "p.fecha_creacion", filtros)
        agregar_igual(cond, params, "p.estatus", "f_estado", filtros.estado)
        base = (
            "SELECT p.id_proveedor, p.nombre, p.tipo_documento, p.num_documento, p.telefono, "
            "p.correo, p.estatus, p.fecha_creacion "
            "FROM proveedores p" + clausula_where(cond)
        )
        consultas["proveedores"] = Consulta(base=base, orden="p.nombre ASC", params=params)

    if seccion in (None, SeccionTransporte.REPUESTOS):
        cond = ["1 = 1"]
        params = {}
        agregar_fechas(cond, params, "rp.fecha_creacion", filtros)
        agregar_igual(cond, params, "rp.estatus", "f_estado", filtros.estado)
        base = (
            "SELECT rp.id_repuesto, rp.nombre, rp.cantidad, rp.estatus, rp.fecha_creacion, "
            "p.nombre AS proveedor "
            "FROM repuestos_vehiculos rp "
            "LEFT JOIN proveedores p ON rp.id_proveedor = p.id_proveedor" + clausula_where(cond)
        )
        consultas["repuestos"] = Consulta(base=base, orden="rp.nombre ASC", params=params)

    if seccion in (None, SeccionTransporte.ASIGNACIONES):
        cond = ["1 = 1"]
        params = {}
        agregar_fechas(cond, params, "ar.fecha_asignacion", filtros)
        agregar_igual(cond, params, "ar.estatus", "f_estado", filtros.estado)
        base = (
            "SELECT ar.id_asignacion, ar.fecha_asignacion, ar.estatus, "
            "r.nombre_ruta AS nombre_ruta, v.placa, v.modelo, "
            "CONCAT(e.nombre, ' ', e.apellido) AS chofer, e.cedula AS cedula_chofer "
            "FROM asignaciones_rutas ar "
            "JOIN rutas r ON ar.id_ruta = r.id_ruta "
            "JOIN vehiculos v ON ar.id_vehiculo = v.id_vehiculo "
            f"LEFT JOIN {seguridad}.empleado e ON e.id_empleado = ar.id_empleado"
            + clausula_where(cond)
        )
        consultas["asignaciones"] = Consulta(
            base=base, orden="ar.fecha_asignacion DESC", params=params
        )

    if seccion in (None, SeccionTransporte.MANTENIMIENTOS):
        cond = ["1 = 1"]
        params = {}
        agregar_fechas(cond, params, "mv.fecha", filtros)
        base = (
            "SELECT mv.id_mantenimiento, mv.tipo, mv.fecha, mv.descripcion, "
            "v.placa, v.modelo, v.tipo AS tipo_vehiculo "
            "FROM mantenimiento_vehiculos mv "
            "JOIN vehiculos v ON mv.id_vehiculo = v.id_vehiculo" + clausula_where(cond)
        )
        consultas["mantenimientos"] = Consulta(base=base, orden="mv.fecha DESC", params=params)

    return consultas
