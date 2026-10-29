import unittest

from app.schemas.enums import Intencion, Modulo
from app.services import prompt_service


class TestPromptService(unittest.TestCase):
    def test_roles_cubren_los_10_modulos(self) -> None:
        self.assertEqual(set(prompt_service.ROLES_POR_MODULO), set(Modulo))

    def test_intenciones_cubren_el_catalogo(self) -> None:
        self.assertEqual(set(prompt_service.ENFOQUE_POR_INTENCION), set(Intencion))

    def test_system_prompt_contiene_rol_y_regla_de_exclusividad(self) -> None:
        prompt = prompt_service.construir_system_prompt(Modulo.MEDICINA)
        self.assertIn("Especialista en gestión de servicios médicos universitarios", prompt)
        self.assertIn("EXCLUSIVAMENTE", prompt)
        self.assertIn("MARKDOWN", prompt.upper())

    def test_user_prompt_estructura_completa(self) -> None:
        resumen = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-09-30"},
            "totales": {"consultas": 450},
            "alertas": [],
            "registros_procesados": 450,
        }
        system, user = prompt_service.construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario="Enfocarse en insumos con bajo stock.",
        )
        self.assertIn("Módulo Analizado: medicina", user)
        self.assertIn("Intención del Informe: alertas_y_anomalias", user)
        self.assertIn("2026-01-01 a 2026-09-30", user)
        self.assertNotIn("Enfocarse en insumos con bajo stock.", user)
        self.assertIn("Ninguna indicación adicional.", user)
        self.assertIn("Resumen Ejecutivo", user)
        self.assertIn("Hallazgos Clave y Puntos Críticos", user)
        self.assertIn("Recomendaciones Operativas", user)
        self.assertIn('"consultas": 450', user)
        self.assertTrue(system.startswith("Eres un "))

    def test_user_prompt_sin_observacion_usa_por_defecto(self) -> None:
        _, user = prompt_service.construir_prompts(
            modulo=Modulo.GENERAL,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen={"periodo": {}},
            observacion_usuario=None,
        )
        self.assertIn("Ninguna indicación adicional.", user)
        self.assertIn("inicio de los registros a la fecha actual", user)

    def test_por_pnf_catalogo_oficial_autorizado_y_filtrado(self) -> None:
        """Verifica que por_pnf se transmita al prompt externo cuando pertenezca al catálogo oficial cerrado."""
        # 1. Caso válido con PNFs oficiales
        resumen_valido = {
            "modulo": "medicina",
            "periodo": {},
            "totales": {"consultas": 15},
            "distribuciones": {
                "por_genero": [{"valor": "Femenino", "cantidad": 10, "porcentaje": 66.67}],
                "por_pnf": [
                    {"valor": "PNF Informática", "cantidad": 10, "porcentaje": 66.67},
                    {"valor": "PNF Administración", "cantidad": 5, "porcentaje": 33.33},
                ],
            },
            "alertas": [],
        }
        seguro_valido = prompt_service.filtrar_contexto_seguro(resumen_valido)
        self.assertIn("por_pnf", seguro_valido["distribuciones"])
        self.assertEqual(len(seguro_valido["distribuciones"]["por_pnf"]), 2)
        valores_pnf = [item["valor"] for item in seguro_valido["distribuciones"]["por_pnf"]]
        self.assertIn("PNF Informática", valores_pnf)
        self.assertIn("PNF Administración", valores_pnf)

        # 2. Caso con PNF histórico inactivo ('PNF Sistemas informáticos')
        resumen_historico = {
            "modulo": "medicina",
            "periodo": {},
            "totales": {"consultas": 3},
            "distribuciones": {
                "por_pnf": [
                    {"valor": "PNF Sistemas informáticos", "cantidad": 3, "porcentaje": 100.0},
                ],
            },
            "alertas": [],
        }
        seguro_historico = prompt_service.filtrar_contexto_seguro(resumen_historico)
        self.assertIn("por_pnf", seguro_historico["distribuciones"])
        self.assertEqual(seguro_historico["distribuciones"]["por_pnf"][0]["valor"], "PNF Sistemas informáticos")

        # 3. Caso con PNF no autorizado / canario sintético (debe excluirse totalmente)
        resumen_invalido = {
            "modulo": "medicina",
            "periodo": {},
            "totales": {"consultas": 5},
            "distribuciones": {
                "por_genero": [{"valor": "Femenino", "cantidad": 5, "porcentaje": 100.0}],
                "por_pnf": [
                    {"valor": "CANARIO_PNF_NO_AUTORIZADO", "cantidad": 5, "porcentaje": 100.0},
                ],
            },
            "alertas": [],
        }
        seguro_invalido = prompt_service.filtrar_contexto_seguro(resumen_invalido)
        self.assertIn("por_genero", seguro_invalido["distribuciones"])
        self.assertNotIn("por_pnf", seguro_invalido["distribuciones"])

        # 4. Caso mixto (válido + inválido): principio todo o nada (debe excluir la distribución completa)
        resumen_mixto = {
            "modulo": "medicina",
            "periodo": {},
            "totales": {"consultas": 12},
            "distribuciones": {
                "por_genero": [{"valor": "Masculino", "cantidad": 12, "porcentaje": 100.0}],
                "por_pnf": [
                    {"valor": "PNF Informática", "cantidad": 10, "porcentaje": 83.33},
                    {"valor": "Ingeniería Aeroespacial No Oficial", "cantidad": 2, "porcentaje": 16.67},
                ],
            },
            "alertas": [],
        }
        seguro_mixto = prompt_service.filtrar_contexto_seguro(resumen_mixto)
        self.assertIn("por_genero", seguro_mixto["distribuciones"])
        self.assertNotIn("por_pnf", seguro_mixto["distribuciones"])


if __name__ == "__main__":
    unittest.main()
