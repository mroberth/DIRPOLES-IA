"""
tests/test_contrato_dirpoles4.py
-------------------------------------------------------------------------
Valida el contrato HTTP V1 recibido desde el monolito PHP (DIRPOLES-4).
Comprueba payloads sintéticos enviados por reportesController.php y verifica
que ReporteResponseDTO y los códigos de error cumplan exactamente el contrato.

Suite escrita exclusivamente en unittest (librería estándar de Python, sin pytest).
Ejecutar con:
    python3 -m unittest tests/test_contrato_dirpoles4.py
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import crear_app
from app.core.config import obtener_ajustes
from app.schemas.enums import Modulo, Intencion
from app.schemas.response import ReporteResponseDTO


class TestContratoDirpoles4(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.clave_test = "clave-b2b-de-prueba"
        obtener_ajustes.cache_clear()
        ajustes = obtener_ajustes()
        ajustes.mock_llm = True
        ajustes.dirpoles_ia_api_key = cls.clave_test
        app = crear_app()
        cls.app = app
        cls.cliente = TestClient(app)
        cls.cliente.headers.update({"X-API-Key": cls.clave_test})

    def test_salud_sin_autenticacion(self) -> None:
        """Verifica el endpoint GET /api/v1/salud (público sin X-API-Key)."""
        resp = self.cliente.get("/api/v1/salud")
        self.assertEqual(resp.status_code, 200)
        datos = resp.json()
        self.assertEqual(datos["estado"], "ok")
        self.assertEqual(datos["servicio"], "DIRPOLES-IA")
        self.assertEqual(datos["modo_llm"], "simulado")

    def test_auth_401_sin_api_key(self) -> None:
        """Verifica que una llamada sin X-API-Key retorne 401."""
        cliente_sin_auth = TestClient(self.app)
        resp = cliente_sin_auth.post(
            "/api/v1/reportes/generar",
            json={"modulo": "medicina", "intencion": "resumen_ejecutivo"},
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("X-API-Key", resp.json()["detail"])

    def test_auth_401_api_key_invalida(self) -> None:
        """Verifica que una llamada con X-API-Key errónea retorne 401."""
        cliente_invalido = TestClient(self.app)
        cliente_invalido.headers.update({"X-API-Key": "clave_erronea_sintetica"})
        resp = cliente_invalido.post(
            "/api/v1/reportes/generar",
            json={"modulo": "medicina", "intencion": "resumen_ejecutivo"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_validacion_422_modulo_invalido(self) -> None:
        """Verifica que un módulo inexistente retorne 422 con array detail."""
        resp = self.cliente.post(
            "/api/v1/reportes/generar",
            json={"modulo": "modulo_desconocido", "intencion": "resumen_ejecutivo"},
        )
        self.assertEqual(resp.status_code, 422)
        detalles = resp.json().get("detail", [])
        self.assertTrue(len(detalles) > 0)
        self.assertIn("modulo", detalles[0]["loc"])

    def test_validacion_422_fechas_invertidas(self) -> None:
        """Verifica que fecha_inicio > fecha_fin retorne 422 con mensaje descriptivo."""
        resp = self.cliente.post(
            "/api/v1/reportes/generar",
            json={
                "modulo": "medicina",
                "intencion": "resumen_ejecutivo",
                "filtros": {
                    "fecha_inicio": "2026-12-31",
                    "fecha_fin": "2026-01-01",
                },
            },
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("fecha_inicio no puede ser mayor que fecha_fin", str(resp.json()["detail"]))

    def test_validacion_422_pnf_cero(self) -> None:
        """Verifica que pnf=0 sea rechazado por regla ge=1 en Pydantic."""
        resp = self.cliente.post(
            "/api/v1/reportes/generar",
            json={
                "modulo": "medicina",
                "intencion": "resumen_ejecutivo",
                "filtros": {"pnf": 0},
            },
        )
        self.assertEqual(resp.status_code, 422)

    def test_validacion_422_id_empleado_cero(self) -> None:
        """Verifica que id_empleado=0 sea rechazado por regla ge=1 en Pydantic."""
        resp = self.cliente.post(
            "/api/v1/reportes/generar",
            json={
                "modulo": "medicina",
                "intencion": "resumen_ejecutivo",
                "id_empleado": 0,
            },
        )
        self.assertEqual(resp.status_code, 422)

    def test_payload_sintetico_admin_dirpoles4(self) -> None:
        """
        Verifica el payload sintético generado por reportesIaGenerar() para un Administrador:
        - id_empleado: null (acceso irrestricto)
        - filtros: {} (objeto vacío)
        - modulo: 'general'
        """
        mock_resumen = {
            "modulo": "general",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-10-31"},
            "totales": {"atenciones_totales": 50},
            "distribuciones": {
                "por_area": [
                    {"valor": "Medicina", "cantidad": 30, "porcentaje": 60.0},
                    {"valor": "Psicología", "cantidad": 20, "porcentaje": 40.0},
                ]
            },
            "alertas": [],
            "registros_procesados": 50,
        }

        with patch("app.services.etl_service.procesar", return_value=mock_resumen):
            resp = self.cliente.post(
                "/api/v1/reportes/generar",
                json={
                    "modulo": "general",
                    "intencion": "resumen_ejecutivo",
                    "filtros": {},
                    "observacion_usuario": None,
                    "id_empleado": None,
                },
            )
            self.assertEqual(resp.status_code, 200)
            dto = ReporteResponseDTO.model_validate(resp.json())
            self.assertTrue(dto.exito)
            self.assertEqual(dto.modulo, Modulo.GENERAL)
            self.assertEqual(dto.intencion, Intencion.RESUMEN_EJECUTIVO)
            self.assertEqual(dto.meta.registros_procesados, 50)
            self.assertEqual(dto.meta.modo_informe, "simulado")
            self.assertIn("```mermaid", dto.informe_markdown)
            self.assertIn("pie title Distribución por Por area", dto.informe_markdown)

    def test_payload_sintetico_especialista_trabajo_social(self) -> None:
        """
        Verifica el payload sintético generado para Trabajo Social con filtros y especialista regular:
        - modulo: 'trabajo_social' (snake_case)
        - intencion: 'alertas_y_anomalias'
        - filtros: { pnf: 3, limit: 100, submodulo: 'Becas' }
        - id_empleado: 17 (restringido a sus registros)
        """
        mock_resumen = {
            "modulo": "trabajo_social",
            "periodo": {},
            "totales": {"solicitudes": 15},
            "distribuciones": {
                "por_submodulo": [
                    {"valor": "Becas", "cantidad": 10, "porcentaje": 66.67},
                    {"valor": "Exoneración", "cantidad": 5, "porcentaje": 33.33},
                ]
            },
            "alertas": [
                {
                    "nivel": "advertencia",
                    "mensaje": "El área 'Becas' concentra el 66.67% de las atenciones del periodo.",
                }
            ],
            "registros_procesados": 15,
        }

        with patch("app.services.etl_service.procesar", return_value=mock_resumen):
            resp = self.cliente.post(
                "/api/v1/reportes/generar",
                json={
                    "modulo": "trabajo_social",
                    "intencion": "alertas_y_anomalias",
                    "filtros": {
                        "pnf": 3,
                        "limit": 100,
                        "submodulo": "Becas",
                    },
                    "observacion_usuario": "Priorizar estudiantes en vulnerabilidad.",
                    "id_empleado": 17,
                },
            )
            self.assertEqual(resp.status_code, 200)
            dto = ReporteResponseDTO.model_validate(resp.json())
            self.assertTrue(dto.exito)
            self.assertEqual(dto.modulo, Modulo.TRABAJO_SOCIAL)
            self.assertEqual(dto.meta.registros_procesados, 15)
            self.assertIn("El área 'Becas' concentra el 66.67% de las atenciones del periodo.", dto.informe_markdown)
            self.assertIn("```mermaid", dto.informe_markdown)

    def test_error_bd_mapea_503(self) -> None:
        """Verifica que un fallo de base de datos en etl_service devuelva 503 con la estructura esperada por PHP."""
        with patch("app.services.etl_service.procesar", side_effect=RuntimeError("Conexión perdida con MySQL")):
            resp = self.cliente.post(
                "/api/v1/reportes/generar",
                json={"modulo": "medicina", "intencion": "resumen_ejecutivo"},
            )
            self.assertEqual(resp.status_code, 503)
            cuerpo = resp.json()
            self.assertFalse(cuerpo["detail"]["exito"])
            self.assertIn("No fue posible extraer los datos", cuerpo["detail"]["detalle"])


if __name__ == "__main__":
    unittest.main()
