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


def discapacidad(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    cond: list[str] = ["1 = 1"]
    params: Parametros = {}
    agregar_fechas(cond, params, "d.fecha_creacion", filtros)
    agregar_igual(cond, params, "b.genero", "f_genero", puro(filtros.genero))
    agregar_igual(cond, params, "b.id_pnf", "f_pnf", filtros.pnf)
    agregar_igual(cond, params, "d.tipo_discapacidad", "f_tipo", puro(filtros.tipo_discapacidad))
    agregar_igual(cond, params, "d.grado", "f_grado", puro(filtros.grado))
    agregar_empleado(cond, params, "ss.id_empleado", id_empleado)

    base = (
        "SELECT d.id_discapacidad, d.fecha_creacion AS fecha, b.nombres, b.apellidos, "
        "CONCAT(b.tipo_cedula, '-', b.cedula) AS cedula, b.genero, b.id_pnf, pnf.nombre_pnf, "
        "d.tipo_discapacidad, d.grado, d.requiere_asistencia, d.carnet_discapacidad "
        "FROM discapacidad d "
        "JOIN solicitud_de_servicio ss ON d.id_solicitud_serv = ss.id_solicitud_serv "
        "JOIN beneficiario b ON ss.id_beneficiario = b.id_beneficiario "
        "LEFT JOIN pnf ON b.id_pnf = pnf.id_pnf" + clausula_where(cond)
    )

    return {
        "registros": Consulta(
            base=base,
            orden="d.fecha_creacion DESC, d.id_discapacidad DESC",
            params=params,
        ),
    }
