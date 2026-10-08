import pytest
from app.db import session
from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO
from app.services import etl_service

pytestmark = pytest.mark.bd


def test_ping_bd() -> None:
    assert session.ping() is True


def test_consulta_general_ejecuta() -> None:
    resumen = etl_service.procesar(Modulo.GENERAL, FiltrosDTO(), id_empleado=None, limit=100)
    assert resumen["modulo"] == "general"
    assert "atenciones" in resumen["totales"]
    assert isinstance(resumen["registros_procesados"], int)


@pytest.mark.parametrize(
    "modulo",
    [
        Modulo.MEDICINA,
        Modulo.PSICOLOGIA,
        Modulo.ORIENTACION,
        Modulo.TRABAJO_SOCIAL,
        Modulo.DISCAPACIDAD,
        Modulo.REFERENCIAS,
        Modulo.JORNADAS,
        Modulo.MOBILIARIO,
        Modulo.TRANSPORTE,
    ],
)
def test_todos_los_modulos_extraen_sin_error(modulo: Modulo) -> None:
    filtros = FiltrosDTO(fecha_inicio="2020-01-01", fecha_fin="2030-12-31")
    resumen = etl_service.procesar(modulo, filtros, id_empleado=None, limit=100)
    assert resumen["modulo"] == modulo.value
    assert "alertas" in resumen
    assert "totales" in resumen


def test_filtro_por_id_empleado_restringe_resultados() -> None:
    sin_filtro = etl_service.procesar(Modulo.GENERAL, FiltrosDTO(), id_empleado=None, limit=100)
    con_filtro = etl_service.procesar(Modulo.GENERAL, FiltrosDTO(), id_empleado=999999, limit=100)
    assert con_filtro["totales"]["atenciones"] <= sin_filtro["totales"]["atenciones"]
    assert con_filtro["totales"]["atenciones"] == 0
