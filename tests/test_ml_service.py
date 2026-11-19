"""Pruebas unitarias e integración para el servicio de Machine Learning (ml_service).

Verifica:
1. Comportamiento ante datos insuficientes (< 3 puntos temporales).
2. Ajuste OLS y cálculo de métricas de ML (R², MAE, MSE, RMSE).
3. Proyección de demanda futura y detección de tendencia (Creciente/Decreciente/Estable).
4. Cálculo del salto de mes (incluyendo cambio de año 2026-12 -> 2027-01).
5. Inclusión de la sección predictiva en el informe de ClienteSimulado.
6. Ingesta de registros crudos en el endpoint V2 con agregación automática.
"""

import unittest

from app.schemas.enums import Intencion, Modulo
from app.schemas.v2 import AnalisisRequestV2DTO, MetricasEntradaV2DTO, PuntoMesV2DTO
from app.services import gemini_service
from app.services.analisis_v2_service import ejecutar_analisis_v2
from app.services.ml_service import predecir_demanda


class TestMLService(unittest.TestCase):
    def test_datos_insuficientes_retorna_no_disponible(self) -> None:
        # Vacío
        res_vacio = predecir_demanda([])
        self.assertFalse(res_vacio["disponible"])
        self.assertIn("al menos 3 periodos", res_vacio["motivo"])

        # 1 solo periodo
        res_uno = predecir_demanda([{"mes": "2026-01", "cantidad": 50}])
        self.assertFalse(res_uno["disponible"])

        # 2 periodos
        res_dos = predecir_demanda(
            [{"mes": "2026-01", "cantidad": 50}, {"mes": "2026-02", "cantidad": 60}]
        )
        self.assertFalse(res_dos["disponible"])

    def test_ajuste_lineal_perfecto_creciente(self) -> None:
        serie = [
            {"mes": "2026-01", "cantidad": 10},
            {"mes": "2026-02", "cantidad": 20},
            {"mes": "2026-03", "cantidad": 30},
        ]
        res = predecir_demanda(serie)
        self.assertTrue(res["disponible"])
        self.assertEqual(res["algoritmo"], "Regresión Lineal OLS (Series Temporales)")
        self.assertEqual(res["periodos_entrenados"], 3)
        self.assertEqual(res["proximo_mes"], "2026-04")
        self.assertEqual(res["prediccion_estimada"], 40)
        self.assertEqual(res["tendencia"], "Creciente")
        self.assertEqual(res["tasa_cambio_mensual"], 10.0)

        metricas = res["metricas_evaluacion"]
        self.assertAlmostEqual(metricas["r2_score"], 1.0, places=2)
        self.assertAlmostEqual(metricas["mae"], 0.0, places=2)
        self.assertAlmostEqual(metricas["mse"], 0.0, places=2)
        self.assertAlmostEqual(metricas["rmse"], 0.0, places=2)

    def test_ajuste_lineal_decreciente_con_salto_de_anio(self) -> None:
        serie = [
            {"mes": "2026-10", "cantidad": 100},
            {"mes": "2026-11", "cantidad": 80},
            {"mes": "2026-12", "cantidad": 60},
        ]
        res = predecir_demanda(serie)
        self.assertTrue(res["disponible"])
        self.assertEqual(res["proximo_mes"], "2027-01")  # Salto de año verificado
        self.assertEqual(res["prediccion_estimada"], 40)
        self.assertEqual(res["tendencia"], "Decreciente")
        self.assertEqual(res["tasa_cambio_mensual"], -20.0)

    def test_tendencia_estable(self) -> None:
        serie = [
            {"mes": "2026-01", "cantidad": 50},
            {"mes": "2026-02", "cantidad": 50},
            {"mes": "2026-03", "cantidad": 50},
        ]
        res = predecir_demanda(serie)
        self.assertTrue(res["disponible"])
        self.assertEqual(res["tendencia"], "Estable")
        self.assertEqual(res["prediccion_estimada"], 50)
        self.assertEqual(res["tasa_cambio_mensual"], 0.0)

    def test_resiliencia_ante_datos_corruptos_o_heterogeneos(self) -> None:
        serie = [
            {"mes": "2026-01", "cantidad": 15},
            {"mes": "2026-02", "cantidad": "veinte_invalido"},  # Corrupto
            {"mes": "2026-03", "cantidad": 35},
            {"mes": "2026-04", "cantidad": 45},
        ]
        res = predecir_demanda(serie)
        # Debe descartar el dato corrupto y procesar los 3 válidos
        self.assertTrue(res["disponible"])
        self.assertEqual(res["periodos_entrenados"], 3)
        self.assertEqual(res["proximo_mes"], "2026-05")
        self.assertTrue(res["prediccion_estimada"] > 45)

    def test_cliente_simulado_incluye_seccion_predictiva(self) -> None:
        resumen = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "totales": {"consultas": 75},
            "distribuciones": {},
            "indicadores": {},
            "alertas": [],
            "registros_procesados": 75,
            "prediccion_ml": {
                "disponible": True,
                "algoritmo": "Regresión Lineal OLS (Series Temporales)",
                "periodos_entrenados": 3,
                "proximo_mes": "2026-04",
                "prediccion_estimada": 35,
                "margen_error_mae": 2.1,
                "tendencia": "Creciente",
                "tasa_cambio_mensual": 5.2,
                "metricas_evaluacion": {
                    "r2_score": 0.9421,
                    "mae": 2.1,
                    "mse": 4.5,
                    "rmse": 2.12,
                },
            },
        }
        contexto = {
            "resumen": resumen,
            "intencion": Intencion.RESUMEN_EJECUTIVO.value,
            "modulo": Modulo.MEDICINA.value,
        }
        informe = gemini_service.ClienteSimulado().generar_informe("sys", "user", contexto)
        self.assertIn("Proyección de Demanda", informe)
        self.assertIn("Regresión Lineal OLS", informe)
        self.assertIn("0.9421", informe)  # R² en el informe
        self.assertIn("2026-04", informe)  # Próximo mes
        self.assertIn("#### 3. Recomendaciones Operativas", informe)

    def test_analisis_v2_ejecuta_ml_con_serie_mensual(self) -> None:
        peticion = AnalisisRequestV2DTO(
            dominio="flota_transporte",
            intencion=Intencion.RESUMEN_EJECUTIVO,
            metricas=MetricasEntradaV2DTO(
                serie_mensual=[
                    PuntoMesV2DTO(mes="2026-01", cantidad=40),
                    PuntoMesV2DTO(mes="2026-02", cantidad=55),
                    PuntoMesV2DTO(mes="2026-03", cantidad=70),
                ]
            ),
        )
        resp = ejecutar_analisis_v2(peticion)
        self.assertTrue(resp.exito)
        self.assertIn("Proyección de Demanda", resp.informe_markdown)
        self.assertIn("2026-04", resp.informe_markdown)
        self.assertIn("R²", resp.informe_markdown)

    def test_analisis_v2_ingesta_filas_crudas_y_auto_agregacion(self) -> None:
        peticion = AnalisisRequestV2DTO(
            dominio="biblioteca_externa",
            intencion=Intencion.RESUMEN_EJECUTIVO,
            registros_crudos=[
                {"fecha": "2026-01-10", "categoria": "Informática", "usuario": "estudiante_1"},
                {"fecha": "2026-01-15", "categoria": "Informática", "usuario": "estudiante_2"},
                {"fecha": "2026-02-12", "categoria": "Administración", "usuario": "estudiante_3"},
                {"fecha": "2026-02-20", "categoria": "Informática", "usuario": "estudiante_4"},
                {"fecha": "2026-03-05", "categoria": "Informática", "usuario": "estudiante_5"},
                {"fecha": "2026-03-18", "categoria": "Administración", "usuario": "estudiante_6"},
                {"fecha": "2026-03-25", "categoria": "Informática", "usuario": "estudiante_7"},
            ],
        )
        resp = ejecutar_analisis_v2(peticion)
        self.assertTrue(resp.exito)
        self.assertEqual(resp.meta.registros_procesados, 7)
        self.assertIn("Informática", resp.informe_markdown)
        # La serie derivada tiene 3 meses (2026-01: 2, 2026-02: 2, 2026-03: 3), por lo que ML entrena
        self.assertIn("Proyección de Demanda", resp.informe_markdown)


if __name__ == "__main__":
    unittest.main()
