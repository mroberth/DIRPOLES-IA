from app.db.queries._comunes import (
    Consulta,
    Parametros,
    agregar_empleado,
    agregar_fechas,
    agregar_igual,
    clausula_where,
)
from app.db.queries.general_queries import puro
from app.schemas.request import FiltrosDTO


def medicina(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    consultas_cond: list[str] = ["1 = 1"]
    consultas_params: Parametros = {}
    agregar_fechas(consultas_cond, consultas_params, "cm.fecha_creacion", filtros)
    agregar_igual(consultas_cond, consultas_params, "b.genero", "f_genero", puro(filtros.genero))
    agregar_igual(consultas_cond, consultas_params, "b.id_pnf", "f_pnf", filtros.pnf)
    agregar_empleado(consultas_cond, consultas_params, "ss.id_empleado", id_empleado)

    consultas_base = (
        "SELECT cm.id_consulta_med, cm.fecha_creacion AS fecha, b.nombres, b.apellidos, "
        "CONCAT(b.tipo_cedula, '-', b.cedula) AS cedula, b.genero, b.id_pnf, pnf.nombre_pnf, "
        "cm.motivo_visita AS motivo, cm.diagnostico, cm.tratamiento "
        "FROM consulta_medica cm "
        "JOIN solicitud_de_servicio ss ON cm.id_solicitud_serv = ss.id_solicitud_serv "
        "JOIN beneficiario b ON ss.id_beneficiario = b.id_beneficiario "
        "LEFT JOIN pnf ON b.id_pnf = pnf.id_pnf " + clausula_where(consultas_cond)
    )

    insumos_cond: list[str] = ["1 = 1"]
    insumos_params: Parametros = {}
    agregar_fechas(insumos_cond, insumos_params, "i.fecha_creacion", filtros)
    insumos_base = (
        "SELECT i.id_insumo, i.nombre_insumo, i.tipo_insumo, "
        "pi.nombre_presentacion AS presentacion, i.cantidad, i.fecha_vencimiento, "
        "CASE WHEN i.fecha_vencimiento < CURDATE() THEN 'Vencido' ELSE i.estatus END AS estatus "
        "FROM insumos i "
        "LEFT JOIN presentacion_insumo pi ON i.id_presentacion = pi.id_presentacion"
        + clausula_where(insumos_cond)
    )

    return {
        "consultas": Consulta(
            base=consultas_base,
            orden="cm.fecha_creacion DESC, cm.id_consulta_med DESC",
            params=consultas_params,
        ),
        "insumos": Consulta(
            base=insumos_base,
            orden="i.fecha_vencimiento ASC, i.nombre_insumo ASC",
            params=insumos_params,
        ),
    }
