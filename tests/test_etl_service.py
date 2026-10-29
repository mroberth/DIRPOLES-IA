from datetime import date
import unittest

import pandas as pd

from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO
from app.services.etl_service import Extraccion, transformar


def _filtros(**kwargs: object) -> FiltrosDTO:
    return FiltrosDTO.model_validate(kwargs)


def _extraccion(datos: dict[str, pd.DataFrame], totales: dict[str, int]) -> Extraccion:
    return Extraccion(datos=datos, totales=totales)


class TestEtlService(unittest.TestCase):
    def test_medicina_detecta_stock_critico_y_vencidos(self) -> None:
        consultas = pd.DataFrame(
            [
                {
                    "fecha": date(2026, 3, 1),
                    "genero": "M",
                    "nombre_pnf": "PNF Informática",
                    "motivo": "Fiebre",
                    "diagnostico": "Gripe",
                },
                {
                    "fecha": date(2026, 3, 15),
                    "genero": "F",
                    "nombre_pnf": "PNF Informática",
                    "motivo": "Dolor",
                    "diagnostico": "Gripe",
                },
            ]
        )
        insumos = pd.DataFrame(
            [
                {
                    "nombre_insumo": "Paracetamol",
                    "cantidad": 2,
                    "fecha_vencimiento": date(2026, 1, 1),
                    "estatus": "Disponible",
                },
                {
                    "nombre_insumo": "Guantes",
                    "cantidad": 50,
                    "fecha_vencimiento": date(2030, 1, 1),
                    "estatus": "Disponible",
                },
            ]
        )
        extraccion = _extraccion(
            {"consultas": consultas, "insumos": insumos},
            {"consultas": 2, "insumos": 2},
        )
        resumen = transformar(Modulo.MEDICINA, extraccion, _filtros())

        self.assertEqual(resumen["registros_procesados"], 4)
        niveles = {a["nivel"] for a in resumen["alertas"]}
        self.assertIn("critico", niveles)
        indicadores = resumen["indicadores"]["insumos"]
        self.assertEqual(indicadores["vencidos"], 1)
        self.assertEqual(indicadores["stock_critico"][0]["nombre"], "Paracetamol")
        self.assertNotIn("top_diagnosticos", resumen["distribuciones"])
        self.assertNotIn("top_motivos", resumen["distribuciones"])

    def test_medicina_comparativa_mensual(self) -> None:
        consultas = pd.DataFrame(
            [
                {"fecha": date(2026, 1, 5), "genero": "M", "diagnostico": "A", "motivo": "x"},
                {"fecha": date(2026, 2, 5), "genero": "M", "diagnostico": "A", "motivo": "x"},
                {"fecha": date(2026, 2, 6), "genero": "M", "diagnostico": "A", "motivo": "x"},
                {"fecha": date(2026, 2, 7), "genero": "M", "diagnostico": "B", "motivo": "x"},
            ]
        )
        extraccion = _extraccion({"consultas": consultas, "insumos": pd.DataFrame()}, {"consultas": 4})
        resumen = transformar(Modulo.MEDICINA, extraccion, _filtros())
        comp = resumen["comparativa"]
        self.assertIsNotNone(comp)
        self.assertEqual(comp["mes_anterior"]["cantidad"], 1)
        self.assertEqual(comp["mes_actual"]["cantidad"], 3)
        self.assertEqual(comp["variacion_pct"], 200.0)

    def test_psicologia_alerta_por_no_asistio(self) -> None:
        citas = pd.DataFrame(
            [
                {"fecha": date(2026, 3, 1), "estado": "Atendida"},
                {"fecha": date(2026, 3, 2), "estado": "No asistió"},
                {"fecha": date(2026, 3, 3), "estado": "No asistió"},
                {"fecha": date(2026, 3, 4), "estado": "Pendiente"},
            ]
        )
        morbilidad = pd.DataFrame(
            [{"fecha": date(2026, 3, 1), "tipo_consulta": "Diagnóstico", "diagnostico": "Ansiedad"}]
        )
        extraccion = _extraccion(
            {"citas": citas, "morbilidad": morbilidad},
            {"citas": 4, "morbilidad": 1},
        )
        resumen = transformar(Modulo.PSICOLOGIA, extraccion, _filtros())
        self.assertEqual(resumen["indicadores"]["citas_no_asistio"], 2)
        self.assertEqual(resumen["indicadores"]["citas_pendientes"], 1)
        self.assertTrue(any("No asistió" in a["mensaje"] for a in resumen["alertas"]))

    def test_referencias_alerta_por_pendientes(self) -> None:
        remisiones = pd.DataFrame(
            [
                {"fecha": date(2026, 3, 1), "estado": "Pendiente", "servicio_destino": "Medicina"},
                {"fecha": date(2026, 3, 2), "estado": "Aceptada", "servicio_destino": "Medicina"},
            ]
        )
        extraccion = _extraccion({"remisiones": remisiones}, {"remisiones": 2})
        resumen = transformar(Modulo.REFERENCIAS, extraccion, _filtros())
        self.assertEqual(resumen["indicadores"]["pendientes"], 1)
        self.assertTrue(any("pendiente" in a["mensaje"].lower() for a in resumen["alertas"]))

    def test_general_distribuciones_y_area_concentrada(self) -> None:
        filas = [
            {
                "fecha": date(2026, 3, 1),
                "area": "Medicina",
                "genero": "F",
                "nombre_pnf": "PNF Informática",
            }
            for _ in range(7)
        ] + [
            {
                "fecha": date(2026, 3, 2),
                "area": "Psicología",
                "genero": "M",
                "nombre_pnf": "PNF Contaduría",
            }
            for _ in range(3)
        ]
        extraccion = _extraccion({"atenciones": pd.DataFrame(filas)}, {"atenciones": 10})
        resumen = transformar(Modulo.GENERAL, extraccion, _filtros())
        self.assertEqual(resumen["distribuciones"]["por_area"][0]["valor"], "Medicina")
        self.assertEqual(resumen["distribuciones"]["por_area"][0]["porcentaje"], 70.0)
        self.assertEqual(resumen["distribuciones"]["por_genero"][0]["valor"], "Femenino")
        self.assertTrue(any("Medicina" in a["mensaje"] for a in resumen["alertas"]))

    def test_dataset_vacio_genera_alerta_informativa(self) -> None:
        extraccion = _extraccion(
            {"casos": pd.DataFrame()},
            {"casos": 0},
        )
        resumen = transformar(Modulo.ORIENTACION, extraccion, _filtros())
        self.assertEqual(resumen["registros_procesados"], 0)
        self.assertTrue(any("No se encontraron registros" in a["mensaje"] for a in resumen["alertas"]))

    def test_truncamiento_por_limit_genera_advertencia(self) -> None:
        df = pd.DataFrame([{"fecha": date(2026, 3, 1), "submodulo": "Becas"}] * 3)
        extraccion = _extraccion({"registros": df}, {"registros": 100})
        resumen = transformar(Modulo.TRABAJO_SOCIAL, extraccion, _filtros())
        self.assertTrue(any("límite de filas" in a["mensaje"] for a in resumen["alertas"]))

    def test_transporte_repuestos_bajo_stock(self) -> None:
        repuestos = pd.DataFrame(
            [
                {"nombre": "Filtro de aceite", "cantidad": 2, "estatus": "Disponible"},
                {"nombre": "Pastillas", "cantidad": 20, "estatus": "Disponible"},
            ]
        )
        extraccion = _extraccion(
            {"repuestos": repuestos, "vehiculos": pd.DataFrame()},
            {"repuestos": 2, "vehiculos": 0},
        )
        resumen = transformar(Modulo.TRANSPORTE, extraccion, _filtros())
        self.assertEqual(resumen["secciones"]["repuestos"]["bajo_stock"], 1)
        self.assertTrue(any("repuesto" in a["mensaje"].lower() for a in resumen["alertas"]))

    def test_jornadas_ocupacion_de_aforo(self) -> None:
        jornadas = pd.DataFrame(
            [
                {
                    "nombre_jornada": "Jornada Dental",
                    "tipo_jornada": "Especializada",
                    "fecha_inicio": date(2026, 3, 1),
                    "estatus": "Finalizada",
                    "aforo_maximo": 10,
                    "total_asistentes": 12,
                    "total_diagnosticos": 8,
                }
            ]
        )
        extraccion = _extraccion({"jornadas": jornadas}, {"jornadas": 1})
        resumen = transformar(Modulo.JORNADAS, extraccion, _filtros())
        self.assertEqual(resumen["indicadores"]["asistentes_totales"], 12)
        self.assertEqual(resumen["indicadores"]["ocupacion_por_jornada"][0]["ocupacion_pct"], 120.0)
        self.assertTrue(any("aforo" in a["mensaje"] for a in resumen["alertas"]))

    def test_discapacidad_conteo_carnet_y_grave(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "fecha": date(2026, 3, 1),
                    "tipo_discapacidad": "Física",
                    "grado": "Grave",
                    "carnet_discapacidad": "C-001",
                    "requiere_asistencia": "Si",
                },
                {
                    "fecha": date(2026, 3, 2),
                    "tipo_discapacidad": "Sensorial",
                    "grado": "Leve",
                    "carnet_discapacidad": "",
                    "requiere_asistencia": "No",
                },
            ]
        )
        extraccion = _extraccion({"registros": df}, {"registros": 2})
        resumen = transformar(Modulo.DISCAPACIDAD, extraccion, _filtros())
        self.assertEqual(resumen["indicadores"]["con_carnet"], 1)
        self.assertEqual(resumen["indicadores"]["sin_carnet"], 1)
        self.assertEqual(resumen["indicadores"]["grado_grave"], 1)
        self.assertTrue(any("Grave" in a["mensaje"] for a in resumen["alertas"]))

    def test_por_pnf_calculado_en_etl_para_consumo_monolito(self) -> None:
        """Verifica que el ETL conserve el cálculo de por_pnf en los 6 módulos de bienestar estudiantil."""
        filas = [
            {"fecha": date(2026, 3, 1), "nombre_pnf": "PNF Informática", "genero": "F", "area": "Medicina"},
            {"fecha": date(2026, 3, 2), "nombre_pnf": "PNF Administración", "genero": "M", "area": "Medicina"},
        ]
        df = pd.DataFrame(filas)
        modulos_con_pnf = [
            Modulo.GENERAL,
            Modulo.MEDICINA,
            Modulo.PSICOLOGIA,
            Modulo.ORIENTACION,
            Modulo.DISCAPACIDAD,
            Modulo.TRABAJO_SOCIAL,
        ]
        for modulo in modulos_con_pnf:
            with self.subTest(modulo=modulo):
                if modulo == Modulo.GENERAL:
                    extr = _extraccion({"atenciones": df}, {"atenciones": 2})
                elif modulo == Modulo.MEDICINA:
                    extr = _extraccion({"consultas": df, "insumos": pd.DataFrame()}, {"consultas": 2})
                elif modulo == Modulo.PSICOLOGIA:
                    extr = _extraccion({"morbilidad": df, "citas": pd.DataFrame()}, {"morbilidad": 2})
                elif modulo == Modulo.ORIENTACION:
                    extr = _extraccion({"casos": df}, {"casos": 2})
                elif modulo == Modulo.DISCAPACIDAD:
                    df_disc = df.copy()
                    df_disc["tipo_discapacidad"] = "Física"
                    df_disc["grado"] = "Leve"
                    df_disc["carnet_discapacidad"] = "Sí"
                    df_disc["requiere_asistencia"] = "No"
                    extr = _extraccion({"registros": df_disc}, {"registros": 2})
                elif modulo == Modulo.TRABAJO_SOCIAL:
                    df_ts = df.copy()
                    df_ts["submodulo"] = "Becas"
                    extr = _extraccion({"registros": df_ts}, {"registros": 2})

                resumen = transformar(modulo, extr, _filtros())
                self.assertIn("por_pnf", resumen["distribuciones"])
                pnfs = [item["valor"] for item in resumen["distribuciones"]["por_pnf"]]
                self.assertIn("PNF Informática", pnfs)
                self.assertIn("PNF Administración", pnfs)


if __name__ == "__main__":
    unittest.main()
