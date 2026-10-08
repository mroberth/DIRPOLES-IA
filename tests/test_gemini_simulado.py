import pytest
from app.core.config import obtener_ajustes
from app.schemas.enums import Intencion, Modulo
from app.services import gemini_service, prompt_service


def _contexto() -> dict[str, object]:
    resumen = {
        "modulo": "medicina",
        "periodo": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-09-30"},
        "totales": {"consultas": 450, "insumos": 30},
        "distribuciones": {
            "por_genero": [
                {"valor": "Femenino", "cantidad": 260, "porcentaje": 57.8},
                {"valor": "Masculino", "cantidad": 190, "porcentaje": 42.2},
            ]
        },
        "indicadores": {"insumos": {"vencidos": 2, "por_vencer_30_dias": 5}},
        "alertas": [
            {"nivel": "critico", "mensaje": "2 insumos vencidos."},
            {"nivel": "advertencia", "mensaje": "5 insumos por vencer."},
        ],
        "registros_procesados": 480,
    }
    return {
        "resumen": resumen,
        "intencion": Intencion.ALERTAS_Y_ANOMALIAS.value,
        "modulo": Modulo.MEDICINA.value,
    }


def test_simulado_genera_las_tres_secciones() -> None:
    cliente = gemini_service.ClienteSimulado()
    informe = cliente.generar_informe("sys", "user", _contexto())
    assert "#### 1. Resumen Ejecutivo" in informe
    assert "#### 2. Hallazgos Clave y Puntos Críticos" in informe
    assert "#### 3. Recomendaciones Operativas" in informe


def test_simulado_incorpora_cifras_y_alertas() -> None:
    cliente = gemini_service.ClienteSimulado()
    informe = cliente.generar_informe("sys", "user", _contexto())
    assert "**450**" in informe or "450" in informe
    assert "2 insumos vencidos." in informe
    assert "57.8%" in informe
    assert "modo simulado" in informe


def test_simulado_sin_alertas_mensaje_adecuado() -> None:
    contexto = _contexto()
    contexto["resumen"]["alertas"] = []  # type: ignore[index]
    informe = gemini_service.ClienteSimulado().generar_informe("sys", "user", contexto)
    assert "No se detectaron anomalías críticas" in informe
    assert "Mantener el ritmo operativo actual" in informe


def test_obtener_cliente_devuelve_simulado_sin_key(monkeypatch: pytest.MonkeyPatch) -> None:
    ajustes = obtener_ajustes()
    monkeypatch.setattr(ajustes, "mock_llm", True)
    monkeypatch.setattr(ajustes, "gemini_api_key", "")
    assert gemini_service.obtener_cliente().modo == "simulado"


def test_obtener_cliente_devuelve_gemini_con_key(monkeypatch: pytest.MonkeyPatch) -> None:
    ajustes = obtener_ajustes()
    monkeypatch.setattr(ajustes, "mock_llm", False)
    monkeypatch.setattr(ajustes, "gemini_api_key", "AIzaSimuladaParaPrueba")
    cliente = gemini_service.obtener_cliente()
    assert cliente.modo == "gemini"


def test_flujo_completo_prompt_simulado() -> None:
    contexto = _contexto()
    system, user = prompt_service.construir_prompts(
        modulo=Modulo.MEDICINA,
        intencion=Intencion.ALERTAS_Y_ANOMALIAS,
        resumen=contexto["resumen"],  # type: ignore[arg-type]
        observacion_usuario=None,
    )
    informe = gemini_service.ClienteSimulado().generar_informe(system, user, contexto)
    assert informe.startswith("### 📊 Informe de Análisis Inteligente: Módulo Medicina")
