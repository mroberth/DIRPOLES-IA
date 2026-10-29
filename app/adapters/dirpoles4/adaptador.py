import pandas as pd

from app.adapters.base import AdaptadorFuenteDatos, Extraccion
from app.adapters.dirpoles4.queries import obtener_consultas, sql_con_limit, sql_total
from app.db import session
from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO


class AdaptadorDirpoles4SQL(AdaptadorFuenteDatos):
    """Adaptador de fuente de datos relacional para el monolito DIRPOLES-4.

    Encapsula el acceso de solo lectura (READ-ONLY) a los esquemas
    `dirpoles_business` y `dirpoles_security` de MySQL/MariaDB, ejecutando
    las consultas parametrizadas y aplicando la visibilidad por `id_empleado`.
    """

    def extraer(
        self,
        modulo: Modulo,
        filtros: FiltrosDTO,
        id_empleado: int | None,
        limit: int,
    ) -> Extraccion:
        consultas = obtener_consultas(modulo, filtros, id_empleado)
        datos: dict[str, pd.DataFrame] = {}
        totales: dict[str, int] = {}
        for nombre, consulta in consultas.items():
            sql_filas, params_filas = sql_con_limit(consulta, limit)
            datos[nombre] = session.consultar_dataframe(sql_filas, params_filas)
            sql_tot, params_tot = sql_total(consulta)
            totales[nombre] = session.contar(sql_tot, params_tot)
        return Extraccion(datos=datos, totales=totales)
