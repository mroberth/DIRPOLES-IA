from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

from app.core.config import obtener_ajustes

_motor: Engine | None = None


def obtener_motor() -> Engine:
    global _motor
    if _motor is None:
        aj = obtener_ajustes()
        url = URL.create(
            drivername="mysql+pymysql",
            username=aj.db_user,
            password=aj.db_password,
            host=aj.db_host,
            port=aj.db_port,
            database=aj.db_name_business,
            query={"charset": "utf8mb4"},
        )
        _motor = create_engine(url, pool_pre_ping=True, pool_recycle=1800, future=True)
    return _motor


def consultar(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with obtener_motor().connect() as conexion:
        resultado = conexion.execute(text(sql), params or {})
        return [dict(fila) for fila in resultado.mappings()]


def contar(sql: str, params: dict[str, Any] | None = None) -> int:
    filas = consultar(sql, params)
    if not filas:
        return 0
    valor = next(iter(filas[0].values()))
    return int(valor or 0)


def consultar_dataframe(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    return pd.DataFrame(consultar(sql, params))


def ping() -> bool:
    try:
        consultar("SELECT 1 AS ok")
        return True
    except Exception:
        return False


def cerrar_motor() -> None:
    global _motor
    if _motor is not None:
        _motor.dispose()
        _motor = None
