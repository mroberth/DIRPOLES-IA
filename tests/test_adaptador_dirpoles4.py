"""Pruebas unitarias para la capa de adaptadores y encapsulación de DIRPOLES-4.

Verifica:
1. Conformidad con el protocolo AdaptadorFuenteDatos.
2. Extracción de datos y totales usando AdaptadorDirpoles4SQL con mocks.
3. Inyección de adaptadores alternativos en etl_service.procesar (desacoplamiento total del núcleo).
4. Retrocompatibilidad de la capa app.db.queries con app.adapters.dirpoles4.queries.
"""

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from app.adapters.base import AdaptadorFuenteDatos, Extraccion
from app.adapters.dirpoles4 import AdaptadorDirpoles4SQL
from app.adapters.dirpoles4.queries import Consulta
from app.db import queries as queries_legacy
from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO
from app.services import etl_service


class AdaptadorSinteticoPrueba:
    """Adaptador en memoria para simular cualquier consumidor externo sin SQL."""

    def __init__(self, datos: dict[str, pd.DataFrame], totales: dict[str, int]) -> None:
        self._datos = datos
        self._totales = totales

    def extraer(
        self,
        modulo: Modulo,
        filtros: FiltrosDTO,
        id_empleado: int | None,
        limit: int,
    ) -> Extraccion:
        return Extraccion(datos=self._datos, totales=self._totales)


class TestAdaptadorDirpoles4(unittest.TestCase):
    def test_conformidad_protocolo(self) -> None:
        adaptador = AdaptadorDirpoles4SQL()
        self.assertIsInstance(adaptador, AdaptadorFuenteDatos)

    @patch("app.db.session.contar", return_value=42)
    @patch("app.db.session.consultar_dataframe")
    def test_extraer_dirpoles4_ejecuta_consultas_y_conteo(
        self,
        mock_consultar_df: MagicMock,
        mock_contar: MagicMock,
    ) -> None:
        mock_consultar_df.return_value = pd.DataFrame([{"id": 1, "nombre": "Item"}])
        adaptador = AdaptadorDirpoles4SQL()

        resultado = adaptador.extraer(
            modulo=Modulo.MEDICINA,
            filtros=FiltrosDTO(),
            id_empleado=5,
            limit=50,
        )

        self.assertIsInstance(resultado, Extraccion)
        self.assertIn("consultas", resultado.datos)
        self.assertIn("insumos", resultado.datos)
        self.assertEqual(resultado.totales["consultas"], 42)
        self.assertEqual(resultado.totales["insumos"], 42)
        self.assertTrue(mock_consultar_df.called)
        self.assertTrue(mock_contar.called)

    def test_desacoplamiento_nucleo_con_adaptador_personalizado(self) -> None:
        """Demuestra que el núcleo analítico de etl_service puede procesar datos

        de cualquier adaptador externo sin ejecutar SQL ni conectarse a MySQL.
        """
        df_consultas = pd.DataFrame(
            [
                {"id": 1, "genero": "F", "nombre_pnf": "Informática", "fecha": "2026-05-10"},
                {"id": 2, "genero": "M", "nombre_pnf": "Administración", "fecha": "2026-05-11"},
            ]
        )
        df_insumos = pd.DataFrame(
            [
                {
                    "id": 1,
                    "estatus": "Disponible",
                    "cantidad": 50,
                    "dias_hasta_vencimiento": 120,
                    "nombre_insumo": "Gasa",
                }
            ]
        )
        datos_sinteticos = {
            "consultas": df_consultas,
            "insumos": df_insumos,
        }
        totales_sinteticos = {"consultas": 2, "insumos": 1}

        adaptador_custom = AdaptadorSinteticoPrueba(datos_sinteticos, totales_sinteticos)

        resumen = etl_service.procesar(
            modulo=Modulo.MEDICINA,
            filtros=FiltrosDTO(),
            id_empleado=None,
            limit=100,
            adaptador=adaptador_custom,
        )

        self.assertEqual(resumen["modulo"], "medicina")
        self.assertEqual(resumen["registros_procesados"], 3)
        self.assertIn("distribuciones", resumen)
        self.assertIn("por_genero", resumen["distribuciones"])
        self.assertEqual(len(resumen["distribuciones"]["por_genero"]), 2)

    def test_retrocompatibilidad_app_db_queries(self) -> None:
        """Verifica que app.db.queries reexporta fielmente las funciones y clases

        del adaptador encapsulado.
        """
        self.assertTrue(callable(queries_legacy.obtener_consultas))
        self.assertTrue(callable(queries_legacy.sql_con_limit))
        self.assertTrue(callable(queries_legacy.sql_total))
        self.assertIs(queries_legacy.Consulta, Consulta)

        consultas = queries_legacy.obtener_consultas(
            Modulo.ORIENTACION, FiltrosDTO(), id_empleado=None
        )
        self.assertIn("casos", consultas)
        self.assertIsInstance(consultas["casos"], Consulta)


if __name__ == "__main__":
    unittest.main()
