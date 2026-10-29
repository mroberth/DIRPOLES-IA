import unittest

from fastapi.testclient import TestClient

from app.core.config import obtener_ajustes
from app.db import session
from app.main import crear_app
from tests.guard_integracion_bd import (
    activar_motor_pruebas,
    restaurar_motor_original,
    validar_seguridad_entorno_pruebas,
)

CLAVE_TEST = "clave-b2b-de-prueba"


class TestFlujoBDApi(unittest.TestCase):
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

    def setUp(self) -> None:
        self.ajustes = obtener_ajustes()
        self.orig_mock_llm = self.ajustes.mock_llm
        self.orig_api_key = self.ajustes.dirpoles_ia_api_key
        self.ajustes.mock_llm = True
        self.ajustes.dirpoles_ia_api_key = CLAVE_TEST

        self.app = crear_app()
        self.cliente = TestClient(self.app)
        self.cliente.headers.update({"X-API-Key": CLAVE_TEST})

    def tearDown(self) -> None:
        self.ajustes.mock_llm = self.orig_mock_llm
        self.ajustes.dirpoles_ia_api_key = self.orig_api_key

    def test_generar_reporte_medicina_end_to_end(self) -> None:
        respuesta = self.cliente.post(
            "/api/v1/reportes/generar",
            json={
                "modulo": "medicina",
                "intencion": "alertas_y_anomalias",
                "filtros": {"fecha_inicio": "2020-01-01", "fecha_fin": "2030-12-31"},
                "observacion_usuario": "Enfocarse en insumos con bajo stock.",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertTrue(cuerpo["exito"])
        self.assertEqual(cuerpo["modulo"], "medicina")
        self.assertEqual(cuerpo["intencion"], "alertas_y_anomalias")
        self.assertIn("Resumen Ejecutivo", cuerpo["informe_markdown"])
        self.assertGreaterEqual(cuerpo["meta"]["registros_procesados"], 0)
        self.assertIn(cuerpo["meta"]["modo_informe"], {"simulado", "gemini", "simulado_fallback"})
        self.assertGreaterEqual(cuerpo["meta"]["tiempo_procesamiento_seg"], 0)

    def test_generar_los_10_modulos(self) -> None:
        modulos = [
            "general",
            "medicina",
            "psicologia",
            "orientacion",
            "trabajo_social",
            "discapacidad",
            "referencias",
            "jornadas",
            "mobiliario",
            "transporte",
        ]
        for modulo in modulos:
            with self.subTest(modulo=modulo):
                respuesta = self.cliente.post(
                    "/api/v1/reportes/generar",
                    json={
                        "modulo": modulo,
                        "intencion": "resumen_ejecutivo",
                        "filtros": {"fecha_inicio": "2020-01-01", "fecha_fin": "2030-12-31"},
                    },
                )
                self.assertEqual(respuesta.status_code, 200, respuesta.text)
                self.assertTrue(respuesta.json()["exito"])

    def test_generar_con_filtros_avanzados(self) -> None:
        respuesta = self.cliente.post(
            "/api/v1/reportes/generar",
            json={
                "modulo": "transporte",
                "intencion": "recomendaciones",
                "filtros": {"seccion_transporte": "Repuestos", "estado": "Disponible"},
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["exito"])


if __name__ == "__main__":
    unittest.main()
