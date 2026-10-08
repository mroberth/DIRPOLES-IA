from app.db.queries._comunes import (
    Consulta,
    Parametros,
    agregar_fechas,
    agregar_igual,
    clausula_where,
)
from app.schemas.request import FiltrosDTO


def referencias(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    del id_empleado
    cond: list[str] = ["1 = 1"]
    params: Parametros = {}
    agregar_fechas(cond, params, "r.fecha_referencia", filtros)
    agregar_igual(cond, params, "r.estado", "f_estado", filtros.estado)
    agregar_igual(
        cond, params, "r.id_servicio_destino", "f_servicio_destino", filtros.servicio_destino
    )

    base = (
        "SELECT r.id_referencia, r.fecha_referencia AS fecha, r.estado, "
        "b.nombres AS nombres_benef, b.apellidos AS apellidos_benef, "
        "CONCAT(b.tipo_cedula, '-', b.cedula) AS cedula_benef, "
        "so.nombre_serv AS servicio_origen, sd.nombre_serv AS servicio_destino, r.motivo "
        "FROM referencias r "
        "JOIN beneficiario b ON r.id_beneficiario = b.id_beneficiario "
        "JOIN servicio so ON r.id_servicio_origen = so.id_servicios "
        "JOIN servicio sd ON r.id_servicio_destino = sd.id_servicios" + clausula_where(cond)
    )

    return {
        "remisiones": Consulta(
            base=base,
            orden="r.fecha_referencia DESC, r.id_referencia DESC",
            params=params,
        ),
    }
