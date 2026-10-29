from datetime import date
import unittest

from pydantic import ValidationError

from app.schemas.enums import Intencion, Modulo
from app.schemas.request import FiltrosDTO, ReporteRequestDTO


def _peticion(**kwargs: object) -> ReporteRequestDTO:
    base: dict[str, object] = {
        "modulo": "medicina",
        "intencion": "resumen_ejecutivo",
        "filtros": {},
    }
    base.update(kwargs)
    return ReporteRequestDTO.model_validate(base)


class TestSchemas(unittest.TestCase):
    def test_peticion_minima_valida(self) -> None:
        peticion = _peticion()
        self.assertIs(peticion.modulo, Modulo.MEDICINA)
        self.assertIs(peticion.intencion, Intencion.RESUMEN_EJECUTIVO)
        self.assertIsNone(peticion.id_empleado)
        self.assertIsNone(peticion.filtros.fecha_inicio)

    def test_modulo_invalido_rechazado(self) -> None:
        with self.assertRaises(ValidationError):
            _peticion(modulo="inexistente")

    def test_intencion_invalida_rechazada(self) -> None:
        with self.assertRaises(ValidationError):
            _peticion(intencion="otra")

    def test_fechas_invertidas_rechazadas(self) -> None:
        with self.assertRaises(ValidationError):
            FiltrosDTO(fecha_inicio=date(2026, 12, 1), fecha_fin=date(2026, 1, 1))

    def test_fechas_orden_validas(self) -> None:
        filtros = FiltrosDTO(fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31))
        self.assertLess(filtros.fecha_inicio, filtros.fecha_fin)

    def test_estado_con_caracteres_html_rechazado(self) -> None:
        with self.assertRaises(ValidationError):
            FiltrosDTO(estado="Pendiente<script>")

    def test_estado_en_blanco_se_normaliza_a_none(self) -> None:
        self.assertIsNone(FiltrosDTO(estado="   ").estado)

    def test_estado_catalogo_psicologia(self) -> None:
        peticion = _peticion(modulo="psicologia", filtros={"estado": "Pendiente"})
        self.assertEqual(peticion.filtros.estado, "Pendiente")

    def test_estado_fuera_de_catalogo_psicologia_rechazado(self) -> None:
        with self.assertRaises(ValidationError):
            _peticion(modulo="psicologia", filtros={"estado": "Activo"})

    def test_estado_libre_en_medicina_aceptado(self) -> None:
        peticion = _peticion(modulo="medicina", filtros={"estado": "Cualquier texto"})
        self.assertEqual(peticion.filtros.estado, "Cualquier texto")

    def test_genero_solo_m_o_f(self) -> None:
        self.assertEqual(_peticion(filtros={"genero": "F"}).filtros.genero.value, "F")
        with self.assertRaises(ValidationError):
            _peticion(filtros={"genero": "X"})

    def test_limit_fuera_de_rango_rechazado(self) -> None:
        with self.assertRaises(ValidationError):
            FiltrosDTO(limit=50000)

    def test_pnf_mayor_cero(self) -> None:
        self.assertEqual(FiltrosDTO(pnf=3).pnf, 3)
        with self.assertRaises(ValidationError):
            FiltrosDTO(pnf=0)


if __name__ == "__main__":
    unittest.main()
