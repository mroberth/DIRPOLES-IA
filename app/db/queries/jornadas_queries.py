from app.db.queries._comunes import (
    Consulta,
    Parametros,
    agregar_fechas,
    agregar_igual,
    clausula_where,
)
from app.schemas.request import FiltrosDTO


def jornadas(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    del id_empleado
    cond: list[str] = ["1 = 1"]
    params: Parametros = {}
    agregar_fechas(cond, params, "j.fecha_inicio", filtros)
    agregar_igual(cond, params, "j.estatus", "f_estado", filtros.estado)

    base = (
        "SELECT j.id_jornada, j.nombre_jornada, j.tipo_jornada, j.ubicacion, "
        "j.fecha_inicio, j.fecha_fin, j.estatus, j.aforo_maximo, "
        "(SELECT COUNT(*) FROM jornada_beneficiarios jb "
        "WHERE jb.id_jornada = j.id_jornada) AS total_asistentes, "
        "(SELECT COUNT(*) FROM jornada_diagnosticos jd "
        "JOIN jornada_beneficiarios jb2 "
        "ON jd.id_jornada_beneficiario = jb2.id_jornada_beneficiario "
        "WHERE jb2.id_jornada = j.id_jornada) AS total_diagnosticos "
        "FROM jornadas_medicas j" + clausula_where(cond)
    )

    return {
        "jornadas": Consulta(
            base=base,
            orden="j.fecha_inicio DESC, j.id_jornada DESC",
            params=params,
        ),
    }
