import logging
import os

from app.knowledge.base import BaseConocimiento
from app.knowledge.dirpoles4 import ConocimientoDirpoles4

# Caché por tenant para no consultar MariaDB en cada petición.
_CACHE_CONOCIMIENTO: dict[tuple[str, str], BaseConocimiento] = {}
_LOGGER = logging.getLogger("dirpoles_ia.knowledge")


def _backend_activo() -> str:
    return os.getenv("KNOWLEDGE_BACKEND", "mariadb").strip().lower()


def obtener_conocimiento(conocimiento_id: str | None = None) -> BaseConocimiento:
    """Retorna la base de conocimiento del tenant solicitado.

    - ``KNOWLEDGE_BACKEND=mariadb`` (por defecto): usa ``dirpoles_knowledge``.
    - ``KNOWLEDGE_BACKEND=static``: usa el fallback en archivos Python.

    Si MariaDB no está disponible, ``ConocimientoMariaDB`` degrada internamente
    a ``ConocimientoDirpoles4`` sin romper la petición.
    """
    clave = str(conocimiento_id or "dirpoles4").strip() or "dirpoles4"
    backend = _backend_activo()
    if backend in {"db", "database"}:
        backend = "mariadb"
    if backend not in {"mariadb", "static"}:
        raise ValueError(f"KNOWLEDGE_BACKEND no soportado: {backend}")

    clave_cache = (backend, clave)
    if clave_cache in _CACHE_CONOCIMIENTO:
        return _CACHE_CONOCIMIENTO[clave_cache]

    if backend == "mariadb":
        from app.knowledge.mariadb import ConocimientoMariaDB

        kb: BaseConocimiento = ConocimientoMariaDB(sistema_id=clave)
    else:
        kb = ConocimientoDirpoles4()

    _CACHE_CONOCIMIENTO[clave_cache] = kb
    return kb


def obtener_conocimiento_por_defecto() -> BaseConocimiento:
    """Retorna la base de conocimiento activa del tenant institucional."""
    return obtener_conocimiento("dirpoles4")


def restablecer_conocimiento() -> None:
    """Limpia la caché de conocimiento (útil en pruebas y recargas de configuración)."""
    _CACHE_CONOCIMIENTO.clear()


__all__ = [
    "BaseConocimiento",
    "ConocimientoDirpoles4",
    "obtener_conocimiento",
    "obtener_conocimiento_por_defecto",
    "restablecer_conocimiento",
]
