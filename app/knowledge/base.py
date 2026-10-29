import re
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BaseConocimiento(Protocol):
    """Protocolo contractual para la base de conocimiento de un consumidor.

    Encapsula el conocimiento declarativo de dominio:
    - Roles institucionales y propósitos analíticos.
    - Catálogos oficiales y dominios controlados para distribuciones analíticas.
    - Expresiones regulares para validación de alertas canónicas estructuradas.
    - Directrices preaprobadas para instrucciones de usuario.
    """

    def obtener_rol(self, modulo: Any) -> str:
        """Retorna la descripción del rol especializado según el módulo analizado."""
        ...

    def obtener_enfoque(self, intencion: Any) -> str:
        """Retorna el enfoque analítico según la intención del reporte."""
        ...

    def obtener_dominios_distribuciones(self) -> dict[str, frozenset[str]]:
        """Retorna el mapa de claves de distribución permitidas y sus dominios cerrados."""
        ...

    def es_alerta_autorizada(self, mensaje: str, nivel: str) -> bool:
        """Verifica si un mensaje de alerta se ajusta a las plantillas canónicas autorizadas."""
        ...

    def resolver_directriz(self, texto: str | None) -> str:
        """Resuelve la directriz canónica autorizada para la observación del usuario."""
        ...
