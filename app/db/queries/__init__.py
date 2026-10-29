"""Capa de compatibilidad hacia atrás para consultas SQL de DIRPOLES-4.

Las consultas y constructores han sido encapsulados en el adaptador
específico `app.adapters.dirpoles4.queries`. Este módulo mantiene la
interfaz pública idéntica para preservar la compatibilidad con el código
y las pruebas existentes.
"""

from app.adapters.dirpoles4.queries import (  # noqa: F401
    _CONSTRUCTORES,
    Consulta,
    Constructor,
    discapacidad_queries,
    general_queries,
    jornadas_queries,
    medicina_queries,
    mobiliario_queries,
    obtener_consultas,
    orientacion_queries,
    psicologia_queries,
    referencias_queries,
    sql_con_limit,
    sql_total,
    trabajo_social_queries,
    transporte_queries,
)

__all__ = [
    "Consulta",
    "Constructor",
    "_CONSTRUCTORES",
    "obtener_consultas",
    "sql_con_limit",
    "sql_total",
    "discapacidad_queries",
    "general_queries",
    "jornadas_queries",
    "medicina_queries",
    "mobiliario_queries",
    "orientacion_queries",
    "psicologia_queries",
    "referencias_queries",
    "trabajo_social_queries",
    "transporte_queries",
]
