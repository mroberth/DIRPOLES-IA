from typing import Any, Protocol, runtime_checkable


def formatear_plantilla(plantilla: str, valores: dict[str, Any], por_defecto: str) -> str:
    """Formatea una plantilla declarativa sin romper la ejecución si faltan claves.

    Las plantillas viven en la base de conocimiento (por ejemplo
    ``conocimiento_conclusiones.plantilla_mensaje``). Si una plantilla tiene un
    placeholder desconocido o está mal formada, se devuelve el texto por defecto
    del motor para no degradar el informe.
    """
    try:
        return plantilla.format(**valores)
    except (KeyError, IndexError, ValueError):
        return por_defecto


@runtime_checkable
class BaseConocimiento(Protocol):
    """Protocolo contractual para la base de conocimiento de un consumidor.

    Encapsula el conocimiento declarativo de dominio:
    - Roles institucionales, instrucciones y directrices de privacidad.
    - Catálogos oficiales y dominios controlados para distribuciones analíticas.
    - Umbrales de inferencia y plantillas de mensajes.
    - Expresiones regulares para validación de alertas canónicas estructuradas.
    - Directrices preaprobadas para instrucciones de usuario.
    """

    def obtener_rol(self, modulo: Any) -> str:
        """Retorna la descripción del rol especializado según el módulo analizado."""
        ...

    def obtener_instrucciones_sistema(self, modulo: Any) -> str:
        """Retorna las instrucciones de sistema declarativas para el módulo."""
        ...

    def obtener_directrices_privacidad(self, modulo: Any) -> str:
        """Retorna las directrices deontológicas y de privacidad del módulo."""
        ...

    def obtener_enfoque(self, intencion: Any) -> str:
        """Retorna el enfoque analítico según la intención del reporte."""
        ...

    def obtener_dominios_distribuciones(self) -> dict[str, frozenset[str]]:
        """Retorna el mapa de claves de distribución permitidas y sus dominios cerrados."""
        ...

    def obtener_catalogo(self, tipo_catalogo: str) -> frozenset[str]:
        """Retorna un catálogo institucional cerrado por tipo (pnf, area, estado_cita...)."""
        ...

    def obtener_umbral(self, codigo_hecho: str, por_defecto: float) -> float:
        """Retorna el umbral declarativo de un hecho observable."""
        ...

    def obtener_mensaje(self, codigo_conclusion: str, por_defecto: str, **valores: Any) -> str:
        """Retorna y formatea la plantilla declarativa de un mensaje o alerta."""
        ...

    def es_alerta_autorizada(self, mensaje: str, nivel: str) -> bool:
        """Verifica si un mensaje de alerta se ajusta a las plantillas canónicas autorizadas."""
        ...

    def resolver_directriz(self, texto: str | None) -> str:
        """Resuelve la directriz canónica autorizada para la observación del usuario."""
        ...

    def sanitizar_observacion(self, texto: str | None) -> str:
        """Aplica los filtros de PII en código antes de cualquier salida externa."""
        ...

    def evaluar_reglas(self, hechos: dict[str, float]) -> list[dict[str, str]]:
        """Evalúa las reglas de inferencia declarativas contra un mapa de hechos."""
        ...


__all__ = ["BaseConocimiento", "formatear_plantilla"]
