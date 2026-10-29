"""Pruebas unitarias y de contrato para el Endpoint Universal V2 (Fase 4).

Verifica:
1. Autenticación con X-API-Key (401 si ausente o errónea).
2. Validación de esquemas Pydantic V2 (422 ante dominios o datos inválidos).
3. Happy Path de consumo sin base de datos (Modo Push) para un dominio externo.
4. Generación de Markdown estructurado con tablas y bloques Mermaid.js.
5. Detección automática de anomalías por concentración y variación temporal.
6. Aislamiento total: funciona sin requerir conexión a MySQL/MariaDB.
"""

import unittest

from fastapi.testclient import TestClient

from app.core.config import obtener_ajustes
from app.main import app
from app.schemas.v2 import AnalisisResponseV2DTO


class TestApiV2Universal(unittest.TestCase):
    def setUp(self) -> None:
        self.cliente = TestClient(app)
        self.ajustes = obtener_ajustes()
        self.cabeceras_auth = {"X-API-Key": self.ajustes.dirpoles_ia_api_key}

    def test_auth_401_sin_api_key(self) -> None:
        resp = self.cliente.post(
            "/api/v2/analizar",
            json={
                "dominio": "ventas",
                "intencion": "resumen_ejecutivo",
                "metricas": {"totales": {"pedidos": 10}},
            },
        )
        self.assertEqual(resp.status_code, 401)

    def test_auth_401_api_key_invalida(self) -> None:
        resp = self.cliente.post(
            "/api/v2/analizar",
            headers={"X-API-Key": "clave_erronea_fase4"},
            json={
                "dominio": "ventas",
                "intencion": "resumen_ejecutivo",
                "metricas": {"totales": {"pedidos": 10}},
            },
        )
        self.assertEqual(resp.status_code, 401)

    def test_validacion_422_dominio_caracteres_invalidos(self) -> None:
        resp = self.cliente.post(
            "/api/v2/analizar",
            headers=self.cabeceras_auth,
            json={
                "dominio": "ventas; DROP TABLE test;",
                "intencion": "resumen_ejecutivo",
                "metricas": {"totales": {"pedidos": 10}},
            },
        )
        self.assertEqual(resp.status_code, 422)

    def test_validacion_422_total_negativo(self) -> None:
        resp = self.cliente.post(
            "/api/v2/analizar",
            headers=self.cabeceras_auth,
            json={
                "dominio": "ventas",
                "intencion": "resumen_ejecutivo",
                "metricas": {"totales": {"pedidos": -5}},
            },
        )
        self.assertEqual(resp.status_code, 422)

    def test_happy_path_consumidor_externo_sin_bd(self) -> None:
        """Prueba que un consumidor externo (ej. Sistema Logístico) envíe métricas

        y reciba un informe ejecutivo visual con diagrama Mermaid.
        """
        payload = {
            "dominio": "logistica_flotas",
            "intencion": "resumen_ejecutivo",
            "periodo": {
                "fecha_inicio": "2026-01-01",
                "fecha_fin": "2026-06-30",
            },
            "metricas": {
                "totales": {
                    "envios_totales": 1200,
                    "entregados_a_tiempo": 1140,
                },
                "distribuciones": {
                    "por_zona": [
                        {"valor": "Zona Norte", "cantidad": 600},
                        {"valor": "Zona Centro", "cantidad": 400},
                        {"valor": "Zona Sur", "cantidad": 200},
                    ]
                },
                "serie_mensual": [
                    {"mes": "2026-01", "cantidad": 180},
                    {"mes": "2026-02", "cantidad": 190},
                    {"mes": "2026-03", "cantidad": 210},
                ],
                "indicadores": {
                    "tiempo_promedio_horas": 3.2,
                },
            },
            "rol_analista": "Director de Operaciones Logísticas de Distribución",
            "observacion_usuario": "Priorizar análisis de tiempos en Zona Norte.",
        }

        resp = self.cliente.post("/api/v2/analizar", headers=self.cabeceras_auth, json=payload)
        self.assertEqual(resp.status_code, 200)

        dto = AnalisisResponseV2DTO.model_validate(resp.json())
        self.assertTrue(dto.exito)
        self.assertEqual(dto.dominio, "logistica_flotas")
        self.assertEqual(dto.meta.registros_procesados, 2340)
        self.assertIn("```mermaid", dto.informe_markdown)
        self.assertIn("pie title", dto.informe_markdown)
        self.assertIn("Zona Norte", dto.informe_markdown)
        self.assertIn("#### 1. Resumen Ejecutivo", dto.informe_markdown)
        self.assertIn("#### 2. Hallazgos Clave y Puntos Críticos", dto.informe_markdown)

    def test_deteccion_automatica_de_anomalias_por_concentracion(self) -> None:
        """Verifica que el motor detecte cuando una categoría supera el umbral

        de concentración configurado (ej: 50% de concentración en una sucursal).
        """
        payload = {
            "dominio": "atencion_urgencias",
            "intencion": "alertas_y_anomalias",
            "metricas": {
                "distribuciones": {
                    "por_triage": [
                        {"valor": "Respiratorio Agudo", "cantidad": 850},
                        {"valor": "Traumatismo Leve", "cantidad": 150},
                    ]
                }
            },
            "reglas_analiticas": {
                "umbral_concentracion_pct": 50.0,
            },
        }

        resp = self.cliente.post("/api/v2/analizar", headers=self.cabeceras_auth, json=payload)
        self.assertEqual(resp.status_code, 200)

        dto = AnalisisResponseV2DTO.model_validate(resp.json())
        self.assertTrue(dto.exito)
        self.assertEqual(dto.meta.registros_procesados, 1000)
        self.assertIn("Respiratorio Agudo", dto.informe_markdown)
        self.assertIn("concentra el 85", dto.informe_markdown)


if __name__ == "__main__":
    unittest.main()
