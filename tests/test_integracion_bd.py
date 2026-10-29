import unittest

from app.db import session
from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO
from app.services import etl_service
from tests.guard_integracion_bd import (
    activar_motor_pruebas,
    restaurar_motor_original,
    validar_seguridad_entorno_pruebas,
)


class TestIntegracionBD(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        seguro, motivo, config = validar_seguridad_entorno_pruebas()
        if not seguro or config is None:
            raise unittest.SkipTest(motivo)

        try:
            activar_motor_pruebas(config)
            if not session.ping():
                restaurar_motor_original()
                raise unittest.SkipTest(
                    f"Instancia MySQL de pruebas en {config.host}:{config.port} no responde o no tiene creados "
                    f"los esquemas '{config.name_business}'/'{config.name_security}'."
                )
        except Exception as exc:
            restaurar_motor_original()
            raise unittest.SkipTest(f"Fallo al conectar al entorno de pruebas aislado: {exc}")

    @classmethod
    def tearDownClass(cls) -> None:
        restaurar_motor_original()

    def test_ping_bd(self) -> None:
        self.assertTrue(session.ping())

    def test_consulta_general_ejecuta(self) -> None:
        resumen = etl_service.procesar(Modulo.GENERAL, FiltrosDTO(), id_empleado=None, limit=100)
        self.assertEqual(resumen["modulo"], "general")
        self.assertIn("atenciones", resumen["totales"])
        self.assertIsInstance(resumen["registros_procesados"], int)

    def test_todos_los_modulos_extraen_sin_error(self) -> None:
        modulos = [
            Modulo.MEDICINA,
            Modulo.PSICOLOGIA,
            Modulo.ORIENTACION,
            Modulo.TRABAJO_SOCIAL,
            Modulo.DISCAPACIDAD,
            Modulo.REFERENCIAS,
            Modulo.JORNADAS,
            Modulo.MOBILIARIO,
            Modulo.TRANSPORTE,
        ]
        for modulo in modulos:
            with self.subTest(modulo=modulo):
                filtros = FiltrosDTO(fecha_inicio="2020-01-01", fecha_fin="2030-12-31")
                resumen = etl_service.procesar(modulo, filtros, id_empleado=None, limit=100)
                self.assertEqual(resumen["modulo"], modulo.value)
                self.assertIn("alertas", resumen)
                self.assertIn("totales", resumen)

    def test_filtro_por_id_empleado_restringe_resultados(self) -> None:
        sin_filtro = etl_service.procesar(Modulo.GENERAL, FiltrosDTO(), id_empleado=None, limit=100)
        con_filtro = etl_service.procesar(Modulo.GENERAL, FiltrosDTO(), id_empleado=999999, limit=100)
        self.assertLessEqual(con_filtro["totales"]["atenciones"], sin_filtro["totales"]["atenciones"])
        self.assertEqual(con_filtro["totales"]["atenciones"], 0)


if __name__ == "__main__":
    unittest.main()
