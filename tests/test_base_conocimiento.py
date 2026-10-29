"""Pruebas unitarias para la Base de Conocimiento y su desacoplamiento (Fase 3).

Verifica:
1. Conformidad de ConocimientoDirpoles4 con el protocolo BaseConocimiento.
2. Resolución de roles, enfoques, catálogos cerrados y alertas autorizadas.
3. Capacidad de inyectar una BaseConocimiento personalizada (otro consumidor)
   en prompt_service sin modificar el núcleo.
"""

import unittest

from app.knowledge.base import BaseConocimiento
from app.knowledge.dirpoles4 import (
    ConocimientoDirpoles4,
    PLANTILLAS_ALERTAS_AUTORIZADAS,
    ROLES_POR_MODULO,
    es_alerta_autorizada,
)
from app.schemas.enums import Intencion, Modulo
from app.services import prompt_service


class BaseConocimientoHospitalarioPrueba:
    """Base de conocimiento simulada para un hipotético sistema hospitalario externo."""

    def obtener_rol(self, modulo: str) -> str:
        return "Director de Epidemiología Hospitalaria"

    def obtener_enfoque(self, intencion: str) -> str:
        return "Enfoque clínico de triaje y disponibilidad de camas UCI."

    def obtener_dominios_distribuciones(self) -> dict[str, frozenset[str]]:
        return {
            "por_triage": frozenset({"Rojo", "Amarillo", "Verde"}),
        }

    def es_alerta_autorizada(self, mensaje: str, nivel: str) -> bool:
        return "UCI" in mensaje and nivel in {"critico", "advertencia"}

    def resolver_directriz(self, texto: str | None) -> str:
        return "Atención prioritaria a pacientes pediátricos." if texto else "Protocolo estándar."


class TestBaseConocimiento(unittest.TestCase):
    def test_conformidad_protocolo_dirpoles4(self) -> None:
        kb = ConocimientoDirpoles4()
        self.assertIsInstance(kb, BaseConocimiento)

    def test_roles_y_enfoques_cubren_enums_dirpoles4(self) -> None:
        kb = ConocimientoDirpoles4()
        for mod in Modulo:
            rol = kb.obtener_rol(mod)
            self.assertIsInstance(rol, str)
            self.assertGreater(len(rol), 10)

        for inte in Intencion:
            enfoque = kb.obtener_enfoque(inte)
            self.assertIsInstance(enfoque, str)
            self.assertGreater(len(enfoque), 10)

    def test_dominios_distribuciones_incluyen_pnf_oficial(self) -> None:
        kb = ConocimientoDirpoles4()
        dominios = kb.obtener_dominios_distribuciones()
        self.assertIn("por_pnf", dominios)
        self.assertIn("PNF Informática", dominios["por_pnf"])
        self.assertIn("por_genero", dominios)
        self.assertEqual(dominios["por_genero"], frozenset({"Masculino", "Femenino", "No especificado"}))

    def test_alertas_autorizadas_validacion(self) -> None:
        kb = ConocimientoDirpoles4()
        self.assertTrue(
            kb.es_alerta_autorizada(
                "3 insumo(s) por debajo del umbral crítico (10 unidades).",
                "critico",
            )
        )
        self.assertTrue(
            kb.es_alerta_autorizada(
                "El área 'Becas' concentra el 65% de las atenciones del periodo.",
                "advertencia",
            )
        )
        # Rechaza texto arbitrario no contemplado en plantillas
        self.assertFalse(
            kb.es_alerta_autorizada(
                "Texto inventado arbitrario con posible PII de Juan Perez.",
                "advertencia",
            )
        )

    def test_inyeccion_conocimiento_personalizado_en_prompt_service(self) -> None:
        """Demuestra que prompt_service puede construir prompts para otro sistema

        consumidor utilizando su propia BaseConocimiento sin tocar el código central.
        """
        kb_hospital = BaseConocimientoHospitalarioPrueba()
        system, user = prompt_service.construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen={"modulo": "urgencias", "periodo": {}},
            observacion_usuario="Instrucción de prueba",
            conocimiento=kb_hospital,
        )

        self.assertIn("Director de Epidemiología Hospitalaria", system)
        self.assertIn("Enfoque clínico de triaje y disponibilidad de camas UCI.", user)
        self.assertIn("Atención prioritaria a pacientes pediátricos.", user)


if __name__ == "__main__":
    unittest.main()
