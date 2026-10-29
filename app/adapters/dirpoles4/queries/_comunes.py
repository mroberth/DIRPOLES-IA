from dataclasses import dataclass
from typing import Any

from app.schemas.request import FiltrosDTO

Parametros = dict[str, Any]


@dataclass(frozen=True)
class Consulta:
    base: str
    orden: str
    params: Parametros


def agregar_fechas(
    condiciones: list[str],
    params: Parametros,
    columna: str,
    filtros: FiltrosDTO,
) -> None:
    if filtros.fecha_inicio is not None:
        condiciones.append(f"DATE({columna}) >= :f_desde")
        params["f_desde"] = filtros.fecha_inicio
    if filtros.fecha_fin is not None:
        condiciones.append(f"DATE({columna}) <= :f_hasta")
        params["f_hasta"] = filtros.fecha_fin


def agregar_igual(
    condiciones: list[str],
    params: Parametros,
    columna: str,
    parametro: str,
    valor: Any,
) -> None:
    if valor is not None:
        condiciones.append(f"{columna} = :{parametro}")
        params[parametro] = valor


def agregar_empleado(
    condiciones: list[str],
    params: Parametros,
    columna: str,
    id_empleado: int | None,
) -> None:
    if id_empleado is not None:
        condiciones.append(f"{columna} = :id_empleado")
        params["id_empleado"] = id_empleado


def clausula_where(condiciones: list[str]) -> str:
    if not condiciones:
        return ""
    return " WHERE " + " AND ".join(condiciones)
