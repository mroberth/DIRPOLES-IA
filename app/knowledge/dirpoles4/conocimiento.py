from typing import Any

from app.knowledge.base import BaseConocimiento, formatear_plantilla
from app.knowledge.dirpoles4.alertas import (
    PLANTILLAS_ALERTAS_AUTORIZADAS,
    es_alerta_autorizada,
)
from app.knowledge.dirpoles4.catalogos import (
    CAMPOS_PERMITIDOS_LLM,
    CATALOGO_PNF_OFICIAL,
    DISTRIBUCIONES_PERMITIDAS_LLM,
    DOMINIOS_DISTRIBUCIONES,
    ESTADOS_JORNADA_VALIDOS,
)
from app.knowledge.dirpoles4.directrices import (
    DIRECTRICES_CANONICAS,
    resolver_observacion_para_prompt,
    sanitizar_observacion_usuario,
)
from app.knowledge.dirpoles4.parametros import (
    MENSAJES_POR_DEFECTO,
    UMBRALES_POR_DEFECTO,
)
from app.knowledge.dirpoles4.roles import (
    DIRECTRICES_PRIVACIDAD_POR_MODULO,
    ENFOQUE_POR_INTENCION,
    INSTRUCCIONES_POR_MODULO,
    ROLES_POR_MODULO,
)
from app.schemas.enums import Intencion, Modulo


class ConocimientoDirpoles4(BaseConocimiento):
    """Implementación de la Base de Conocimiento institucional para DIRPOLES-4 (UPTAEB).

    Centraliza las definiciones analíticas, roles de bienestar estudiantil,
    catálogos de PNF y reglas de validación canónica de alertas.

    Esta implementación es el *fallback* determinista del sistema. La fuente de
    verdad en producción es ``ConocimientoMariaDB`` (esquema
    ``dirpoles_knowledge``); este objeto garantiza la operación si la base de
    datos no está disponible.
    """

    def __init__(self) -> None:
        self.roles: dict[Modulo, str] = ROLES_POR_MODULO
        self.instrucciones: dict[Modulo, str] = INSTRUCCIONES_POR_MODULO
        self.directrices_privacidad: dict[Modulo, str] = DIRECTRICES_PRIVACIDAD_POR_MODULO
        self.enfoques: dict[Intencion, str] = ENFOQUE_POR_INTENCION
        self.dominios: dict[str, frozenset[str]] = DOMINIOS_DISTRIBUCIONES
        self.catalogo_pnf: frozenset[str] = CATALOGO_PNF_OFICIAL
        self.distribuciones_permitidas: frozenset[str] = DISTRIBUCIONES_PERMITIDAS_LLM
        self.estados_jornada_validos: frozenset[str] = ESTADOS_JORNADA_VALIDOS
        self.campos_permitidos: frozenset[str] = CAMPOS_PERMITIDOS_LLM
        self.plantillas_alertas = PLANTILLAS_ALERTAS_AUTORIZADAS
        self.directrices_canonicas = DIRECTRICES_CANONICAS
        self.umbrales: dict[str, float] = UMBRALES_POR_DEFECTO
        self.mensajes: dict[str, str] = MENSAJES_POR_DEFECTO

    @staticmethod
    def _clave_modulo(modulo: Any) -> str:
        return modulo.value if isinstance(modulo, Modulo) else str(modulo).lower()

    @staticmethod
    def _clave_intencion(intencion: Any) -> str:
        return intencion.value if isinstance(intencion, Intencion) else str(intencion).lower()

    def obtener_rol(self, modulo: Any) -> str:
        clave = self._clave_modulo(modulo)
        for m, rol in self.roles.items():
            if m.value == clave:
                return rol
        return "Analista Institucional"

    def obtener_instrucciones_sistema(self, modulo: Any) -> str:
        clave = self._clave_modulo(modulo)
        for m, texto in self.instrucciones.items():
            if m.value == clave:
                return texto
        return ""

    def obtener_directrices_privacidad(self, modulo: Any) -> str:
        clave = self._clave_modulo(modulo)
        for m, texto in self.directrices_privacidad.items():
            if m.value == clave:
                return texto
        return ""

    def obtener_enfoque(self, intencion: Any) -> str:
        clave = self._clave_intencion(intencion)
        for i, enfoque in self.enfoques.items():
            if i.value == clave:
                return enfoque
        return "Prioriza una visión panorámica."

    def obtener_dominios_distribuciones(self) -> dict[str, frozenset[str]]:
        return self.dominios

    def obtener_catalogo(self, tipo_catalogo: str) -> frozenset[str]:
        tipo = str(tipo_catalogo).strip().lower()
        if tipo == "pnf":
            return self.catalogo_pnf
        if tipo == "area":
            return self.dominios["por_area"]
        if tipo == "estado_jornada":
            return self.estados_jornada_validos
        return frozenset()

    def obtener_umbral(self, codigo_hecho: str, por_defecto: float) -> float:
        return float(self.umbrales.get(str(codigo_hecho).strip(), por_defecto))

    def obtener_mensaje(self, codigo_conclusion: str, por_defecto: str, **valores: Any) -> str:
        plantilla = self.mensajes.get(str(codigo_conclusion).strip(), por_defecto)
        return formatear_plantilla(plantilla, valores, por_defecto)

    def es_alerta_autorizada(self, mensaje: str, nivel: str) -> bool:
        return es_alerta_autorizada(mensaje, nivel)

    def resolver_directriz(self, texto: str | None) -> str:
        return resolver_observacion_para_prompt(texto)

    def sanitizar_observacion(self, texto: str | None) -> str:
        return sanitizar_observacion_usuario(texto)

    def evaluar_reglas(self, hechos: dict[str, float]) -> list[dict[str, str]]:
        """El fallback estático no evalúa reglas: el ETL aplica sus umbrales locales."""
        return []
