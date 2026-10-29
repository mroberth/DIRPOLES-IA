"""Módulo de salvaguarda y configuración segura para pruebas de integración con MySQL.

Impide de forma estricta la ejecución accidental de pruebas contra bases de datos
operativas o institucionales, exigiendo variables de conexión dedicadas y un esquema
aislado claramente identificado con prefijo o sufijo de prueba.
"""

from dataclasses import dataclass
import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from app.core.config import obtener_ajustes
from app.db import session

ESQUEMAS_OPERATIVOS_PROHIBIDOS: set[str] = {
    "dirpoles_business",
    "dirpoles_security",
    "dirpoles4",
    "dirpoles",
    "production",
    "produccion",
    "dirpoles_prod",
}


@dataclass(frozen=True)
class ConfiguracionPruebasBD:
    host: str
    port: int
    user: str
    password: str
    name_business: str
    name_security: str


def obtener_configuracion_pruebas_bd() -> ConfiguracionPruebasBD | None:
    """Extrae la configuración de pruebas desde variables de entorno específicas de test."""
    name_business = os.getenv("DIRPOLES_TEST_DB_NAME_BUSINESS") or os.getenv("DB_TEST_NAME_BUSINESS")
    name_security = os.getenv("DIRPOLES_TEST_DB_NAME_SECURITY") or os.getenv("DB_TEST_NAME_SECURITY")

    if not name_business or not name_security:
        return None

    host = os.getenv("DIRPOLES_TEST_DB_HOST") or os.getenv("DB_TEST_HOST") or "127.0.0.1"
    port_str = os.getenv("DIRPOLES_TEST_DB_PORT") or os.getenv("DB_TEST_PORT") or "3306"
    user = os.getenv("DIRPOLES_TEST_DB_USER") or os.getenv("DB_TEST_USER") or "dirpoles_test_user"
    password = os.getenv("DIRPOLES_TEST_DB_PASSWORD") or os.getenv("DB_TEST_PASSWORD") or ""

    try:
        port = int(port_str)
    except ValueError:
        port = 3306

    return ConfiguracionPruebasBD(
        host=host,
        port=port,
        user=user,
        password=password,
        name_business=name_business.strip(),
        name_security=name_security.strip(),
    )


def validar_seguridad_entorno_pruebas() -> tuple[bool, str, ConfiguracionPruebasBD | None]:
    """Valida de forma estricta que las pruebas no apunten a bases operativas.

    Retorna: (es_seguro, mensaje_diagnostico, configuracion)
    """
    flag_activa = os.getenv("DIRPOLES_TEST_BD", "0").strip() == "1"
    if not flag_activa:
        return (
            False,
            "Pruebas de integración omitidas: requiere 'DIRPOLES_TEST_BD=1' y configuración aislada en variables DIRPOLES_TEST_DB_*.",
            None,
        )

    config = obtener_configuracion_pruebas_bd()
    if config is None:
        return (
            False,
            "BLOQUEO DE SEGURIDAD: 'DIRPOLES_TEST_BD=1' está activo pero faltan variables de base de datos de prueba "
            "('DIRPOLES_TEST_DB_NAME_BUSINESS' y 'DIRPOLES_TEST_DB_NAME_SECURITY'). "
            "Está terminantemente prohibido reutilizar el archivo .env operativo para ejecutar pruebas de integración.",
            None,
        )

    # 1. Validación contra listas negras de esquemas operativos
    if config.name_business.lower() in ESQUEMAS_OPERATIVOS_PROHIBIDOS:
        return (
            False,
            f"BLOQUEO DE SEGURIDAD: El esquema de negocio '{config.name_business}' coincide con un esquema operativo institucional. "
            "Las pruebas de integración deben ejecutarse sobre un esquema de prueba aislado (ej. 'dirpoles_business_test').",
            None,
        )

    if config.name_security.lower() in ESQUEMAS_OPERATIVOS_PROHIBIDOS:
        return (
            False,
            f"BLOQUEO DE SEGURIDAD: El esquema de seguridad '{config.name_security}' coincide con un esquema operativo institucional. "
            "Las pruebas de integración deben ejecutarse sobre un esquema de prueba aislado (ej. 'dirpoles_security_test').",
            None,
        )

    # 2. Validación contra la configuración activa del .env operativo
    ajustes_operativos = obtener_ajustes()
    if config.name_business.lower() == ajustes_operativos.db_name_business.lower():
        return (
            False,
            f"BLOQUEO DE SEGURIDAD: El esquema de pruebas '{config.name_business}' es idéntico a db_name_business en .env. "
            "Debe usar un esquema de prueba separado.",
            None,
        )

    if config.name_security.lower() == ajustes_operativos.db_name_security.lower():
        return (
            False,
            f"BLOQUEO DE SEGURIDAD: El esquema de seguridad '{config.name_security}' es idéntico a db_name_security en .env. "
            "Debe usar un esquema de prueba separado.",
            None,
        )

    # 3. Validación de patrón de nombres: debe contener 'test' o 'prueba'
    if "test" not in config.name_business.lower() and "prueba" not in config.name_business.lower():
        return (
            False,
            f"BLOQUEO DE SEGURIDAD: El nombre de la base de datos '{config.name_business}' debe contener el prefijo/sufijo 'test' o 'prueba' "
            "para certificar que es un contenedor desechable de pruebas.",
            None,
        )

    return (True, "Entorno de pruebas aislado verificado y seguro.", config)


_motor_original: Engine | None = None
_ajustes_business_original: str | None = None
_ajustes_security_original: str | None = None


def activar_motor_pruebas(config: ConfiguracionPruebasBD) -> Engine:
    """Crea y conecta un motor SQLAlchemy temporal apuntando exclusivamente a la base de pruebas."""
    global _motor_original, _ajustes_business_original, _ajustes_security_original
    _motor_original = session._motor

    url = URL.create(
        drivername="mysql+pymysql",
        username=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        database=config.name_business,
        query={"charset": "utf8mb4"},
    )
    motor_test = create_engine(url, pool_pre_ping=True, future=True)
    session._motor = motor_test

    # Configurar esquemas temporales para consultas dinámicas
    ajustes = obtener_ajustes()
    _ajustes_business_original = ajustes.db_name_business
    _ajustes_security_original = ajustes.db_name_security
    ajustes.db_name_business = config.name_business
    ajustes.db_name_security = config.name_security

    return motor_test


def restaurar_motor_original() -> None:
    """Restaura el motor de sesión a su estado previo tras finalizar las pruebas de integración."""
    global _motor_original, _ajustes_business_original, _ajustes_security_original
    if session._motor is not None:
        try:
            session._motor.dispose()
        except Exception:
            pass
    session._motor = _motor_original

    if _ajustes_business_original is not None:
        obtener_ajustes().db_name_business = _ajustes_business_original
    if _ajustes_security_original is not None:
        obtener_ajustes().db_name_security = _ajustes_security_original
