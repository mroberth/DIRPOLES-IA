import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.bd


def test_generar_reporte_medicina_end_to_end(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/api/v1/reportes/generar",
        json={
            "modulo": "medicina",
            "intencion": "alertas_y_anomalias",
            "filtros": {"fecha_inicio": "2020-01-01", "fecha_fin": "2030-12-31"},
            "observacion_usuario": "Enfocarse en insumos con bajo stock.",
        },
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["exito"] is True
    assert cuerpo["modulo"] == "medicina"
    assert cuerpo["intencion"] == "alertas_y_anomalias"
    assert "Resumen Ejecutivo" in cuerpo["informe_markdown"]
    assert cuerpo["meta"]["registros_procesados"] >= 0
    assert cuerpo["meta"]["modo_informe"] in {"simulado", "gemini", "simulado_fallback"}
    assert cuerpo["meta"]["tiempo_procesamiento_seg"] >= 0


@pytest.mark.parametrize(
    "modulo",
    [
        "general",
        "medicina",
        "psicologia",
        "orientacion",
        "trabajo_social",
        "discapacidad",
        "referencias",
        "jornadas",
        "mobiliario",
        "transporte",
    ],
)
def test_generar_los_10_modulos(cliente: TestClient, modulo: str) -> None:
    respuesta = cliente.post(
        "/api/v1/reportes/generar",
        json={
            "modulo": modulo,
            "intencion": "resumen_ejecutivo",
            "filtros": {"fecha_inicio": "2020-01-01", "fecha_fin": "2030-12-31"},
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["exito"] is True


def test_generar_con_filtros_avanzados(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/api/v1/reportes/generar",
        json={
            "modulo": "transporte",
            "intencion": "recomendaciones",
            "filtros": {"seccion_transporte": "Repuestos", "estado": "Disponible"},
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["exito"] is True
