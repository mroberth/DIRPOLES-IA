from collections.abc import Callable

from app.db.queries import (
    discapacidad_queries,
    general_queries,
    jornadas_queries,
    medicina_queries,
    mobiliario_queries,
    orientacion_queries,
    psicologia_queries,
    referencias_queries,
    trabajo_social_queries,
    transporte_queries,
)
from app.db.queries._comunes import Consulta
from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO

Constructor = Callable[[FiltrosDTO, int | None], dict[str, Consulta]]

_CONSTRUCTORES: dict[Modulo, Constructor] = {
    Modulo.GENERAL: general_queries.general,
    Modulo.MEDICINA: medicina_queries.medicina,
    Modulo.PSICOLOGIA: psicologia_queries.psicologia,
    Modulo.ORIENTACION: orientacion_queries.orientacion,
    Modulo.TRABAJO_SOCIAL: trabajo_social_queries.trabajo_social,
    Modulo.DISCAPACIDAD: discapacidad_queries.discapacidad,
    Modulo.REFERENCIAS: referencias_queries.referencias,
    Modulo.JORNADAS: jornadas_queries.jornadas,
    Modulo.MOBILIARIO: mobiliario_queries.mobiliario,
    Modulo.TRANSPORTE: transporte_queries.transporte,
}


def obtener_consultas(
    modulo: Modulo,
    filtros: FiltrosDTO,
    id_empleado: int | None,
) -> dict[str, Consulta]:
    constructor = _CONSTRUCTORES[modulo]
    return constructor(filtros, id_empleado)


def sql_con_limit(consulta: Consulta, limit: int) -> tuple[str, dict[str, object]]:
    params: dict[str, object] = dict(consulta.params)
    params["limit"] = limit
    return f"{consulta.base} ORDER BY {consulta.orden} LIMIT :limit", params


def sql_total(consulta: Consulta) -> tuple[str, dict[str, object]]:
    return f"SELECT COUNT(*) AS total FROM ({consulta.base}) conteo", dict(consulta.params)
