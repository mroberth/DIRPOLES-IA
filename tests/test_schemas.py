from datetime import date

import pytest
from app.schemas.enums import Intencion, Modulo
from app.schemas.request import FiltrosDTO, ReporteRequestDTO
from pydantic import ValidationError


def _peticion(**kwargs: object) -> ReporteRequestDTO:
    base: dict[str, object] = {
        "modulo": "medicina",
        "intencion": "resumen_ejecutivo",
        "filtros": {},
    }
    base.update(kwargs)
    return ReporteRequestDTO.model_validate(base)


def test_peticion_minima_valida() -> None:
    peticion = _peticion()
    assert peticion.modulo is Modulo.MEDICINA
    assert peticion.intencion is Intencion.RESUMEN_EJECUTIVO
    assert peticion.id_empleado is None
    assert peticion.filtros.fecha_inicio is None


def test_modulo_invalido_rechazado() -> None:
    with pytest.raises(ValidationError):
        _peticion(modulo="inexistente")


def test_intencion_invalida_rechazada() -> None:
    with pytest.raises(ValidationError):
        _peticion(intencion="otra")


def test_fechas_invertidas_rechazadas() -> None:
    with pytest.raises(ValidationError):
        FiltrosDTO(fecha_inicio=date(2026, 12, 1), fecha_fin=date(2026, 1, 1))


def test_fechas_orden_validas() -> None:
    filtros = FiltrosDTO(fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31))
    assert filtros.fecha_inicio < filtros.fecha_fin


def test_estado_con_caracteres_html_rechazado() -> None:
    with pytest.raises(ValidationError):
        FiltrosDTO(estado="Pendiente<script>")


def test_estado_en_blanco_se_normaliza_a_none() -> None:
    assert FiltrosDTO(estado="   ").estado is None


def test_estado_catalogo_psicologia() -> None:
    peticion = _peticion(modulo="psicologia", filtros={"estado": "Pendiente"})
    assert peticion.filtros.estado == "Pendiente"


def test_estado_fuera_de_catalogo_psicologia_rechazado() -> None:
    with pytest.raises(ValidationError):
        _peticion(modulo="psicologia", filtros={"estado": "Activo"})


def test_estado_libre_en_medicina_aceptado() -> None:
    peticion = _peticion(modulo="medicina", filtros={"estado": "Cualquier texto"})
    assert peticion.filtros.estado == "Cualquier texto"


def test_genero_solo_m_o_f() -> None:
    assert _peticion(filtros={"genero": "F"}).filtros.genero.value == "F"
    with pytest.raises(ValidationError):
        _peticion(filtros={"genero": "X"})


def test_limit_fuera_de_rango_rechazado() -> None:
    with pytest.raises(ValidationError):
        FiltrosDTO(limit=50000)


def test_pnf_mayor_cero() -> None:
    assert FiltrosDTO(pnf=3).pnf == 3
    with pytest.raises(ValidationError):
        FiltrosDTO(pnf=0)
