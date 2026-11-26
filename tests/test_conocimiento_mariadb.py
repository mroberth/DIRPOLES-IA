import unittest
from unittest.mock import patch

from app.knowledge.base import BaseConocimiento
from app.knowledge.mariadb.conocimiento import ConocimientoMariaDB
from app.schemas.enums import Modulo
from app.services.prompt_service import filtrar_contexto_seguro
from sqlalchemy.exc import SQLAlchemyError


class TestConocimientoMariaDB(unittest.TestCase):
    """Pruebas de la base de conocimiento respaldada por MariaDB con fallback."""

    def test_conformidad_protocolo(self) -> None:
        with patch("app.knowledge.mariadb.conocimiento.consultar", return_value=[]):
            instancia = ConocimientoMariaDB(sistema_id="dirpoles4")
        self.assertIsInstance(instancia, BaseConocimiento)

    def test_obtener_rol_con_fallback_si_no_hay_bd(self) -> None:
        with patch(
            "app.knowledge.mariadb.conocimiento.consultar",
            side_effect=SQLAlchemyError("Falla BD"),
        ):
            instancia = ConocimientoMariaDB(sistema_id="dirpoles4")
            rol = instancia.obtener_rol(Modulo.MEDICINA)
            self.assertTrue("médic" in rol.lower())

    def test_obtener_rol_desde_datos_cargados(self) -> None:
        def consultar_con_rol(
            sql: str, params: dict[str, str] | None = None
        ) -> list[dict[str, str]]:
            if "conocimiento_roles_prompts" in sql:
                return [
                    {
                        "dominio": "medicina",
                        "nombre_rol": "Médico institucional",
                        "instrucciones_sistema": "Analiza datos de salud agregados.",
                        "enfoque_por_defecto": "Prioriza prevención.",
                        "directrices_privacidad": "No divulgues identidades.",
                    }
                ]
            return []

        with patch(
            "app.knowledge.mariadb.conocimiento.consultar",
            side_effect=consultar_con_rol,
        ):
            instancia = ConocimientoMariaDB(sistema_id="dirpoles4")
        rol = instancia.obtener_rol(Modulo.MEDICINA)
        self.assertEqual(rol, "Médico institucional")

    def test_dominios_distribuciones_incluyen_pnf(self) -> None:
        def consultar_con_pnf(
            sql: str, params: dict[str, str] | None = None
        ) -> list[dict[str, str]]:
            if "conocimiento_catalogos_autorizados" in sql:
                return [{"tipo_catalogo": "pnf", "nombre_oficial": "PNF Informática"}]
            return []

        with patch(
            "app.knowledge.mariadb.conocimiento.consultar",
            side_effect=consultar_con_pnf,
        ):
            instancia = ConocimientoMariaDB(sistema_id="dirpoles4")
        doms = instancia.obtener_dominios_distribuciones()
        self.assertIn("por_pnf", doms)
        self.assertEqual(doms["por_pnf"], frozenset({"PNF Informática"}))

    def test_catalogos_de_bd_reemplazan_dominios_estaticos_y_filtran_contexto(self) -> None:
        def consultar_con_catalogos(
            sql: str, params: dict[str, str] | None = None
        ) -> list[dict[str, str]]:
            if "conocimiento_catalogos_autorizados" not in sql:
                return []
            return [
                {"tipo_catalogo": "pnf", "nombre_oficial": "PNF Nueva Carrera"},
                {"tipo_catalogo": "area", "nombre_oficial": "Área Nueva"},
                {"tipo_catalogo": "estado_jornada", "nombre_oficial": "En curso"},
            ]

        with patch(
            "app.knowledge.mariadb.conocimiento.consultar",
            side_effect=consultar_con_catalogos,
        ):
            instancia = ConocimientoMariaDB(sistema_id="dirpoles4")

        dominios = instancia.obtener_dominios_distribuciones()
        self.assertEqual(dominios["por_pnf"], frozenset({"PNF Nueva Carrera"}))
        self.assertEqual(dominios["por_area"], frozenset({"Área Nueva"}))

        contexto = filtrar_contexto_seguro(
            {
                "modulo": "general",
                "distribuciones": {
                    "por_area": [{"valor": "Área Nueva", "cantidad": 2, "porcentaje": 100.0}]
                },
                "top_areas_concentracion": [
                    {"valor": "Área Nueva", "cantidad": 2, "porcentaje": 100.0}
                ],
                "indicadores": {
                    "ocupacion_por_jornada": [
                        {
                            "jornada": "Dato identificable",
                            "estatus": "En curso",
                            "aforo": 4,
                            "asistentes": 2,
                            "ocupacion_pct": 50.0,
                        }
                    ]
                },
            },
            conocimiento=instancia,
        )
        self.assertEqual(contexto["distribuciones"]["por_area"][0]["valor"], "Área Nueva")
        self.assertEqual(contexto["top_areas_concentracion"][0]["valor"], "Área Nueva")
        self.assertEqual(
            contexto["indicadores"]["ocupacion_por_jornada"][0]["estatus"],
            "En curso",
        )
        self.assertEqual(
            contexto["indicadores"]["ocupacion_por_jornada"][0]["jornada"],
            "Jornada #1",
        )


if __name__ == "__main__":
    unittest.main()
