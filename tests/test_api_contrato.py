import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import obtener_ajustes
from app.main import crear_app

CLAVE_TEST = "clave-b2b-de-prueba"


class TestApiContrato(unittest.TestCase):
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

    def test_salud_sin_api_key(self) -> None:
        # Simular ping para no intentar conexión real TCP a MySQL
        with patch("app.db.session.ping", return_value=True):
            respuesta = self.cliente.get("/api/v1/salud")
            self.assertEqual(respuesta.status_code, 200)
            cuerpo = respuesta.json()
            self.assertEqual(cuerpo["estado"], "ok")
            self.assertEqual(cuerpo["servicio"], "DIRPOLES-IA")

    def test_generar_sin_api_key_devuelve_401(self) -> None:
        self.cliente.headers.pop("X-API-Key", None)
        respuesta = self.cliente.post(
            "/api/v1/reportes/generar",
            json={"modulo": "medicina", "intencion": "resumen_ejecutivo", "filtros": {}},
        )
        self.assertEqual(respuesta.status_code, 401)

    def test_generar_con_api_key_incorrecta_devuelve_401(self) -> None:
        respuesta = self.cliente.post(
            "/api/v1/reportes/generar",
            headers={"X-API-Key": "clave-erronea"},
            json={"modulo": "medicina", "intencion": "resumen_ejecutivo", "filtros": {}},
        )
        self.assertEqual(respuesta.status_code, 401)

    def test_catalogos(self) -> None:
        respuesta = self.cliente.get("/api/v1/reportes/catalogos")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertIn("medicina", cuerpo["modulos"])
        self.assertIn("alertas_y_anomalias", cuerpo["intenciones"])
        self.assertEqual(len(cuerpo["modulos"]), 10)
        self.assertEqual(len(cuerpo["intenciones"]), 4)


if __name__ == "__main__":
    unittest.main()
