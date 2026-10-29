from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import pandas as pd


@dataclass
class Extraccion:
    """Contenedor desacoplado para datos extraídos y conteos totales."""

    datos: dict[str, pd.DataFrame]
    totales: dict[str, int]


@runtime_checkable
class AdaptadorFuenteDatos(Protocol):
    """Protocolo contractual para adaptadores de fuentes de datos.

    Cualquier sistema consumidor o repositorio de datos (SQL, API externa,
    payload en memoria) debe implementar esta interfaz para abastecer al
    motor analítico de DIRPOLES-IA sin acoplar el núcleo a esquemas particulares.
    """

    def extraer(
        self,
        modulo: Any,
        filtros: Any,
        id_empleado: int | None,
        limit: int,
    ) -> Extraccion: ...
