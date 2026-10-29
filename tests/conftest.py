try:
    import pytest
except ImportError:
    pytest = None  # type: ignore[assignment]

if pytest is not None:
    from app.core.config import obtener_ajustes
    from app.db import session

    CLAVE_TEST = "clave-b2b-de-prueba"

    @pytest.fixture(autouse=True)
    def _modo_simulado_determinista(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(obtener_ajustes(), "mock_llm", True)

    @pytest.fixture()
    def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
        ajustes = obtener_ajustes()
        monkeypatch.setattr(ajustes, "dirpoles_ia_api_key", CLAVE_TEST)
        return CLAVE_TEST

    @pytest.fixture()
    def cliente(api_key: str):
        from fastapi.testclient import TestClient

        from app.main import crear_app

        with TestClient(crear_app()) as cliente_prueba:
            cliente_prueba.headers.update({"X-API-Key": api_key})
            yield cliente_prueba

    @pytest.fixture()
    def bd_disponible() -> bool:
        try:
            return session.ping()
        except Exception:
            return False
