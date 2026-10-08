from app.db.queries._comunes import (
    Consulta,
    Parametros,
    agregar_fechas,
    agregar_igual,
)
from app.db.queries.general_queries import puro
from app.schemas.request import FiltrosDTO


def mobiliario(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    del id_empleado
    params: Parametros = {}

    rama_mob = (
        "SELECT m.id_mobiliario, "
        "CONCAT(COALESCE(tm.nombre, 'Sin tipo'), ' — ', "
        "COALESCE(NULLIF(m.marca, ''), 'sin marca'), ' ', "
        "COALESCE(NULLIF(m.modelo, ''), 'sin modelo')) AS nombre_item, "
        "'Mobiliario' AS tipo_bien, COALESCE(tm.nombre, 'Sin tipo') AS categoria, "
        "m.cantidad, m.estatus, DATE(m.fecha_registro) AS fecha "
        "FROM mobiliario m "
        "LEFT JOIN tipo_mobiliario tm ON m.id_tipo_mobiliario = tm.id_tipo_mobiliario"
    )
    rama_eq = (
        "SELECT eq.id_equipo, "
        "CONCAT(COALESCE(te.nombre, 'Sin tipo'), ' — ', "
        "COALESCE(NULLIF(eq.marca, ''), 'sin marca'), ' ', "
        "COALESCE(NULLIF(eq.modelo, ''), 'sin modelo'), ' ', "
        "COALESCE(CONCAT('(', eq.serial, ')'), '')) AS nombre_item, "
        "'Equipo' AS tipo_bien, COALESCE(te.nombre, 'Sin tipo') AS categoria, "
        "1 AS cantidad, eq.estatus, DATE(eq.fecha_registro) AS fecha "
        "FROM equipos eq "
        "LEFT JOIN tipo_equipo te ON eq.id_tipo_equipo = te.id_tipo_equipo"
    )
    union = f"{rama_mob}\nUNION ALL\n{rama_eq}"

    cond_externas: list[str] = ["1 = 1"]
    agregar_fechas(cond_externas, params, "t.fecha", filtros)
    agregar_igual(cond_externas, params, "t.tipo_bien", "f_tipo_bien", puro(filtros.tipo_bien))
    agregar_igual(cond_externas, params, "t.estatus", "f_estado", filtros.estado)

    base = f"SELECT * FROM (\n{union}\n) t WHERE " + " AND ".join(cond_externas)
    return {
        "bienes": Consulta(base=base, orden="t.tipo_bien ASC, t.nombre_item ASC", params=params),
    }
