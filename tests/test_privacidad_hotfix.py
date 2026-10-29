"""Pruebas unitarias de frontera de privacidad y hotfix de PII para DIRPOLES-IA.

Verifica de forma exhaustiva y recursiva que datos personales identificables (PII),
muestras de filas individuales, identificadores personales, textos clínicos individuales
y valores anidados no autorizados no alcancen el prompt enviado a Google Gemini ni
la llamada al SDK, cubriendo todas las especificaciones de las Tareas 01 y 01.1.
"""

from datetime import date
import json
import unittest
from unittest.mock import MagicMock

import pandas as pd

from app.schemas.enums import Intencion, Modulo
from app.schemas.request import FiltrosDTO, ReporteRequestDTO
from app.schemas.response import MetaDTO, ReporteResponseDTO
from app.services import gemini_service
from app.services.etl_service import Extraccion, transformar
from app.services.prompt_service import (
    CAMPOS_PERMITIDOS_LLM,
    DIRECTRICES_CANONICAS,
    construir_prompts,
    construir_user_prompt,
    filtrar_contexto_seguro,
    resolver_observacion_para_prompt,
    sanitizar_observacion_usuario,
)

# Cadenas centinela sintéticas únicas para detección inequívoca de fuga de PII e individualidades
SENTINEL_NOMBRE = "SENTINEL_NOMBRE_ESTUDIANTE_XYZ_9999"
SENTINEL_APELLIDO = "SENTINEL_APELLIDO_ESTUDIANTE_XYZ_8888"
SENTINEL_CEDULA = "V-99887766-SENTINEL"
SENTINEL_ID_BENEFICIARIO = "ID-BENEF-SENTINEL-0001"
SENTINEL_TEXTO_CLINICO_TRATAMIENTO = "SENTINEL_TRATAMIENTO_INDIVIDUAL_SECRETO_7777"
SENTINEL_DESCRIPCION_CASO = "SENTINEL_DESCRIPCION_CASO_INDIVIDUAL_6666"
SENTINEL_DETALLE_EXTRA = "SENTINEL_DETALLE_EXTRA_GESTACION_5555"
SENTINEL_ANIDADO_DICT = "SENTINEL_ROUE_DICT_ANIDADO_4444"
SENTINEL_ANIDADO_ALERTA = "SENTINEL_ROUE_ALERTA_ANIDADA_3333"
SENTINEL_ANIDADO_DIST = "SENTINEL_ROUE_DISTRIBUCION_ANIDADA_2222"
SENTINEL_OBS_SENSIBLE = "SENTINEL_TEXTO_OBSERVACION_SENSIBLE_1111"
SENTINEL_XSS = "SENTINEL_XSS_INYECCION_0000"

TODOS_LOS_SENTINELAS = [
    SENTINEL_NOMBRE,
    SENTINEL_APELLIDO,
    SENTINEL_CEDULA,
    SENTINEL_ID_BENEFICIARIO,
    SENTINEL_TEXTO_CLINICO_TRATAMIENTO,
    SENTINEL_DESCRIPCION_CASO,
    SENTINEL_DETALLE_EXTRA,
    SENTINEL_ANIDADO_DICT,
    SENTINEL_ANIDADO_ALERTA,
    SENTINEL_ANIDADO_DIST,
    SENTINEL_OBS_SENSIBLE,
    SENTINEL_XSS,
]


def _crear_extraccion_sintetica_medicina() -> Extraccion:
    consultas = pd.DataFrame(
        [
            {
                "id_beneficiario": SENTINEL_ID_BENEFICIARIO,
                "fecha": date(2026, 3, 1),
                "nombres": SENTINEL_NOMBRE,
                "apellidos": SENTINEL_APELLIDO,
                "cedula": SENTINEL_CEDULA,
                "genero": "M",
                "id_pnf": 1,
                "nombre_pnf": "PNF Informática",
                "motivo": "Fiebre",
                "diagnostico": "Gripe",
                "tratamiento": SENTINEL_TEXTO_CLINICO_TRATAMIENTO,
                "descripcion_caso": SENTINEL_DESCRIPCION_CASO,
            },
            {
                "id_beneficiario": "ID-BENEF-0002",
                "fecha": date(2026, 3, 15),
                "nombres": "EstudianteDos",
                "apellidos": "ApellidoDos",
                "cedula": "V-11223344",
                "genero": "F",
                "id_pnf": 1,
                "nombre_pnf": "PNF Informática",
                "motivo": "Control general",
                "diagnostico": "Sano",
                "tratamiento": "Reposo e hidratación",
                "descripcion_caso": "Evaluación rutinaria",
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
            }
        ]
    )
    return Extraccion(
        datos={"consultas": consultas, "insumos": insumos},
        totales={"consultas": 2, "insumos": 1},
    )


def _crear_extraccion_sintetica_general() -> Extraccion:
    atenciones = pd.DataFrame(
        [
            {
                "id_beneficiario": SENTINEL_ID_BENEFICIARIO,
                "nombres": SENTINEL_NOMBRE,
                "apellidos": SENTINEL_APELLIDO,
                "cedula": SENTINEL_CEDULA,
                "genero": "F",
                "id_pnf": 2,
                "nombre_pnf": "PNF Administración",
                "area": "Medicina",
                "fecha": date(2026, 3, 10),
            }
        ]
    )
    return Extraccion(datos={"atenciones": atenciones}, totales={"atenciones": 1})


def _crear_extraccion_sintetica_trabajo_social() -> Extraccion:
    registros = pd.DataFrame(
        [
            {
                "submodulo": "Gestión Embarazo",
                "fecha": date(2026, 3, 5),
                "id_beneficiario": SENTINEL_ID_BENEFICIARIO,
                "nombres": SENTINEL_NOMBRE,
                "apellidos": SENTINEL_APELLIDO,
                "cedula": SENTINEL_CEDULA,
                "genero": "F",
                "id_pnf": 1,
                "nombre_pnf": "PNF Informática",
                "detalle_extra": SENTINEL_DETALLE_EXTRA,
            }
        ]
    )
    return Extraccion(datos={"registros": registros}, totales={"registros": 1})


class TestFronteraPrivacidad(unittest.TestCase):
    """Suite de verificación del hotfix de privacidad y endurecimiento (Fase 0 y Tarea 01.1)."""

    def test_prueba_a_exclusion_de_datos_individuales_medicina(self) -> None:
        """Prueba A: Cadenas centinela de PII y datos individuales no deben aparecer en el prompt."""
        extraccion = _crear_extraccion_sintetica_medicina()
        filtros = FiltrosDTO()
        resumen = transformar(Modulo.MEDICINA, extraccion, filtros)

        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario="Foco en alertas generales.",
        )

        for sentinela in TODOS_LOS_SENTINELAS:
            self.assertNotIn(
                sentinela,
                user_prompt,
                f"Fuga detectada: el centinela '{sentinela}' aparece en user_prompt",
            )
            self.assertNotIn(
                sentinela,
                system_prompt,
                f"Fuga detectada: el centinela '{sentinela}' aparece en system_prompt",
            )

        # Verificar que 'ejemplos' no existe en el resumen ni en el JSON del user_prompt
        self.assertNotIn("ejemplos", resumen)
        self.assertNotIn('"ejemplos"', user_prompt)

    def test_prueba_a_exclusion_de_datos_individuales_general(self) -> None:
        """Prueba A (General): Nombres y cédulas no deben filtrarse en el módulo General."""
        extraccion = _crear_extraccion_sintetica_general()
        resumen = transformar(Modulo.GENERAL, extraccion, FiltrosDTO())

        _, user_prompt = construir_prompts(
            modulo=Modulo.GENERAL,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=None,
        )

        self.assertNotIn(SENTINEL_NOMBRE, user_prompt)
        self.assertNotIn(SENTINEL_APELLIDO, user_prompt)
        self.assertNotIn(SENTINEL_CEDULA, user_prompt)
        self.assertNotIn(SENTINEL_ID_BENEFICIARIO, user_prompt)
        self.assertNotIn("ejemplos", resumen)

    def test_prueba_a_exclusion_de_datos_individuales_trabajo_social(self) -> None:
        """Prueba A (Trabajo Social): Detalle extra individual y nombres no deben filtrarse."""
        extraccion = _crear_extraccion_sintetica_trabajo_social()
        resumen = transformar(Modulo.TRABAJO_SOCIAL, extraccion, FiltrosDTO())

        _, user_prompt = construir_prompts(
            modulo=Modulo.TRABAJO_SOCIAL,
            intencion=Intencion.RECOMENDACIONES,
            resumen=resumen,
            observacion_usuario="Priorizar casos vulnerables",
        )

        self.assertNotIn(SENTINEL_NOMBRE, user_prompt)
        self.assertNotIn(SENTINEL_APELLIDO, user_prompt)
        self.assertNotIn(SENTINEL_CEDULA, user_prompt)
        self.assertNotIn(SENTINEL_DETALLE_EXTRA, user_prompt)
        self.assertNotIn("ejemplos", resumen)

    def test_prueba_b_validacion_contexto_permitido_allowlist(self) -> None:
        """Prueba B: Solo los campos en CAMPOS_PERMITIDOS_LLM se transmiten al prompt."""
        resumen_con_claves_no_autorizadas = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 100,
            "totales": {"consultas": 100},
            "distribuciones": {"por_genero": []},
            "comparativa": None,
            "serie_mensual": [],
            "top_areas_concentracion": [],
            "indicadores": {"insumos": {}},
            "secciones": {},
            "alertas": [],
            # Claves no autorizadas añadidas artificialmente en primer nivel
            "ejemplos": [{"nombre": SENTINEL_NOMBRE, "tratamiento": SENTINEL_TEXTO_CLINICO_TRATAMIENTO}],
            "filas_crudas": [{"id": 1, "cedula": SENTINEL_CEDULA}],
            "pacientes": ["Paciente Uno", "Paciente Dos"],
            "historias_clinicas": {"101": SENTINEL_DESCRIPCION_CASO},
        }

        contexto_seguro = filtrar_contexto_seguro(resumen_con_claves_no_autorizadas)

        # Comprobar que únicamente las claves de la allowlist están presentes
        for clave in contexto_seguro:
            self.assertIn(
                clave,
                CAMPOS_PERMITIDOS_LLM,
                f"Clave no autorizada '{clave}' encontrada en contexto seguro",
            )

        # Comprobar exclusión explícita de campos crudos
        self.assertNotIn("ejemplos", contexto_seguro)
        self.assertNotIn("filas_crudas", contexto_seguro)
        self.assertNotIn("pacientes", contexto_seguro)
        self.assertNotIn("historias_clinicas", contexto_seguro)

        # Comprobar que construir_user_prompt no incluye ninguna clave ni centinela no autorizado
        user_prompt = construir_user_prompt(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen_con_claves_no_autorizadas,
            observacion_usuario=None,
        )
        self.assertNotIn(SENTINEL_NOMBRE, user_prompt)
        self.assertNotIn(SENTINEL_CEDULA, user_prompt)
        self.assertNotIn(SENTINEL_TEXTO_CLINICO_TRATAMIENTO, user_prompt)
        self.assertNotIn(SENTINEL_DESCRIPCION_CASO, user_prompt)
        self.assertNotIn("filas_crudas", user_prompt)
        self.assertNotIn("historias_clinicas", user_prompt)

    def test_revisión_d1_centinela_en_diccionario_anidado_bajo_clave_permitida(self) -> None:
        """Revisión D.1: Centinela inyectado en diccionario anidado bajo clave permitida debe ser purgado."""
        resumen = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 50,
            "totales": {"consultas": 50},
            "indicadores": {
                "insumos": {
                    "vencidos": 1,
                    "por_vencer_30_dias": 0,
                    "stock_critico": [],
                    # Inyección de diccionario no autorizado dentro de indicadores.insumos
                    "rogue_subdict": {"fuga_paciente": SENTINEL_ANIDADO_DICT},
                },
                # Inyección de clave no autorizada a nivel de indicadores
                "paciente_infiltrado": {"nombre": SENTINEL_ANIDADO_DICT},
            },
            "alertas": [],
        }

        contexto_seguro = filtrar_contexto_seguro(resumen)
        _, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario="Foco en insumos",
        )

        self.assertNotIn(SENTINEL_ANIDADO_DICT, user_prompt)
        self.assertNotIn("rogue_subdict", user_prompt)
        self.assertNotIn("paciente_infiltrado", user_prompt)
        self.assertNotIn("paciente_infiltrado", contexto_seguro.get("indicadores", {}))
        self.assertNotIn("rogue_subdict", contexto_seguro.get("indicadores", {}).get("insumos", {}))

    def test_revisión_d2_centinela_en_lista_anidada_alerta_o_distribucion(self) -> None:
        """Revisión D.2: Centinela inyectado en campos extra de listas (alertas/distribuciones) debe ser purgado."""
        resumen = {
            "modulo": "psicologia",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 40,
            "totales": {"morbilidad": 40},
            "distribuciones": {
                "por_genero": [
                    {
                        "valor": "Femenino",
                        "cantidad": 25,
                        "porcentaje": 62.5,
                        # Campo no tipado inyectado dentro del elemento de distribución
                        "inyeccion_rogue": SENTINEL_ANIDADO_DIST,
                    }
                ]
            },
            "alertas": [
                {
                    "nivel": "advertencia",
                    "mensaje": "Alerta legítima de inasistencia",
                    # Campo no tipado inyectado dentro de la alerta
                    "paciente_secreto": SENTINEL_ANIDADO_ALERTA,
                }
            ],
        }

        contexto_seguro = filtrar_contexto_seguro(resumen)
        _, user_prompt = construir_prompts(
            modulo=Modulo.PSICOLOGIA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario=None,
        )

        # Ni el centinela de distribución ni el de alerta deben aparecer en el prompt
        self.assertNotIn(SENTINEL_ANIDADO_DIST, user_prompt)
        self.assertNotIn(SENTINEL_ANIDADO_ALERTA, user_prompt)
        self.assertNotIn("inyeccion_rogue", user_prompt)
        self.assertNotIn("paciente_secreto", user_prompt)

        # Comprobar que los campos legítimos sí se conservan
        dist_item = contexto_seguro["distribuciones"]["por_genero"][0]
        self.assertEqual(dist_item["valor"], "Femenino")
        self.assertEqual(dist_item["cantidad"], 25)
        self.assertNotIn("inyeccion_rogue", dist_item)

        alerta_item = contexto_seguro["alertas"][0]
        self.assertEqual(alerta_item["nivel"], "advertencia")
        self.assertIn("Alerta legítima", alerta_item["mensaje"])
        self.assertNotIn("paciente_secreto", alerta_item)

    def test_revisión_d3_sanitizacion_observacion_usuario_sensible(self) -> None:
        """Revisión D.3: Observación del usuario con cédulas, nombres etiquetados y centinelas debe ser redactada."""
        observacion_con_pii = (
            f"Por favor revisar al paciente: {SENTINEL_NOMBRE} con cédula V-12345678 y "
            f"identificación: {SENTINEL_CEDULA}. Contactar a usuario@uptaeb.edu.ve o teléfono 0412-5551234. "
            f"Tiene diagnóstico: {SENTINEL_OBS_SENSIBLE}."
        )

        observacion_saneada = sanitizar_observacion_usuario(observacion_con_pii)

        # Verificar redacción de centinelas e identificadores
        self.assertNotIn(SENTINEL_NOMBRE, observacion_saneada)
        self.assertNotIn("V-12345678", observacion_saneada)
        self.assertNotIn(SENTINEL_CEDULA, observacion_saneada)
        self.assertNotIn("usuario@uptaeb.edu.ve", observacion_saneada)
        self.assertNotIn("0412-5551234", observacion_saneada)
        self.assertNotIn(SENTINEL_OBS_SENSIBLE, observacion_saneada)

        # Verificar presencia de marcas de redacción
        self.assertIn("[DOCUMENTO_REDACTADO]", observacion_saneada)
        self.assertIn("[CORREO_REDACTADO]", observacion_saneada)
        self.assertIn("[TELEFONO_REDACTADO]", observacion_saneada)

        # Verificar en el prompt completo
        resumen = {"modulo": "medicina", "totales": {"consultas": 10}, "registros_procesados": 10}
        _, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=observacion_con_pii,
        )
        self.assertNotIn(SENTINEL_NOMBRE, user_prompt)
        self.assertNotIn(SENTINEL_CEDULA, user_prompt)
        self.assertNotIn(SENTINEL_OBS_SENSIBLE, user_prompt)
        self.assertNotIn("[DOCUMENTO_REDACTADO]", user_prompt)
        self.assertIn("Ninguna indicación adicional.", user_prompt)

    def test_revisión_d4_solicitud_completa_a_sdk_simulado_gemini(self) -> None:
        """Revisión D.4: Comprobar la solicitud exacta que recibe el SDK de Google GenAI sin llamadas de red."""
        extraccion = _crear_extraccion_sintetica_medicina()
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())

        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario="Analizar stock crítico",
        )

        contexto = {
            "resumen": filtrar_contexto_seguro(resumen),
            "intencion": Intencion.ALERTAS_Y_ANOMALIAS.value,
            "modulo": Modulo.MEDICINA.value,
        }

        # Instanciar ClienteGemini real con clave simulada (inicialización offline comprobada)
        cliente_gemini = gemini_service.ClienteGemini(
            api_key="AIzaPruebaOfflineSeguraSinRed",
            modelo="gemini-2.0-flash",
        )

        # Simular la llamada a models.generate_content en el SDK subyacente
        mock_respuesta = MagicMock()
        mock_respuesta.text = "### 📊 Informe Generado por Modelo Mock"
        cliente_gemini._cliente.models.generate_content = MagicMock(return_value=mock_respuesta)

        # Ejecutar generación
        informe_obtenido = cliente_gemini.generar_informe(system_prompt, user_prompt, contexto)

        # Validar que el SDK fue invocado exactamente una vez
        cliente_gemini._cliente.models.generate_content.assert_called_once()
        _, kwargs = cliente_gemini._cliente.models.generate_content.call_args

        # Validar argumentos exactos pasados al SDK de Google GenAI
        self.assertEqual(kwargs["model"], "gemini-2.0-flash")
        contents_enviado = kwargs["contents"]
        system_instruction_enviada = kwargs["config"].system_instruction

        self.assertEqual(contents_enviado, user_prompt)
        self.assertEqual(system_instruction_enviada, system_prompt)

        # Validar ausencia total de centinelas en todos los argumentos de llamada al SDK
        for sentinela in TODOS_LOS_SENTINELAS:
            self.assertNotIn(sentinela, contents_enviado)
            self.assertNotIn(sentinela, system_instruction_enviada)

        self.assertEqual(informe_obtenido, "### 📊 Informe Generado por Modelo Mock")

    def test_revisión_d5_conservacion_de_metricas_y_alertas_legitimas(self) -> None:
        """Revisión D.5: Las métricas agregadas, distribuciones y alertas se conservan íntegras."""
        extraccion = _crear_extraccion_sintetica_medicina()
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        contexto_seguro = filtrar_contexto_seguro(resumen)

        # Totales conservados
        self.assertEqual(contexto_seguro["totales"]["consultas"], 2)
        self.assertEqual(contexto_seguro["totales"]["insumos"], 1)
        self.assertEqual(contexto_seguro["registros_procesados"], 3)

        # Alertas analíticas conservadas
        self.assertTrue(len(contexto_seguro["alertas"]) > 0)
        niveles = {a["nivel"] for a in contexto_seguro["alertas"]}
        self.assertIn("critico", niveles)

        # Distribuciones agregadas conservadas con dominio controlado
        distribuciones = contexto_seguro["distribuciones"]
        self.assertIn("por_genero", distribuciones)
        self.assertIn("por_pnf", distribuciones)

        # Indicadores de insumos conservados
        indicadores = contexto_seguro["indicadores"]["insumos"]
        self.assertEqual(indicadores["vencidos"], 1)
        self.assertEqual(indicadores["stock_critico"][0]["nombre"], "Insumo #1")

        # Serialización no vacía en user_prompt
        _, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario="Observación de prueba analítica",
        )
        self.assertIn('"consultas": 2', user_prompt)
        self.assertIn('"Insumo #1"', user_prompt)
        self.assertNotIn('"Paracetamol"', user_prompt)
        self.assertNotIn("Observación de prueba analítica", user_prompt)
        self.assertIn("Ninguna indicación adicional.", user_prompt)

    def test_revisión_d6_compatibilidad_cliente_simulado_y_response_dto(self) -> None:
        """Revisión D.6: El flujo de generación local y el DTO V1 se mantienen 100% compatibles."""
        extraccion = _crear_extraccion_sintetica_medicina()
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())

        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=None,
        )

        contexto = {
            "resumen": filtrar_contexto_seguro(resumen),
            "intencion": Intencion.RESUMEN_EJECUTIVO.value,
            "modulo": Modulo.MEDICINA.value,
        }

        # Generar informe mediante el motor determinista local
        cliente_simulado = gemini_service.ClienteSimulado()
        informe_markdown = cliente_simulado.generar_informe(
            system_prompt, user_prompt, contexto
        )

        # Validar estructura del Markdown
        self.assertIn("### 📊 Informe de Análisis Inteligente: Módulo Medicina", informe_markdown)
        self.assertIn("#### 1. Resumen Ejecutivo", informe_markdown)
        self.assertIn("#### 2. Hallazgos Clave y Puntos Críticos", informe_markdown)
        self.assertIn("#### 3. Recomendaciones Operativas", informe_markdown)
        self.assertIn("```mermaid", informe_markdown)
        self.assertIn("pie title", informe_markdown)

        # Validar que ningún centinela haya entrado en el informe simulado
        for sentinela in TODOS_LOS_SENTINELAS:
            self.assertNotIn(sentinela, informe_markdown)

        # Validar compatibilidad estricta con el contrato ReporteResponseDTO
        respuesta_dto = ReporteResponseDTO(
            exito=True,
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            informe_markdown=informe_markdown,
            meta=MetaDTO(
                registros_procesados=resumen["registros_procesados"],
                tiempo_procesamiento_seg=0.15,
                modo_informe=cliente_simulado.modo,
            ),
        )

        self.assertTrue(respuesta_dto.exito)
        self.assertEqual(respuesta_dto.modulo, Modulo.MEDICINA)
        self.assertEqual(respuesta_dto.meta.modo_informe, "simulado")
        self.assertEqual(respuesta_dto.meta.registros_procesados, 3)

        # Comprobar serialización JSON compatible
        dict_salida = respuesta_dto.model_dump()
        self.assertIn("informe_markdown", dict_salida)
        self.assertIn("meta", dict_salida)

    def test_revisión_d7_observacion_con_inyeccion_html_scripts(self) -> None:
        """Revisión D.7: Observación con inyección de HTML o scripts es neutralizada."""
        obs_con_html = f"<script>alert('{SENTINEL_XSS}')</script><b>Enfocarse en inventario</b>"
        saneada = sanitizar_observacion_usuario(obs_con_html)

        self.assertNotIn("<script>", saneada)
        self.assertNotIn("<b>", saneada)
        self.assertNotIn(SENTINEL_XSS, saneada)
        self.assertIn("Enfocarse en inventario", saneada)

    def _invocar_gemini_simulado(
        self,
        modulo: Modulo,
        intencion: Intencion,
        resumen: dict,
        observacion_usuario: str | None,
    ) -> tuple[str, dict]:
        """Captura la llamada exacta a models.generate_content y devuelve contents y kwargs."""
        system_prompt, user_prompt = construir_prompts(
            modulo=modulo,
            intencion=intencion,
            resumen=resumen,
            observacion_usuario=observacion_usuario,
        )
        contexto = {
            "resumen": filtrar_contexto_seguro(resumen),
            "intencion": intencion.value,
            "modulo": modulo.value,
        }
        cliente_gemini = gemini_service.ClienteGemini(
            api_key="AIzaPruebaOfflineSeguraSinRed",
            modelo="gemini-2.0-flash",
        )
        mock_respuesta = MagicMock()
        mock_respuesta.text = "### 📊 Informe Mock Generado"
        cliente_gemini._cliente.models.generate_content = MagicMock(return_value=mock_respuesta)
        cliente_gemini.generar_informe(system_prompt, user_prompt, contexto)

        cliente_gemini._cliente.models.generate_content.assert_called_once()
        _, kwargs = cliente_gemini._cliente.models.generate_content.call_args
        return kwargs["contents"], kwargs

    def test_tarea01_2_1_observacion_con_nombre_ficticio_en_prosa_no_llega_a_gemini(self) -> None:
        """1. Una observación con un nombre ficticio incrustado en prosa no llega a Gemini."""
        extraccion = _crear_extraccion_sintetica_medicina()
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        observacion_prosa = "El estudiante Carlos Mendoza requiere atención urgente en su seguimiento académico."

        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=observacion_prosa,
        )

        self.assertNotIn("Carlos Mendoza", contents)
        self.assertNotIn("Carlos", contents)
        self.assertNotIn("Mendoza", contents)
        self.assertNotIn("atención urgente", contents)
        self.assertNotIn("seguimiento académico", contents)
        self.assertIn("Ninguna indicación adicional.", contents)

    def test_tarea01_2_2_observacion_con_informacion_clinica_sintetica_no_llega_a_gemini(self) -> None:
        """2. Una observación con información clínica sintética no llega a Gemini."""
        extraccion = _crear_extraccion_sintetica_medicina()
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        observacion_clinica = "Paciente con diagnóstico de bronquitis aguda severa medicado con amoxicilina 500mg cada 8 horas."

        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario=observacion_clinica,
        )

        self.assertNotIn("bronquitis aguda", contents)
        self.assertNotIn("amoxicilina", contents)
        self.assertNotIn("500mg", contents)
        self.assertNotIn("cada 8 horas", contents)
        self.assertIn("Ninguna indicación adicional.", contents)

    def test_tarea01_2_3_observacion_con_cedula_ficticia_y_texto_adicional_no_llega_a_gemini(self) -> None:
        """3. Una observación con una cédula ficticia y texto adicional no llega a Gemini."""
        extraccion = _crear_extraccion_sintetica_medicina()
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        observacion_cedula = "Verificar expediente del titular con cédula V-28999888 antes de emitir constancia de servicio."

        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RECOMENDACIONES,
            resumen=resumen,
            observacion_usuario=observacion_cedula,
        )

        self.assertNotIn("V-28999888", contents)
        self.assertNotIn("28999888", contents)
        self.assertNotIn("Verificar expediente", contents)
        self.assertNotIn("constancia de servicio", contents)
        self.assertIn("Ninguna indicación adicional.", contents)

    def test_tarea01_2_4_valor_no_reconocido_no_termina_en_prompt_ni_en_contents(self) -> None:
        """4. Un valor no reconocido no termina en el prompt ni en el argumento contents del SDK simulado."""
        extraccion = _crear_extraccion_sintetica_medicina()
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        valor_arbitrario = "INSTRUCCION_CUSTOM_NO_RECONOCIDA_XYZ_999"

        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=valor_arbitrario,
        )

        self.assertNotIn(valor_arbitrario, contents)
        self.assertIn("Ninguna indicación adicional.", contents)

    def test_tarea01_2_5_metricas_agregadas_y_alertas_siguen_presentes(self) -> None:
        """5. Las métricas agregadas y las alertas siguen presentes."""
        resumen_analitico = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-06-30"},
            "totales": {"consultas": 789, "insumos": 42},
            "distribuciones": {
                "por_genero": [
                    {"valor": "Femenino", "cantidad": 450, "porcentaje": 57.0},
                    {"valor": "Masculino", "cantidad": 339, "porcentaje": 43.0},
                ]
            },
            "comparativa": {
                "mes_actual": {"mes": "2026-06", "cantidad": 150},
                "mes_anterior": {"mes": "2026-05", "cantidad": 130},
                "variacion_porcentual": 15.38,
                "tendencia": "incremento",
            },
            "serie_mensual": [{"mes": "2026-05", "cantidad": 130}, {"mes": "2026-06", "cantidad": 150}],
            "top_areas_concentracion": [],
            "indicadores": {"insumos": {"vencidos": 2, "por_vencer_30_dias": 5, "stock_critico": []}},
            "secciones": {},
            "alertas": [{"nivel": "critico", "mensaje": "Stock de insumos en nivel crítico (< 10)."}],
            "registros_procesados": 789,
        }

        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen_analitico,
            observacion_usuario="Cualquier texto no canónico",
        )

        # Comprobar métricas y agregaciones presentes en contents
        self.assertIn("789", contents)
        self.assertIn("Stock de insumos en nivel crítico (< 10).", contents)
        self.assertIn("Femenino", contents)
        self.assertIn("2026-01-01 a 2026-06-30", contents)
        self.assertIn("Módulo Analizado: medicina", contents)
        self.assertIn("Intención del Informe: alertas_y_anomalias", contents)
        self.assertNotIn("Cualquier texto no canónico", contents)

    def test_tarea01_2_6_respuesta_conserva_contrato_v1(self) -> None:
        """6. La respuesta conserva el contrato V1."""
        # 1. Validación de entrada vía ReporteRequestDTO
        peticion = ReporteRequestDTO(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            filtros=FiltrosDTO(fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 6, 30)),
            observacion_usuario="Texto arbitrario enviado desde el cliente V1",
            id_empleado=10,
        )
        self.assertEqual(peticion.modulo, Modulo.MEDICINA)
        self.assertEqual(peticion.observacion_usuario, "Texto arbitrario enviado desde el cliente V1")

        # 2. Generación con ClienteSimulado y verificación de respuesta vía ReporteResponseDTO
        cliente_simulado = gemini_service.ClienteSimulado()
        extraccion = _crear_extraccion_sintetica_medicina()
        resumen = transformar(Modulo.MEDICINA, extraccion, peticion.filtros)
        contexto_seguro = filtrar_contexto_seguro(resumen)

        system_prompt, user_prompt = construir_prompts(
            modulo=peticion.modulo,
            intencion=peticion.intencion,
            resumen=contexto_seguro,
            observacion_usuario=peticion.observacion_usuario,
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": peticion.intencion.value,
            "modulo": peticion.modulo.value,
        }

        informe_markdown = cliente_simulado.generar_informe(system_prompt, user_prompt, contexto)

        respuesta = ReporteResponseDTO(
            exito=True,
            modulo=peticion.modulo,
            intencion=peticion.intencion,
            informe_markdown=informe_markdown,
            meta=MetaDTO(
                registros_procesados=resumen["registros_procesados"],
                tiempo_procesamiento_seg=0.12,
                modo_informe=cliente_simulado.modo,
            ),
        )

        self.assertTrue(respuesta.exito)
        self.assertEqual(respuesta.modulo, Modulo.MEDICINA)
        self.assertEqual(respuesta.intencion, Intencion.ALERTAS_Y_ANOMALIAS)
        self.assertIn("Informe de Análisis Inteligente", respuesta.informe_markdown)
        self.assertEqual(respuesta.meta.modo_informe, "simulado")
        self.assertEqual(respuesta.meta.registros_procesados, 3)
        self.assertGreaterEqual(respuesta.meta.tiempo_procesamiento_seg, 0)

        # Verificar serialización JSON conforme a V1
        cuerpo_json = respuesta.model_dump()
        self.assertIn("exito", cuerpo_json)
        self.assertIn("modulo", cuerpo_json)
        self.assertIn("intencion", cuerpo_json)
        self.assertIn("informe_markdown", cuerpo_json)
        self.assertIn("meta", cuerpo_json)

    def test_tarea01_2_7_directriz_canonica_preaprobada_solo_usa_representacion_interna(self) -> None:
        """7. Si existe una directriz canónica preaprobada, solo se utiliza la representación interna autorizada."""
        clave_canonica = "DIRECTRIZ_TEST_STOCK_CRITICO"
        representacion_interna = "Instrucción interna predefinida: Focalizar el análisis exclusivamente en insumos con agotamiento inminente."

        # Registrar temporalmente en el catálogo canónico
        DIRECTRICES_CANONICAS[clave_canonica] = representacion_interna
        try:
            extraccion = _crear_extraccion_sintetica_medicina()
            resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())

            # Caso 7a: Coincidencia exacta con la directriz canónica
            contents, _ = self._invocar_gemini_simulado(
                modulo=Modulo.MEDICINA,
                intencion=Intencion.ALERTAS_Y_ANOMALIAS,
                resumen=resumen,
                observacion_usuario=clave_canonica,
            )

            # Debe contener la representación interna autorizada, NUNCA el texto original del usuario
            self.assertIn(representacion_interna, contents)

            # Caso 7b: Intento de inyectar texto extra junto con la clave canónica (no es coincidencia exacta)
            intento_inyeccion = f"{clave_canonica} y además atender al paciente Juan Perez con cédula V-12345678"
            contents_inyectado, _ = self._invocar_gemini_simulado(
                modulo=Modulo.MEDICINA,
                intencion=Intencion.ALERTAS_Y_ANOMALIAS,
                resumen=resumen,
                observacion_usuario=intento_inyeccion,
            )

            # Al no ser coincidencia exacta, se rechaza y no se incluye la directriz ni el texto añadido
            self.assertNotIn("Juan Perez", contents_inyectado)
            self.assertNotIn("V-12345678", contents_inyectado)
            self.assertNotIn(representacion_interna, contents_inyectado)
            self.assertIn("Ninguna indicación adicional.", contents_inyectado)
        finally:
            # Limpiar el registro temporal
            DIRECTRICES_CANONICAS.pop(clave_canonica, None)

    def test_tarea01_4_1_medicina_motivo_con_nombres_ficticios_no_aparece_en_gemini(self) -> None:
        """1. Medicina: un motivo de consulta con nombres ficticios no aparece en el prompt enviado a Gemini."""
        consultas = pd.DataFrame([
            {
                "fecha": date(2026, 3, 1),
                "genero": "F",
                "nombre_pnf": "PNF Informática",
                "motivo": "Consulta urgente para estudiante Juan Carlos Perez acompañado de su madre Maria Perez",
                "diagnostico": "Cefalea tensional",
            }
        ])
        extraccion = Extraccion(datos={"consultas": consultas, "insumos": pd.DataFrame()}, totales={"consultas": 1})
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=None,
        )

        self.assertNotIn("Juan Carlos Perez", contents)
        self.assertNotIn("Maria Perez", contents)
        self.assertNotIn("Consulta urgente", contents)
        self.assertNotIn("top_motivos", contents)

    def test_tarea01_4_2_medicina_diagnostico_sintetico_con_pii_no_aparece_en_gemini(self) -> None:
        """2. Medicina: un diagnóstico sintético que contiene información personal no aparece en el prompt."""
        consultas = pd.DataFrame([
            {
                "fecha": date(2026, 3, 1),
                "genero": "M",
                "nombre_pnf": "PNF Informática",
                "motivo": "Malestar general",
                "diagnostico": "Infección respiratoria aguda severa en paciente Pedro Morales CI 15444333",
            }
        ])
        extraccion = Extraccion(datos={"consultas": consultas, "insumos": pd.DataFrame()}, totales={"consultas": 1})
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario=None,
        )

        self.assertNotIn("Pedro Morales", contents)
        self.assertNotIn("15444333", contents)
        self.assertNotIn("Infección respiratoria aguda severa", contents)
        self.assertNotIn("top_diagnosticos", contents)

    def test_tarea01_4_3_psicologia_diagnostico_sensible_no_aparece_en_distribuciones_ni_alertas(self) -> None:
        """3. Psicología: un diagnóstico individual con información sensible no aparece en distribuciones ni alertas."""
        morbilidad = pd.DataFrame([
            {
                "fecha": date(2026, 3, 1),
                "tipo_consulta": "Individual",
                "nombre_pnf": "PNF Informática",
                "diagnostico": "Trastorno de adaptación con ideación suicida - Caso confidencial Sofia Ramirez",
            }
        ])
        citas = pd.DataFrame([{"fecha": date(2026, 3, 1), "estado": "Atendida"}])
        extraccion = Extraccion(
            datos={"morbilidad": morbilidad, "citas": citas},
            totales={"morbilidad": 1, "citas": 1},
        )
        resumen = transformar(Modulo.PSICOLOGIA, extraccion, FiltrosDTO())
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.PSICOLOGIA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario=None,
        )

        self.assertNotIn("Sofia Ramirez", contents)
        self.assertNotIn("Trastorno de adaptación", contents)
        self.assertNotIn("ideación suicida", contents)
        self.assertNotIn("top_diagnosticos", contents)
        # La alerta debe ser numérica y genérica
        self.assertIn("Una condición diagnóstica concentra el 100.0% de la morbilidad psicológica", contents)

    def test_tarea01_4_4_orientacion_motivo_individual_en_texto_libre_no_aparece_en_contexto_externo(self) -> None:
        """4. Orientación: un motivo individual en texto libre no aparece en el contexto externo."""
        casos = pd.DataFrame([
            {
                "fecha": date(2026, 3, 1),
                "genero": "M",
                "nombre_pnf": "PNF Informática",
                "motivo_consulta": "Problemas vocacionales y familiares del estudiante Diego Castro con el profesor Mendoza",
            }
        ])
        extraccion = Extraccion(datos={"casos": casos}, totales={"casos": 1})
        resumen = transformar(Modulo.ORIENTACION, extraccion, FiltrosDTO())
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.ORIENTACION,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=None,
        )

        self.assertNotIn("Diego Castro", contents)
        self.assertNotIn("profesor Mendoza", contents)
        self.assertNotIn("Problemas vocacionales", contents)
        self.assertNotIn("top_motivos", contents)

    def test_tarea01_4_5_jornadas_e_inventario_texto_no_controlado_excluido_de_salida_externa(self) -> None:
        """5. Jornadas e inventario: los valores de texto no controlados se excluyen de la salida externa."""
        insumos = pd.DataFrame([
            {
                "nombre_insumo": "InsumoExperimentalConfidencialXYZ",
                "cantidad": 1,
                "fecha_vencimiento": date(2026, 1, 1),
                "estatus": "Disponible",
            }
        ])
        extraccion_med = Extraccion(datos={"consultas": pd.DataFrame(), "insumos": insumos}, totales={"consultas": 0, "insumos": 1})
        resumen_med = transformar(Modulo.MEDICINA, extraccion_med, FiltrosDTO())
        contents_med, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen_med,
            observacion_usuario=None,
        )

        self.assertNotIn("InsumoExperimentalConfidencialXYZ", contents_med)
        self.assertIn("Insumo #1", contents_med)
        self.assertIn('"cantidad": 1', contents_med)

        jornadas = pd.DataFrame([
            {
                "nombre_jornada": "JornadaEspecialSecretaSectorABC",
                "tipo_jornada": "General",
                "fecha_inicio": date(2026, 3, 1),
                "estatus": "Finalizada",
                "aforo_maximo": 50,
                "total_asistentes": 60,
                "total_diagnosticos": 40,
            }
        ])
        extraccion_jor = Extraccion(datos={"jornadas": jornadas}, totales={"jornadas": 1})
        resumen_jor = transformar(Modulo.JORNADAS, extraccion_jor, FiltrosDTO())
        contents_jor, _ = self._invocar_gemini_simulado(
            modulo=Modulo.JORNADAS,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen_jor,
            observacion_usuario=None,
        )

        self.assertNotIn("JornadaEspecialSecretaSectorABC", contents_jor)
        self.assertIn("Jornada #1", contents_jor)
        self.assertIn('"aforo": 50', contents_jor)
        self.assertIn('"asistentes": 60', contents_jor)

    def test_tarea01_4_6_contenido_exacto_a_sdk_simulado_sin_centinelas(self) -> None:
        """6. El contenido exacto enviado al SDK simulado no contiene los centinelas sintéticos."""
        consultas = pd.DataFrame([
            {
                "id_beneficiario": SENTINEL_ID_BENEFICIARIO,
                "fecha": date(2026, 3, 1),
                "nombres": SENTINEL_NOMBRE,
                "apellidos": SENTINEL_APELLIDO,
                "cedula": SENTINEL_CEDULA,
                "genero": "M",
                "id_pnf": 1,
                "nombre_pnf": "PNF Informática",
                "motivo": SENTINEL_OBS_SENSIBLE,
                "diagnostico": SENTINEL_DESCRIPCION_CASO,
                "tratamiento": SENTINEL_TEXTO_CLINICO_TRATAMIENTO,
            }
        ])
        insumos = pd.DataFrame([
            {
                "nombre_insumo": "InsumoCentinelaTest",
                "cantidad": 1,
                "fecha_vencimiento": date(2026, 1, 1),
                "estatus": "Disponible",
            }
        ])
        extraccion = Extraccion(datos={"consultas": consultas, "insumos": insumos}, totales={"consultas": 1, "insumos": 1})
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario=f"Instruccion con {SENTINEL_NOMBRE}",
        )

        for sentinela in TODOS_LOS_SENTINELAS:
            self.assertNotIn(sentinela, contents)

    def test_tarea01_4_7_cliente_simulado_no_reintroduce_valores_eliminados(self) -> None:
        """7. ClienteSimulado tampoco reintroduce esos valores al generar el informe."""
        consultas = pd.DataFrame([
            {
                "id_beneficiario": SENTINEL_ID_BENEFICIARIO,
                "fecha": date(2026, 3, 1),
                "nombres": SENTINEL_NOMBRE,
                "apellidos": SENTINEL_APELLIDO,
                "cedula": SENTINEL_CEDULA,
                "genero": "F",
                "id_pnf": 1,
                "nombre_pnf": "PNF Informática",
                "motivo": "MotivoClinicoConfidencialXYZ",
                "diagnostico": "DiagnosticoClinicoConfidencialABC",
            }
        ])
        extraccion = Extraccion(datos={"consultas": consultas, "insumos": pd.DataFrame()}, totales={"consultas": 1})
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        contexto_seguro = filtrar_contexto_seguro(resumen)

        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=contexto_seguro,
            observacion_usuario="Indicacion libre",
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": Intencion.RESUMEN_EJECUTIVO.value,
            "modulo": Modulo.MEDICINA.value,
        }

        cliente_simulado = gemini_service.ClienteSimulado()
        informe = cliente_simulado.generar_informe(system_prompt, user_prompt, contexto)

        self.assertNotIn("MotivoClinicoConfidencialXYZ", informe)
        self.assertNotIn("DiagnosticoClinicoConfidencialABC", informe)
        for sentinela in TODOS_LOS_SENTINELAS:
            self.assertNotIn(sentinela, informe)
        self.assertIn("Informe de Análisis Inteligente: Módulo Medicina", informe)
        self.assertIn("Resumen Ejecutivo", informe)

    def test_tarea01_4_8_metricas_agregadas_legitimas_y_alertas_numericas_se_conservan(self) -> None:
        """8. Las métricas agregadas legítimas y las alertas numéricas que no dependen del texto retirado se conservan."""
        consultas = pd.DataFrame([
            {"fecha": date(2026, 3, 1), "genero": "F", "nombre_pnf": "PNF Informática"},
            {"fecha": date(2026, 3, 15), "genero": "M", "nombre_pnf": "PNF Administración"},
        ])
        insumos = pd.DataFrame([
            {"nombre_insumo": "InsumoA", "cantidad": 2, "fecha_vencimiento": date(2026, 1, 1), "estatus": "Disponible"},
        ])
        extraccion = Extraccion(datos={"consultas": consultas, "insumos": insumos}, totales={"consultas": 2, "insumos": 1})
        resumen = transformar(Modulo.MEDICINA, extraccion, FiltrosDTO())
        contexto_seguro = filtrar_contexto_seguro(resumen)

        self.assertEqual(contexto_seguro["totales"]["consultas"], 2)
        self.assertEqual(contexto_seguro["totales"]["insumos"], 1)
        self.assertEqual(contexto_seguro["registros_procesados"], 3)
        self.assertEqual(contexto_seguro["indicadores"]["insumos"]["vencidos"], 1)
        self.assertEqual(contexto_seguro["indicadores"]["insumos"]["stock_critico"][0]["cantidad"], 2)

        # Distribuciones con dominio controlado demostrado presentes
        self.assertIn("por_genero", contexto_seguro["distribuciones"])
        self.assertIn("por_pnf", contexto_seguro["distribuciones"])

        # Distribuciones sin dominio controlado demostrado ausentes
        self.assertNotIn("insumos_por_estatus", contexto_seguro["distribuciones"])

        # Distribuciones no controladas ausentes
        self.assertNotIn("top_diagnosticos", contexto_seguro["distribuciones"])
        self.assertNotIn("top_motivos", contexto_seguro["distribuciones"])

    def test_tarea01_4_9_reporte_response_dto_y_contrato_v1_mantienen_estructura(self) -> None:
        """9. ReporteResponseDTO y el contrato HTTP V1 mantienen su estructura."""
        peticion = ReporteRequestDTO(
            modulo=Modulo.PSICOLOGIA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            filtros=FiltrosDTO(),
            observacion_usuario="Cualquier texto",
        )
        self.assertEqual(peticion.modulo, Modulo.PSICOLOGIA)

        citas = pd.DataFrame([{"fecha": date(2026, 3, 1), "estado": "Atendida"}])
        extraccion = Extraccion(datos={"morbilidad": pd.DataFrame(), "citas": citas}, totales={"morbilidad": 0, "citas": 1})
        resumen = transformar(Modulo.PSICOLOGIA, extraccion, peticion.filtros)
        contexto_seguro = filtrar_contexto_seguro(resumen)

        cliente_simulado = gemini_service.ClienteSimulado()
        informe = cliente_simulado.generar_informe("sys", "user", {"resumen": contexto_seguro, "intencion": peticion.intencion.value, "modulo": peticion.modulo.value})

        respuesta = ReporteResponseDTO(
            exito=True,
            modulo=peticion.modulo,
            intencion=peticion.intencion,
            informe_markdown=informe,
            meta=MetaDTO(
                registros_procesados=contexto_seguro["registros_procesados"],
                tiempo_procesamiento_seg=0.08,
                modo_informe=cliente_simulado.modo,
            ),
        )
        self.assertTrue(respuesta.exito)
        self.assertEqual(respuesta.modulo, Modulo.PSICOLOGIA)
        self.assertEqual(respuesta.intencion, Intencion.ALERTAS_Y_ANOMALIAS)
        self.assertIn("meta", respuesta.model_dump())

    def test_tarea01_4_10_comportamiento_conjuntos_vacios_valores_nulos_y_categorias_faltantes(self) -> None:
        """10. El comportamiento ante conjuntos vacíos, valores nulos y categorías faltantes sigue siendo válido."""
        extraccion_vacia = Extraccion(datos={"consultas": pd.DataFrame(), "insumos": pd.DataFrame()}, totales={"consultas": 0, "insumos": 0})
        resumen_vacio = transformar(Modulo.MEDICINA, extraccion_vacia, FiltrosDTO())
        contexto_vacio = filtrar_contexto_seguro(resumen_vacio)

        self.assertEqual(contexto_vacio["registros_procesados"], 0)
        self.assertEqual(contexto_vacio["totales"]["consultas"], 0)
        self.assertIn("alertas", contexto_vacio)
        self.assertTrue(any("No se encontraron registros" in a["mensaje"] for a in contexto_vacio["alertas"]))

        # Con valores nulos
        df_nulos = pd.DataFrame([{"fecha": None, "genero": None, "nombre_pnf": None}])
        extraccion_nulos = Extraccion(datos={"consultas": df_nulos, "insumos": pd.DataFrame()}, totales={"consultas": 1, "insumos": 0})
        resumen_nulos = transformar(Modulo.MEDICINA, extraccion_nulos, FiltrosDTO())
        contexto_nulos = filtrar_contexto_seguro(resumen_nulos)

        self.assertEqual(contexto_nulos["registros_procesados"], 1)
        self.assertIn("No especificado", [it["valor"] for it in contexto_nulos["distribuciones"]["por_genero"]])

    def test_tarea01_4_1_inyeccion_sintetica_canarios_en_distribuciones(self) -> None:
        """Tarea 01.4.1 (1 y 2): Inyección sintética directa de canarios en distribuciones no autorizadas.

        Verifica que top_diagnosticos, top_motivos y cualquier distribución no autorizada
        sean eliminadas categóricamente del contexto seguro, del prompt enviado al SDK de Gemini
        y del informe producido por ClienteSimulado, preservando las autorizadas (por_genero).
        """
        canario_diag = "CANARIO_DIAGNOSTICO_847"
        canario_motivo = "CANARIO_MOTIVO_263"
        canario_desconocido = "CANARIO_DESCONOCIDO_591"

        resumen_inyeccion = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 100,
            "totales": {"consultas": 100},
            "distribuciones": {
                "top_diagnosticos": [
                    {"valor": canario_diag, "cantidad": 45, "porcentaje": 45.0}
                ],
                "top_motivos": [
                    {"valor": canario_motivo, "cantidad": 35, "porcentaje": 35.0}
                ],
                "distribucion_no_autorizada": [
                    {"valor": canario_desconocido, "cantidad": 20, "porcentaje": 20.0}
                ],
                "por_genero": [
                    {"valor": "Femenino", "cantidad": 60, "porcentaje": 60.0},
                    {"valor": "Masculino", "cantidad": 40, "porcentaje": 40.0},
                ],
            },
            "alertas": [],
        }

        # 1. Verificación en contexto_seguro
        contexto_seguro = filtrar_contexto_seguro(resumen_inyeccion)
        distribuciones_seguras = contexto_seguro["distribuciones"]

        self.assertNotIn("top_diagnosticos", distribuciones_seguras)
        self.assertNotIn("top_motivos", distribuciones_seguras)
        self.assertNotIn("distribucion_no_autorizada", distribuciones_seguras)
        self.assertIn("por_genero", distribuciones_seguras)

        contexto_str = json.dumps(contexto_seguro)
        self.assertNotIn(canario_diag, contexto_str)
        self.assertNotIn(canario_motivo, contexto_str)
        self.assertNotIn(canario_desconocido, contexto_str)
        self.assertIn("Femenino", contexto_str)
        self.assertIn("Masculino", contexto_str)

        # 2. Verificación en contents enviado al SDK de Gemini
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen_inyeccion,
            observacion_usuario=None,
        )

        self.assertNotIn(canario_diag, contents)
        self.assertNotIn(canario_motivo, contents)
        self.assertNotIn(canario_desconocido, contents)
        self.assertNotIn("top_diagnosticos", contents)
        self.assertNotIn("top_motivos", contents)
        self.assertNotIn("distribucion_no_autorizada", contents)
        self.assertIn("por_genero", contents)
        self.assertIn("Femenino", contents)
        self.assertIn("Masculino", contents)

        # 3. Verificación en informe generado por ClienteSimulado
        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=contexto_seguro,
            observacion_usuario=None,
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": Intencion.RESUMEN_EJECUTIVO.value,
            "modulo": Modulo.MEDICINA.value,
        }
        cliente_simulado = gemini_service.ClienteSimulado()
        informe_markdown = cliente_simulado.generar_informe(
            system_prompt, user_prompt, contexto
        )

        self.assertNotIn(canario_diag, informe_markdown)
        self.assertNotIn(canario_motivo, informe_markdown)
        self.assertNotIn(canario_desconocido, informe_markdown)
        self.assertNotIn("top_diagnosticos", informe_markdown)
        self.assertNotIn("top_motivos", informe_markdown)
        self.assertNotIn("distribucion_no_autorizada", informe_markdown)
        self.assertIn("Femenino", informe_markdown)
        self.assertIn("Masculino", informe_markdown)
        self.assertIn("por genero", informe_markdown.lower())

    def test_tarea01_4_1_campos_anidados_estatus_jornada_y_stock_critico(self) -> None:
        """Tarea 01.4.1 (3): Validación estricta de estatus en jornadas y campos de stock crítico.

        Verifica que ocupacion_por_jornada.estatus valide contra EstadoJornada y cualquier
        texto no controlado sea reemplazado por 'No especificado', y que los insumos de stock_critico
        tengan nombres genéricos y fechas controladas.
        """
        canario_jornada = "CANARIO_NOMBRE_JORNADA_999"
        canario_estatus = "CANARIO_ESTATUS_ROGUE_777"
        canario_insumo = "CANARIO_NOMBRE_INSUMO_888"
        canario_vencimiento = "CANARIO_VENCIMIENTO_666"
        canario_alerta = "CANARIO_NIVEL_ROGUE_555"

        resumen_anidado = {
            "modulo": "jornadas",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 50,
            "totales": {"jornadas": 2},
            "indicadores": {
                "ocupacion_por_jornada": [
                    {
                        "jornada": canario_jornada,
                        "estatus": canario_estatus,
                        "aforo": 20,
                        "asistentes": 15,
                        "ocupacion_pct": 75.0,
                    },
                    {
                        "jornada": "Jornada Legítima",
                        "estatus": "Finalizada",
                        "aforo": 30,
                        "asistentes": 30,
                        "ocupacion_pct": 100.0,
                    },
                ],
                "insumos": {
                    "vencidos": 1,
                    "por_vencer_30_dias": 0,
                    "stock_critico": [
                        {
                            "nombre": canario_insumo,
                            "cantidad": 2,
                            "vencimiento": canario_vencimiento,
                        },
                        {
                            "nombre": "Insumo Legítimo",
                            "cantidad": 1,
                            "vencimiento": "2026-11-30",
                        },
                    ],
                },
            },
            "alertas": [
                {
                    "nivel": canario_alerta,
                    "mensaje": "Alerta analítica sin PII.",
                }
            ],
        }

        contexto_seguro = filtrar_contexto_seguro(resumen_anidado)

        # 1. Validación en contexto seguro
        ocupacion = contexto_seguro["indicadores"]["ocupacion_por_jornada"]
        self.assertEqual(ocupacion[0]["jornada"], "Jornada #1")
        self.assertEqual(ocupacion[0]["estatus"], "No especificado")
        self.assertEqual(ocupacion[1]["jornada"], "Jornada #2")
        self.assertEqual(ocupacion[1]["estatus"], "Finalizada")

        stock = contexto_seguro["indicadores"]["insumos"]["stock_critico"]
        self.assertEqual(stock[0]["nombre"], "Insumo #1")
        self.assertEqual(stock[0]["vencimiento"], "N/A")
        self.assertEqual(stock[1]["nombre"], "Insumo #2")
        self.assertEqual(stock[1]["vencimiento"], "2026-11-30")

        self.assertEqual(contexto_seguro["alertas"][0]["nivel"], "info")

        # Ausencia de canarios en la serialización
        contexto_str = json.dumps(contexto_seguro)
        self.assertNotIn(canario_jornada, contexto_str)
        self.assertNotIn(canario_estatus, contexto_str)
        self.assertNotIn(canario_insumo, contexto_str)
        self.assertNotIn(canario_vencimiento, contexto_str)
        self.assertNotIn(canario_alerta, contexto_str)

        # 2. Ausencia en llamada al SDK de Gemini
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.JORNADAS,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen_anidado,
            observacion_usuario=None,
        )
        self.assertNotIn(canario_jornada, contents)
        self.assertNotIn(canario_estatus, contents)
        self.assertNotIn(canario_insumo, contents)
        self.assertNotIn(canario_vencimiento, contents)
        self.assertNotIn(canario_alerta, contents)
        self.assertIn("Finalizada", contents)
        self.assertIn("2026-11-30", contents)

        # 3. Ausencia en informe de ClienteSimulado
        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.JORNADAS,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=contexto_seguro,
            observacion_usuario=None,
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": Intencion.ALERTAS_Y_ANOMALIAS.value,
            "modulo": Modulo.JORNADAS.value,
        }
        cliente_simulado = gemini_service.ClienteSimulado()
        informe_markdown = cliente_simulado.generar_informe(
            system_prompt, user_prompt, contexto
        )
        self.assertNotIn(canario_jornada, informe_markdown)
        self.assertNotIn(canario_estatus, informe_markdown)
        self.assertNotIn(canario_insumo, informe_markdown)
        self.assertNotIn(canario_vencimiento, informe_markdown)
        self.assertNotIn(canario_alerta, informe_markdown)

    def test_tarea01_4_1_pydantic_validators_capa_defensa_en_profundidad(self) -> None:
        """Tarea 01.4.1: Los validadores Pydantic actúan como segunda línea de defensa."""
        from app.services.prompt_service import (
            ContextoAnaliticoSeguro,
            DistribucionItem,
            ItemOcupacionJornada,
            ItemStockCritico,
        )

        # 1. Distribución no autorizada inyectada directamente al modelo
        modelo_dist = ContextoAnaliticoSeguro(
            modulo="medicina",
            distribuciones={
                "top_diagnosticos": [
                    DistribucionItem(valor="CANARIO_DIAGNOSTICO_847", cantidad=1, porcentaje=100.0)
                ],
                "por_genero": [
                    DistribucionItem(valor="Femenino", cantidad=1, porcentaje=100.0)
                ],
            },
        )
        self.assertNotIn("top_diagnosticos", modelo_dist.distribuciones)
        self.assertIn("por_genero", modelo_dist.distribuciones)

        # 2. ItemOcupacionJornada con estatus no controlado
        item_oj = ItemOcupacionJornada(
            jornada="CANARIO_JORNADA",
            estatus="CANARIO_ESTATUS_INEXISTENTE",
            aforo=10,
            asistentes=5,
            ocupacion_pct=50.0,
        )
        self.assertEqual(item_oj.estatus, "No especificado")
        self.assertEqual(item_oj.jornada, "Jornada Genérica")

        # 3. ItemStockCritico con nombre o vencimiento no controlado
        item_sc = ItemStockCritico(
            nombre="Amoxicilina 500mg",
            cantidad=3,
            vencimiento="FECHA_TEXTO_NO_FORMATO",
        )
        self.assertEqual(item_sc.nombre, "Insumo Genérico")
        self.assertEqual(item_sc.vencimiento, "N/A")

    def test_tarea01_4_2_1_centinela_en_valor_distribucion_permitida(self) -> None:
        """Tarea 01.4.2 (1 y 5, 6): Un centinela como 'valor' en distribución permitida (por_genero)

        Verifica que si una distribución contiene una etiqueta ajena al dominio cerrado autorizado,
        no se presente parcialmente: se excluye del contexto externo y el centinela no llega al SDK ni al reporte simulado.
        """
        canario_genero_rogue = "CANARIO_VALOR_GENERO_ROGUE_991"

        resumen = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 100,
            "totales": {"consultas": 100},
            "distribuciones": {
                "por_genero": [
                    {"valor": "Femenino", "cantidad": 60, "porcentaje": 60.0},
                    {"valor": canario_genero_rogue, "cantidad": 40, "porcentaje": 40.0},
                ]
            },
            "alertas": [],
        }

        # 1. En contexto seguro: la distribución parcial/contaminada no se presenta
        contexto_seguro = filtrar_contexto_seguro(resumen)
        self.assertNotIn("por_genero", contexto_seguro["distribuciones"])
        self.assertNotIn(canario_genero_rogue, json.dumps(contexto_seguro))

        # 2. En argumento contents del SDK de Gemini
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=None,
        )
        self.assertNotIn(canario_genero_rogue, contents)
        self.assertNotIn("por_genero", contents)

        # 3. En informe Markdown de ClienteSimulado
        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=contexto_seguro,
            observacion_usuario=None,
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": Intencion.RESUMEN_EJECUTIVO.value,
            "modulo": Modulo.MEDICINA.value,
        }
        cliente_simulado = gemini_service.ClienteSimulado()
        informe = cliente_simulado.generar_informe(system_prompt, user_prompt, contexto)
        self.assertNotIn(canario_genero_rogue, informe)

    def test_tarea01_4_2_2_centinela_en_etiqueta_campo_sin_dominio_controlado(self) -> None:
        """Tarea 01.4.2 (2 y 5, 6): Un centinela en etiqueta de distribución sin dominio controlado demostrado (por_pnf, por_categoria, por_servicio_destino)

        Verifica que campos procedentes de tablas abiertas de BD sin dominio cerrado demostrado
        sean excluidos de la transmisión externa, asegurando ausencia de centinelas.
        """
        canario_pnf = "CANARIO_PNF_NO_CONTROLADO_772"
        canario_cat = "CANARIO_CATEGORIA_NO_CONTROLADA_661"
        canario_serv = "CANARIO_SERVICIO_NO_CONTROLADO_554"

        resumen = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 60,
            "totales": {"consultas": 60},
            "distribuciones": {
                "por_pnf": [
                    {"valor": canario_pnf, "cantidad": 30, "porcentaje": 50.0}
                ],
                "por_categoria": [
                    {"valor": canario_cat, "cantidad": 15, "porcentaje": 25.0}
                ],
                "por_servicio_destino": [
                    {"valor": canario_serv, "cantidad": 15, "porcentaje": 25.0}
                ],
            },
            "alertas": [],
        }

        contexto_seguro = filtrar_contexto_seguro(resumen)
        self.assertNotIn("por_pnf", contexto_seguro["distribuciones"])
        self.assertNotIn("por_categoria", contexto_seguro["distribuciones"])
        self.assertNotIn("por_servicio_destino", contexto_seguro["distribuciones"])

        contexto_str = json.dumps(contexto_seguro)
        self.assertNotIn(canario_pnf, contexto_str)
        self.assertNotIn(canario_cat, contexto_str)
        self.assertNotIn(canario_serv, contexto_str)

        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=resumen,
            observacion_usuario=None,
        )
        self.assertNotIn(canario_pnf, contents)
        self.assertNotIn(canario_cat, contents)
        self.assertNotIn(canario_serv, contents)

        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=contexto_seguro,
            observacion_usuario=None,
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": Intencion.RESUMEN_EJECUTIVO.value,
            "modulo": Modulo.MEDICINA.value,
        }
        cliente_simulado = gemini_service.ClienteSimulado()
        informe = cliente_simulado.generar_informe(system_prompt, user_prompt, contexto)
        self.assertNotIn(canario_pnf, informe)
        self.assertNotIn(canario_cat, informe)
        self.assertNotIn(canario_serv, informe)

    def test_tarea01_4_2_3_mensaje_alerta_con_centinela_y_nivel_valido(self) -> None:
        """Tarea 01.4.2 (3 y 5, 6): Un mensaje de alerta con un centinela y un nivel válido (advertencia/critico)

        Verifica que mensajes no vinculables a plantillas canónicas autorizadas del sistema no transmitan su texto original.
        """
        canario_alerta = "CANARIO_MENSAJE_ALERTA_ADVERTENCIA_883"

        resumen = {
            "modulo": "psicologia",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 40,
            "totales": {"citas": 40},
            "distribuciones": {},
            "alertas": [
                {
                    "nivel": "advertencia",
                    "mensaje": f"Notificación sensible del operador: {canario_alerta}.",
                }
            ],
        }

        contexto_seguro = filtrar_contexto_seguro(resumen)
        self.assertEqual(len(contexto_seguro["alertas"]), 0)
        self.assertNotIn(canario_alerta, json.dumps(contexto_seguro))

        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.PSICOLOGIA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario=None,
        )
        self.assertNotIn(canario_alerta, contents)

        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.PSICOLOGIA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=contexto_seguro,
            observacion_usuario=None,
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": Intencion.ALERTAS_Y_ANOMALIAS.value,
            "modulo": Modulo.PSICOLOGIA.value,
        }
        cliente_simulado = gemini_service.ClienteSimulado()
        informe = cliente_simulado.generar_informe(system_prompt, user_prompt, contexto)
        self.assertNotIn(canario_alerta, informe)

    def test_tarea01_4_2_4_conservacion_etiquetas_validas_y_metricas_legitimas(self) -> None:
        """Tarea 01.4.2 (4): Conservación de etiquetas válidas de dominios controlados y métricas numéricas legítimas."""
        resumen = {
            "modulo": "psicologia",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 100,
            "totales": {"citas": 60, "morbilidad": 40},
            "distribuciones": {
                "citas_por_estado": [
                    {"valor": "Atendida", "cantidad": 45, "porcentaje": 75.0},
                    {"valor": "Pendiente", "cantidad": 15, "porcentaje": 25.0},
                ],
                "morbilidad_por_tipo_consulta": [
                    {"valor": "Diagnóstico", "cantidad": 40, "porcentaje": 100.0},
                ],
            },
            "alertas": [
                {
                    "nivel": "advertencia",
                    "mensaje": "15 cita(s) en estado Pendiente sin atender.",
                },
                {
                    "nivel": "critico",
                    "mensaje": "El 20.0% de las citas terminó en 'No asistió'.",
                },
            ],
            "indicadores": {
                "citas_pendientes": 15,
                "citas_no_asistio": 12,
                "porcentaje_atendidas": 75.0,
            },
        }

        contexto_seguro = filtrar_contexto_seguro(resumen)

        # Distribuciones controladas presentes y completas
        citas_est = contexto_seguro["distribuciones"]["citas_por_estado"]
        self.assertEqual(len(citas_est), 2)
        self.assertEqual(citas_est[0]["valor"], "Atendida")
        self.assertEqual(citas_est[0]["cantidad"], 45)
        self.assertEqual(citas_est[1]["valor"], "Pendiente")
        self.assertEqual(citas_est[1]["cantidad"], 15)

        morb_tipo = contexto_seguro["distribuciones"]["morbilidad_por_tipo_consulta"]
        self.assertEqual(morb_tipo[0]["valor"], "Diagnóstico")
        self.assertEqual(morb_tipo[0]["cantidad"], 40)

        # Alertas legítimas vinculadas a plantillas presentes con sus métricas numéricas
        self.assertEqual(len(contexto_seguro["alertas"]), 2)
        self.assertEqual(contexto_seguro["alertas"][0]["mensaje"], "15 cita(s) en estado Pendiente sin atender.")
        self.assertEqual(contexto_seguro["alertas"][1]["mensaje"], "El 20.0% de las citas terminó en 'No asistió'.")

        # Verificación en contents enviado al SDK
        contents, _ = self._invocar_gemini_simulado(
            modulo=Modulo.PSICOLOGIA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=resumen,
            observacion_usuario=None,
        )
        self.assertIn("Atendida", contents)
        self.assertIn("Pendiente", contents)
        self.assertIn("Diagnóstico", contents)
        self.assertIn("15 cita(s) en estado Pendiente sin atender.", contents)
        self.assertIn("El 20.0% de las citas terminó en 'No asistió'.", contents)

        # Verificación en informe ClienteSimulado
        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.PSICOLOGIA,
            intencion=Intencion.ALERTAS_Y_ANOMALIAS,
            resumen=contexto_seguro,
            observacion_usuario=None,
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": Intencion.ALERTAS_Y_ANOMALIAS.value,
            "modulo": Modulo.PSICOLOGIA.value,
        }
        cliente_simulado = gemini_service.ClienteSimulado()
        informe = cliente_simulado.generar_informe(system_prompt, user_prompt, contexto)
        self.assertIn("Atendida", informe)
        self.assertIn("Pendiente", informe)
        self.assertIn("15 cita(s) en estado Pendiente sin atender.", informe)

    def test_tarea01_4_2_5_comportamiento_distribuciones_vacias_nulas_y_etiquetas_faltantes(self) -> None:
        """Tarea 01.4.2 (7): Comportamiento ante distribuciones vacías, valores nulos y etiquetas faltantes."""
        resumen = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 0,
            "totales": {"consultas": 0},
            "distribuciones": {
                "por_genero": [],
                "por_area": [
                    {"valor": None, "cantidad": 5, "porcentaje": 100.0},
                ],
                "por_grado": [
                    {"sin_clave_valor": "Rogue", "cantidad": 3},
                ],
            },
            "alertas": [],
        }

        contexto_seguro = filtrar_contexto_seguro(resumen)

        # por_genero vacía se conserva vacía de forma válida
        self.assertIn("por_genero", contexto_seguro["distribuciones"])
        self.assertEqual(contexto_seguro["distribuciones"]["por_genero"], [])

        # por_area con valor None no pertenece a AreaGeneral, se excluye sin error
        self.assertNotIn("por_area", contexto_seguro["distribuciones"])

        # por_grado con item mal formado (sin 'valor') se excluye sin excepción
        self.assertNotIn("por_grado", contexto_seguro["distribuciones"])

    def test_tarea01_4_2_6_compatibilidad_contrato_http_v1_y_reporte_response_dto(self) -> None:
        """Tarea 01.4.2 (8): Compatibilidad estricta con ReporteResponseDTO y contrato HTTP V1."""
        resumen = {
            "modulo": "medicina",
            "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
            "registros_procesados": 50,
            "totales": {"consultas": 50},
            "distribuciones": {
                "por_genero": [
                    {"valor": "Femenino", "cantidad": 30, "porcentaje": 60.0},
                    {"valor": "Masculino", "cantidad": 20, "porcentaje": 40.0},
                ]
            },
            "alertas": [
                {
                    "nivel": "critico",
                    "mensaje": "2 insumo(s) con fecha de vencimiento vencida.",
                }
            ],
        }

        contexto_seguro = filtrar_contexto_seguro(resumen)

        system_prompt, user_prompt = construir_prompts(
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            resumen=contexto_seguro,
            observacion_usuario=None,
        )
        contexto = {
            "resumen": contexto_seguro,
            "intencion": Intencion.RESUMEN_EJECUTIVO.value,
            "modulo": Modulo.MEDICINA.value,
        }
        cliente_simulado = gemini_service.ClienteSimulado()
        informe = cliente_simulado.generar_informe(system_prompt, user_prompt, contexto)

        respuesta = ReporteResponseDTO(
            exito=True,
            modulo=Modulo.MEDICINA,
            intencion=Intencion.RESUMEN_EJECUTIVO,
            informe_markdown=informe,
            meta=MetaDTO(
                registros_procesados=contexto_seguro["registros_procesados"],
                tiempo_procesamiento_seg=0.05,
                modo_informe=cliente_simulado.modo,
            ),
        )

        self.assertTrue(respuesta.exito)
        self.assertEqual(respuesta.modulo, Modulo.MEDICINA)
        self.assertEqual(respuesta.intencion, Intencion.RESUMEN_EJECUTIVO)
        self.assertEqual(respuesta.meta.modo_informe, "simulado")
        self.assertEqual(respuesta.meta.registros_procesados, 50)
        self.assertIn("Informe de Análisis Inteligente: Módulo Medicina", respuesta.informe_markdown)


if __name__ == "__main__":
    unittest.main()
