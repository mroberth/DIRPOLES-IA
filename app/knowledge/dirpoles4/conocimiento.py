from typing import Any

from app.knowledge.base import BaseConocimiento
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
from app.knowledge.dirpoles4.roles import ENFOQUE_POR_INTENCION, ROLES_POR_MODULO
from app.schemas.enums import Intencion, Modulo


class ConocimientoDirpoles4(BaseConocimiento):
    """Implementación de la Base de Conocimiento institucional para DIRPOLES-4 (UPTAEB).

    Centraliza las definiciones analíticas, roles de bienestar estudiantil,
    catálogos de PNF y reglas de validación canónica de alertas.
    """

    def __init__(self) -> None:
        self.roles: dict[Modulo, str] = ROLES_POR_MODULO
        self.enfoques: dict[Intencion, str] = ENFOQUE_POR_INTENCION
        self.dominios: dict[str, frozenset[str]] = DOMINIOS_DISTRIBUCIONES
        self.catalogo_pnf: frozenset[str] = CATALOGO_PNF_OFICIAL
        self.distribuciones_permitidas: frozenset[str] = DISTRIBUCIONES_PERMITIDAS_LLM
        self.estados_jornada_validos: frozenset[str] = ESTADOS_JORNADA_VALIDOS
        self.campos_permitidos: frozenset[str] = CAMPOS_PERMITIDOS_LLM
        self.plantillas_alertas = PLANTILLAS_ALERTAS_AUTORIZADAS
        self.directrices_canonicas = DIRECTRICES_CANONICAS

    def obtener_rol(self, modulo: Any) -> str:
        if isinstance(modulo, Modulo):
            return self.roles.get(modulo, "Analista Institucional")
        for m, rol in self.roles.items():
            if m.value == str(modulo):
                return rol
        return "Analista Institucional"

    def obtener_enfoque(self, intencion: Any) -> str:
        if isinstance(intencion, Intencion):
            return self.enfoques.get(intencion, "Prioriza una visión panorámica.")
        for i, enf in self.enfoques.items():
            if i.value == str(intencion):
                return enf
        return "Prioriza una visión panorámica."

    def obtener_dominios_distribuciones(self) -> dict[str, frozenset[str]]:
        return self.dominios

    def es_alerta_autorizada(self, mensaje: str, nivel: str) -> bool:
        return es_alerta_autorizada(mensaje, nivel)

    def resolver_directriz(self, texto: str | None) -> str:
        return resolver_observacion_para_prompt(texto)

    def sanitizar_observacion(self, texto: str | None) -> str:
        return sanitizar_observacion_usuario(texto)
