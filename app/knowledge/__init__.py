from app.knowledge.base import BaseConocimiento
from app.knowledge.dirpoles4 import ConocimientoDirpoles4

_CONOCIMIENTO_POR_DEFECTO: BaseConocimiento = ConocimientoDirpoles4()


def obtener_conocimiento_por_defecto() -> BaseConocimiento:
    """Retorna la base de conocimiento activa por defecto (DIRPOLES-4)."""
    return _CONOCIMIENTO_POR_DEFECTO


__all__ = [
    "BaseConocimiento",
    "ConocimientoDirpoles4",
    "obtener_conocimiento_por_defecto",
]
