"""Pruebas unitarias para la salvaguarda de seguridad de pruebas de integración con MySQL.

Verifica que el guard impida categóricamente conectar contra bases de datos operativas
y exija una configuración explícita, aislada y validada.
"""

import os
import unittest
from unittest.mock import patch

from app.core.config import obtener_ajustes
from app.db import session
from tests.guard_integracion_bd import (
    ConfiguracionPruebasBD,
    activar_motor_pruebas,
    obtener_configuracion_pruebas_bd,
    restaurar_motor_original,
    validar_seguridad_entorno_pruebas,
)


class TestGuardIntegracionBD(unittest.TestCase):
    """Comprueba que ninguna prueba pueda apuntar accidentalmente a la base institucional."""

    def test_rechazo_si_flag_test_bd_no_esta_activa(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            seguro, motivo, config = validar_seguridad_entorno_pruebas()
            self.assertFalse(seguro)
            self.assertIn("requiere 'DIRPOLES_TEST_BD=1'", motivo)
            self.assertIsNone(config)

    def test_bloqueo_si_flag_activa_pero_faltan_variables_de_prueba(self) -> None:
        # Simula un desarrollador que solo puso DIRPOLES_TEST_BD=1 pensando que usaría el .env
        with patch.dict(os.environ, {"DIRPOLES_TEST_BD": "1"}, clear=True):
            seguro, motivo, config = validar_seguridad_entorno_pruebas()
            self.assertFalse(seguro)
            self.assertIn("BLOQUEO DE SEGURIDAD", motivo)
            self.assertIn("faltan variables de base de datos de prueba", motivo)
            self.assertIsNone(config)

    def test_bloqueo_si_esquema_coincide_con_lista_negra_operativa(self) -> None:
        # Intento de apuntar a dirpoles_business directamente
        env_peligroso = {
            "DIRPOLES_TEST_BD": "1",
            "DIRPOLES_TEST_DB_NAME_BUSINESS": "dirpoles_business",
            "DIRPOLES_TEST_DB_NAME_SECURITY": "dirpoles_security_test",
        }
        with patch.dict(os.environ, env_peligroso, clear=True):
            seguro, motivo, config = validar_seguridad_entorno_pruebas()
            self.assertFalse(seguro)
            self.assertIn("coincide con un esquema operativo institucional", motivo)
            self.assertIsNone(config)

    def test_bloqueo_si_esquema_de_seguridad_es_operativo(self) -> None:
        env_peligroso = {
            "DIRPOLES_TEST_BD": "1",
            "DIRPOLES_TEST_DB_NAME_BUSINESS": "dirpoles_business_test",
            "DIRPOLES_TEST_DB_NAME_SECURITY": "dirpoles_security",
        }
        with patch.dict(os.environ, env_peligroso, clear=True):
            seguro, motivo, config = validar_seguridad_entorno_pruebas()
            self.assertFalse(seguro)
            self.assertIn("coincide con un esquema operativo institucional", motivo)
            self.assertIsNone(config)

    def test_bloqueo_si_esquema_es_identico_al_del_archivo_env(self) -> None:
        ajustes = obtener_ajustes()
        env_identico = {
            "DIRPOLES_TEST_BD": "1",
            "DIRPOLES_TEST_DB_NAME_BUSINESS": ajustes.db_name_business,
            "DIRPOLES_TEST_DB_NAME_SECURITY": "seguridad_test",
        }
        with patch.dict(os.environ, env_identico, clear=True):
            seguro, motivo, config = validar_seguridad_entorno_pruebas()
            self.assertFalse(seguro)
            self.assertIn("BLOQUEO DE SEGURIDAD", motivo)
            self.assertIsNone(config)

    def test_bloqueo_si_nombre_de_bd_no_incluye_palabra_test(self) -> None:
        env_sin_marca_test = {
            "DIRPOLES_TEST_BD": "1",
            "DIRPOLES_TEST_DB_NAME_BUSINESS": "otra_base_de_datos",
            "DIRPOLES_TEST_DB_NAME_SECURITY": "otra_seguridad",
        }
        with patch.dict(os.environ, env_sin_marca_test, clear=True):
            seguro, motivo, config = validar_seguridad_entorno_pruebas()
            self.assertFalse(seguro)
            self.assertIn("debe contener el prefijo/sufijo 'test' o 'prueba'", motivo)
            self.assertIsNone(config)

    def test_aprobacion_cuando_entorno_aislado_es_valido_y_seguro(self) -> None:
        env_seguro = {
            "DIRPOLES_TEST_BD": "1",
            "DIRPOLES_TEST_DB_HOST": "127.0.0.1",
            "DIRPOLES_TEST_DB_PORT": "3307",
            "DIRPOLES_TEST_DB_USER": "test_user",
            "DIRPOLES_TEST_DB_PASSWORD": "secret_test_password",
            "DIRPOLES_TEST_DB_NAME_BUSINESS": "dirpoles_business_test",
            "DIRPOLES_TEST_DB_NAME_SECURITY": "dirpoles_security_test",
        }
        with patch.dict(os.environ, env_seguro, clear=True):
            seguro, motivo, config = validar_seguridad_entorno_pruebas()
            self.assertTrue(seguro)
            self.assertIn("Entorno de pruebas aislado verificado y seguro", motivo)
            self.assertIsNotNone(config)
            assert config is not None
            self.assertEqual(config.name_business, "dirpoles_business_test")
            self.assertEqual(config.name_security, "dirpoles_security_test")
            self.assertEqual(config.port, 3307)

    def test_activacion_y_restauracion_del_motor_de_pruebas(self) -> None:
        config = ConfiguracionPruebasBD(
            host="127.0.0.1",
            port=3306,
            user="user_test",
            password="pwd",
            name_business="dirpoles_business_test",
            name_security="dirpoles_security_test",
        )
        motor_original = session._motor
        ajustes_orig_b = obtener_ajustes().db_name_business
        ajustes_orig_s = obtener_ajustes().db_name_security

        try:
            activar_motor_pruebas(config)
            self.assertIsNotNone(session._motor)
            self.assertEqual(obtener_ajustes().db_name_business, "dirpoles_business_test")
            self.assertEqual(obtener_ajustes().db_name_security, "dirpoles_security_test")
        finally:
            restaurar_motor_original()

        self.assertEqual(session._motor, motor_original)
        self.assertEqual(obtener_ajustes().db_name_business, ajustes_orig_b)
        self.assertEqual(obtener_ajustes().db_name_security, ajustes_orig_s)


if __name__ == "__main__":
    unittest.main()
