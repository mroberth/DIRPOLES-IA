import unittest
from unittest.mock import patch

from app.knowledge.base import BaseConocimiento
from app.knowledge.mariadb.conocimiento import ConocimientoMariaDB
from app.schemas.enums import Modulo


class TestConocimientoMariaDB(unittest.TestCase):
    """Pruebas de la base de conocimiento respaldada por MariaDB con fallback."""

    def test_conformidad_protocolo(self) -> None:
        instancia = ConocimientoMariaDB(sistema_id="dirpoles4")
        self.assertIsInstance(instancia, BaseConocimiento)

    def test_obtener_rol_con_fallback_si_no_hay_bd(self) -> None:
        with patch("app.knowledge.mariadb.conocimiento.consultar", side_effect=Exception("Falla BD")):
            instancia = ConocimientoMariaDB(sistema_id="dirpoles4")
            rol = instancia.obtener_rol(Modulo.MEDICINA)
            self.assertTrue("médic" in rol.lower())

    def test_obtener_rol_desde_datos_cargados(self) -> None:
        instancia = ConocimientoMariaDB(sistema_id="dirpoles4")
        rol = instancia.obtener_rol(Modulo.MEDICINA)
        self.assertTrue(len(rol) > 5)

    def test_dominios_distribuciones_incluyen_pnf(self) -> None:
        instancia = ConocimientoMariaDB(sistema_id="dirpoles4")
        doms = instancia.obtener_dominios_distribuciones()
        self.assertIn("por_pnf", doms)
        self.assertTrue(any("Informática" in p for p in doms["por_pnf"]))


if __name__ == "__main__":
    unittest.main()
