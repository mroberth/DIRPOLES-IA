from fastapi.testclient import TestClient


def test_salud_sin_api_key(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/v1/salud")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["servicio"] == "DIRPOLES-IA"


def test_generar_sin_api_key_devuelve_401(cliente: TestClient) -> None:
    cliente.headers.pop("X-API-Key")
    respuesta = cliente.post(
        "/api/v1/reportes/generar",
        json={"modulo": "medicina", "intencion": "resumen_ejecutivo", "filtros": {}},
    )
    assert respuesta.status_code == 401


def test_generar_con_api_key_incorrecta_devuelve_401(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/api/v1/reportes/generar",
        headers={"X-API-Key": "clave-erronea"},
        json={"modulo": "medicina", "intencion": "resumen_ejecutivo", "filtros": {}},
    )
    assert respuesta.status_code == 401


def test_catalogos(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/v1/reportes/catalogos")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "medicina" in cuerpo["modulos"]
    assert "alertas_y_anomalias" in cuerpo["intenciones"]
    assert len(cuerpo["modulos"]) == 10
    assert len(cuerpo["intenciones"]) == 4
