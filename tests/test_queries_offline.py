"""Pruebas automatizadas offline para constructores SQL y funciones de extracción.

Verifica la construcción de consultas parametrizadas, la compilación contra el
dialecto MySQL de SQLAlchemy y el comportamiento del pipeline de extracción con
mocks, sin realizar ninguna conexión de red ni llamadas a bases de datos reales.
"""

from datetime import date
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import obtener_ajustes
from app.db import queries, session
from app.schemas.enums import (
    AreaGeneral,
    EstadoCita,
    Modulo,
    SeccionTransporte,
    SubmoduloTrabajoSocial,
    TipoBien,
)
from app.schemas.request import FiltrosDTO
from app.services import etl_service

COLECCIONES_POR_MODULO: dict[Modulo, set[str]] = {
    Modulo.GENERAL: {"atenciones"},
    Modulo.MEDICINA: {"consultas", "insumos"},
    Modulo.PSICOLOGIA: {"morbilidad", "citas"},
    Modulo.ORIENTACION: {"casos"},
    Modulo.DISCAPACIDAD: {"registros"},
    Modulo.TRABAJO_SOCIAL: {"registros"},
    Modulo.REFERENCIAS: {"remisiones"},
    Modulo.JORNADAS: {"jornadas"},
    Modulo.MOBILIARIO: {"bienes"},
    Modulo.TRANSPORTE: {
        "vehiculos",
        "rutas",
        "proveedores",
        "repuestos",
        "asignaciones",
        "mantenimientos",
    },
}


class TestConstructoresConsultas(unittest.TestCase):
    """Verifica que los constructores generen las consultas y parámetros esperados."""

    def test_los_10_modulos_generan_consultas_esperadas(self) -> None:
        filtros = FiltrosDTO()
        for modulo, colecciones_esperadas in COLECCIONES_POR_MODULO.items():
            with self.subTest(modulo=modulo):
                consultas = queries.obtener_consultas(modulo, filtros, id_empleado=None)
                self.assertIsInstance(consultas, dict)
                self.assertEqual(set(consultas.keys()), colecciones_esperadas)
                for nombre_col, consulta in consultas.items():
                    self.assertIsInstance(consulta.base, str)
                    self.assertGreater(len(consulta.base.strip()), 0)
                    self.assertIsInstance(consulta.orden, str)
                    self.assertGreater(len(consulta.orden.strip()), 0)
                    self.assertIsInstance(consulta.params, dict)

    def test_parametros_vinculados_sin_interpolacion_en_sql(self) -> None:
        """Comprueba que los filtros de usuario se vinculen por parámetros y no se interpolen en el SQL."""
        filtros = FiltrosDTO(
            fecha_inicio=date(2026, 2, 1),
            fecha_fin=date(2026, 11, 30),
            pnf=77,
            genero="M",
            estado="Atendida",
        )
        id_empleado_centinela = 99

        for modulo in Modulo:
            with self.subTest(modulo=modulo):
                consultas = queries.obtener_consultas(modulo, filtros, id_empleado=id_empleado_centinela)
                for nombre_col, c in consultas.items():
                    # El SQL base debe usar parámetros con dos puntos (:param)
                    sql_lim, params_lim = queries.sql_con_limit(c, 50)
                    self.assertIn(":limit", sql_lim)
                    self.assertEqual(params_lim["limit"], 50)

                    # Si el filtro aplica a la consulta, el valor debe estar en params
                    # y la cadena literal no debe estar interpolada directamente en el SQL
                    if "f_desde" in c.params:
                        self.assertEqual(c.params["f_desde"], date(2026, 2, 1))
                        self.assertIn(":f_desde", c.base)
                        self.assertNotIn("2026-02-01", c.base)

                    if "f_hasta" in c.params:
                        self.assertEqual(c.params["f_hasta"], date(2026, 11, 30))
                        self.assertIn(":f_hasta", c.base)
                        self.assertNotIn("2026-11-30", c.base)

                    if "id_empleado" in c.params:
                        self.assertEqual(c.params["id_empleado"], id_empleado_centinela)
                        self.assertIn(":id_empleado", c.base)

    def test_referencia_esquema_seguridad_empleado(self) -> None:
        """Verifica que el cruce con empleado use el prefijo explícito del esquema de seguridad."""
        seguridad = obtener_ajustes().db_name_security
        filtros = FiltrosDTO()
        consultas = queries.obtener_consultas(Modulo.PSICOLOGIA, filtros, id_empleado=10)
        citas_sql = consultas["citas"].base
        self.assertIn(f"{seguridad}.empleado", citas_sql)

    def test_sql_con_limit_y_sql_total_estructura(self) -> None:
        c = queries.Consulta(
            base="SELECT id FROM tabla WHERE 1 = 1",
            orden="id DESC",
            params={"filtro": "valor"},
        )
        sql_lim, p_lim = queries.sql_con_limit(c, 25)
        self.assertEqual(sql_lim, "SELECT id FROM tabla WHERE 1 = 1 ORDER BY id DESC LIMIT :limit")
        self.assertEqual(p_lim["limit"], 25)
        self.assertEqual(p_lim["filtro"], "valor")

        sql_tot, p_tot = queries.sql_total(c)
        self.assertEqual(sql_tot, "SELECT COUNT(*) AS total FROM (SELECT id FROM tabla WHERE 1 = 1) conteo")
        self.assertEqual(p_tot["filtro"], "valor")
        self.assertNotIn("limit", p_tot)


class TestCompilacionDialectoMySQL(unittest.TestCase):
    """Verifica que las sentencias SQL de los 10 módulos compilen válidamente en el dialecto MySQL."""

    def test_compilacion_todas_las_consultas_dialecto_mysql(self) -> None:
        dialecto = mysql.dialect()
        filtros = FiltrosDTO(
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            pnf=5,
            genero="F",
            estado="Atendida",
        )
        for modulo in Modulo:
            with self.subTest(modulo=modulo):
                consultas = queries.obtener_consultas(modulo, filtros, id_empleado=12)
                for nombre_col, c in consultas.items():
                    sql_lim, _ = queries.sql_con_limit(c, 100)
                    sql_tot, _ = queries.sql_total(c)

                    comp_lim = text(sql_lim).compile(dialect=dialecto)
                    self.assertGreater(len(str(comp_lim)), 0)

                    comp_tot = text(sql_tot).compile(dialect=dialecto)
                    self.assertGreater(len(str(comp_tot)), 0)

    def test_compilacion_variantes_filtros_especificos(self) -> None:
        dialecto = mysql.dialect()

        # Variantes de Transporte
        for seccion in SeccionTransporte:
            with self.subTest(seccion_transporte=seccion):
                f = FiltrosDTO(seccion_transporte=seccion)
                cs = queries.obtener_consultas(Modulo.TRANSPORTE, f, None)
                for _, c in cs.items():
                    sql, _ = queries.sql_con_limit(c, 10)
                    self.assertIsNotNone(text(sql).compile(dialect=dialecto))

        # Variantes de Trabajo Social
        for submodulo in SubmoduloTrabajoSocial:
            with self.subTest(submodulo=submodulo):
                f = FiltrosDTO(submodulo=submodulo)
                cs = queries.obtener_consultas(Modulo.TRABAJO_SOCIAL, f, None)
                for _, c in cs.items():
                    sql, _ = queries.sql_con_limit(c, 10)
                    self.assertIsNotNone(text(sql).compile(dialect=dialecto))

        # Variantes de Mobiliario
        for tipo in TipoBien:
            with self.subTest(tipo_bien=tipo):
                f = FiltrosDTO(tipo_bien=tipo)
                cs = queries.obtener_consultas(Modulo.MOBILIARIO, f, None)
                for _, c in cs.items():
                    sql, _ = queries.sql_con_limit(c, 10)
                    self.assertIsNotNone(text(sql).compile(dialect=dialecto))

        # Variantes de General (filtro por área)
        for area in AreaGeneral:
            with self.subTest(area=area):
                f = FiltrosDTO(area=area)
                cs = queries.obtener_consultas(Modulo.GENERAL, f, None)
                for _, c in cs.items():
                    sql, _ = queries.sql_con_limit(c, 10)
                    self.assertIsNotNone(text(sql).compile(dialect=dialecto))


class TestExtraccionOfflineConMocks(unittest.TestCase):
    """Verifica que el pipeline de extracción funcione con mocks sin conexiones a BD."""

    @patch("app.db.session.contar")
    @patch("app.db.session.consultar_dataframe")
    def test_extraer_invoca_session_correctamente_para_los_10_modulos(
        self,
        mock_consultar_df: MagicMock,
        mock_contar: MagicMock,
    ) -> None:
        mock_consultar_df.return_value = pd.DataFrame([{"id": 1, "nombre": "Sintetico"}])
        mock_contar.return_value = 1

        filtros = FiltrosDTO()
        for modulo, colecciones in COLECCIONES_POR_MODULO.items():
            mock_consultar_df.reset_mock()
            mock_contar.reset_mock()

            with self.subTest(modulo=modulo):
                extr = etl_service.extraer(modulo, filtros, id_empleado=None, limit=50)
                self.assertIsInstance(extr, etl_service.Extraccion)
                self.assertEqual(set(extr.datos.keys()), colecciones)
                self.assertEqual(set(extr.totales.keys()), colecciones)

                self.assertEqual(mock_consultar_df.call_count, len(colecciones))
                self.assertEqual(mock_contar.call_count, len(colecciones))

                for col in colecciones:
                    self.assertIsInstance(extr.datos[col], pd.DataFrame)
                    self.assertEqual(extr.totales[col], 1)

    @patch("app.db.session.contar")
    @patch("app.db.session.consultar_dataframe")
    def test_extraer_con_datos_sinteticos_y_vacios(
        self,
        mock_consultar_df: MagicMock,
        mock_contar: MagicMock,
    ) -> None:
        # 1. Resultados sintéticos poblados
        mock_consultar_df.return_value = pd.DataFrame([{"fila": 1}, {"fila": 2}])
        mock_contar.return_value = 2

        extr_poblada = etl_service.extraer(Modulo.MEDICINA, FiltrosDTO(), None, limit=10)
        self.assertEqual(len(extr_poblada.datos["consultas"]), 2)
        self.assertEqual(extr_poblada.totales["consultas"], 2)

        # 2. Resultados sintéticos vacíos
        mock_consultar_df.return_value = pd.DataFrame()
        mock_contar.return_value = 0

        extr_vacia = etl_service.extraer(Modulo.MEDICINA, FiltrosDTO(), None, limit=10)
        self.assertEqual(len(extr_vacia.datos["consultas"]), 0)
        self.assertEqual(extr_vacia.totales["consultas"], 0)

    @patch("app.db.session.consultar_dataframe")
    def test_extraer_propagacion_error_bd(self, mock_consultar_df: MagicMock) -> None:
        mock_consultar_df.side_effect = SQLAlchemyError("Error simulado de conexión MySQL")
        with self.assertRaises(SQLAlchemyError):
            etl_service.extraer(Modulo.GENERAL, FiltrosDTO(), None, limit=10)

    def test_procesar_end_to_end_offline_los_10_modulos(self) -> None:
        """Verifica que procesar() ejecute el pipeline completo ETL con una extracción simulada."""

        def mock_extraer(modulo: Modulo, filtros: FiltrosDTO, id_empleado: int | None, limit: int) -> etl_service.Extraccion:
            datos: dict[str, pd.DataFrame] = {}
            if modulo == Modulo.GENERAL:
                datos["atenciones"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "area": "Medicina", "genero": "F", "nombre_pnf": "PNF Informática"}])
            elif modulo == Modulo.MEDICINA:
                datos["consultas"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "genero": "F", "nombre_pnf": "PNF Informática", "diagnostico": "Gripe", "motivo": "Fiebre"}])
                datos["insumos"] = pd.DataFrame([{"nombre_insumo": "Paracetamol", "cantidad": 20, "estatus": "Disponible", "fecha_vencimiento": date(2030, 1, 1)}])
            elif modulo == Modulo.PSICOLOGIA:
                datos["morbilidad"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "tipo_consulta": "Diagnóstico", "diagnostico": "Ansiedad", "nombre_pnf": "PNF Informática"}])
                datos["citas"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "estado": "Atendida", "nombre_pnf": "PNF Informática"}])
            elif modulo == Modulo.ORIENTACION:
                datos["casos"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "genero": "M", "nombre_pnf": "PNF Informática", "motivo": "Vocacional"}])
            elif modulo == Modulo.DISCAPACIDAD:
                datos["registros"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "genero": "F", "nombre_pnf": "PNF Informática", "tipo_discapacidad": "Física", "grado": "Leve", "carnet_discapacidad": "C-1", "requiere_asistencia": "No"}])
            elif modulo == Modulo.TRABAJO_SOCIAL:
                datos["registros"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "submodulo": "Becas", "nombre_pnf": "PNF Informática", "detalle_extra": None}])
            elif modulo == Modulo.REFERENCIAS:
                datos["remisiones"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "estado": "Aceptada", "servicio_destino": "Medicina", "dias_transcurridos": 5}])
            elif modulo == Modulo.JORNADAS:
                datos["jornadas"] = pd.DataFrame([{"nombre_jornada": "Jornada 1", "fecha_inicio": date(2026, 3, 1), "estatus": "Finalizada", "aforo_maximo": 20, "total_asistentes": 15, "total_diagnosticos": 10}])
            elif modulo == Modulo.MOBILIARIO:
                datos["bienes"] = pd.DataFrame([{"fecha": date(2026, 3, 1), "tipo_bien": "Mobiliario", "estado": "Activo"}])
            elif modulo == Modulo.TRANSPORTE:
                datos["vehiculos"] = pd.DataFrame([{"tipo_vehiculo": "Autobús", "estado": "Operativo"}])
                datos["rutas"] = pd.DataFrame([{"estatus": "Activa"}])
                datos["proveedores"] = pd.DataFrame([{"estatus": "Activo"}])
                datos["repuestos"] = pd.DataFrame([{"nombre": "Filtro", "cantidad": 15, "estatus": "Disponible"}])
                datos["asignaciones"] = pd.DataFrame([{"estatus": "Activa"}])
                datos["mantenimientos"] = pd.DataFrame([{"tipo": "Preventivo"}])

            totales = {k: len(v) for k, v in datos.items()}
            return etl_service.Extraccion(datos=datos, totales=totales)

        with patch("app.services.etl_service.extraer", side_effect=mock_extraer):
            for modulo in Modulo:
                with self.subTest(modulo=modulo):
                    resumen = etl_service.procesar(modulo, FiltrosDTO(), id_empleado=None, limit=100)
                    self.assertEqual(resumen["modulo"], modulo.value)
                    self.assertIn("totales", resumen)
                    self.assertIn("alertas", resumen)
                    self.assertIn("periodo", resumen)
                    self.assertGreaterEqual(resumen["registros_procesados"], 1)


if __name__ == "__main__":
    unittest.main()
