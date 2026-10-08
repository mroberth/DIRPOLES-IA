from app.schemas.enums import Intencion, Modulo
from app.services import prompt_service


def test_roles_cubren_los_10_modulos() -> None:
    assert set(prompt_service.ROLES_POR_MODULO) == set(Modulo)


def test_intenciones_cubren_el_catalogo() -> None:
    assert set(prompt_service.ENFOQUE_POR_INTENCION) == set(Intencion)


def test_system_prompt_contiene_rol_y_regla_de_exclusividad() -> None:
    prompt = prompt_service.construir_system_prompt(Modulo.MEDICINA)
    assert "Especialista en gestión de servicios médicos universitarios" in prompt
    assert "EXCLUSIVAMENTE" in prompt
    assert "Markdown" in prompt


def test_user_prompt_estructura_completa() -> None:
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
    assert "Módulo Analizado: medicina" in user
    assert "Intención del Informe: alertas_y_anomalias" in user
    assert "2026-01-01 a 2026-09-30" in user
    assert "Enfocarse en insumos con bajo stock." in user
    assert "Resumen Ejecutivo" in user
    assert "Hallazgos Clave y Puntos Críticos" in user
    assert "Recomendaciones Operativas" in user
    assert '"consultas": 450' in user
    assert system.startswith("Eres un ")


def test_user_prompt_sin_observacion_usa_por_defecto() -> None:
    _, user = prompt_service.construir_prompts(
        modulo=Modulo.GENERAL,
        intencion=Intencion.RESUMEN_EJECUTIVO,
        resumen={"periodo": {}},
        observacion_usuario=None,
    )
    assert "Ninguna indicación adicional." in user
    assert "inicio de los registros a la fecha actual" in user
