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


def orientacion(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    cond: list[str] = ["1 = 1"]
    params: Parametros = {}
    agregar_fechas(cond, params, "o.fecha_creacion", filtros)
    agregar_igual(cond, params, "b.genero", "f_genero", puro(filtros.genero))
    agregar_igual(cond, params, "b.id_pnf", "f_pnf", filtros.pnf)
    agregar_empleado(cond, params, "ss.id_empleado", id_empleado)

    base = (
        "SELECT o.id_orientacion, o.fecha_creacion AS fecha, b.nombres, b.apellidos, "
        "CONCAT(b.tipo_cedula, '-', b.cedula) AS cedula, b.genero, b.id_pnf, pnf.nombre_pnf, "
        "o.motivo_orientacion AS motivo_consulta, "
        "o.descripcion_orientacion AS descripcion_caso, "
        "o.indicaciones_orientacion AS indicaciones "
        "FROM orientacion o "
        "JOIN solicitud_de_servicio ss ON o.id_solicitud_serv = ss.id_solicitud_serv "
        "JOIN beneficiario b ON ss.id_beneficiario = b.id_beneficiario "
        "LEFT JOIN pnf ON b.id_pnf = pnf.id_pnf" + clausula_where(cond)
    )

    return {
        "casos": Consulta(
            base=base,
            orden="o.fecha_creacion DESC, o.id_orientacion DESC",
            params=params,
        ),
    }
