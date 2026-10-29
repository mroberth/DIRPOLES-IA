"""Implementación de la Base de Conocimiento respaldada por MariaDB (esquema dirpoles_knowledge).

Permite persistir dinámicamente:
- Roles y personalidades de agentes inteligentes.
- Catálogos cerrados (ej. PNF oficial de UPTAEB).
- Reglas lógicas de producción, hechos y conclusiones diagnósticas.
- Directrices institucionales y advertencias deontológicas.

Incluye degradación elegante a ConocimientoDirpoles4 si la base de datos
no se encuentra disponible o no tiene registros cargados (patrón Fallback).
"""

from typing import Any

from app.db.session import consultar
from app.knowledge.base import BaseConocimiento
from app.knowledge.dirpoles4.conocimiento import ConocimientoDirpoles4
from app.schemas.enums import Intencion, Modulo


class ConocimientoMariaDB(BaseConocimiento):
    """Base de conocimiento dinámica con persistencia física en MariaDB."""

    def __init__(self, sistema_id: str = "dirpoles4") -> None:
        self.sistema_id = sistema_id
        self._fallback = ConocimientoDirpoles4()
        self._roles_cache: dict[str, str] = {}
        self._pnf_cache: frozenset[str] | None = None
        self._dominios_cache: dict[str, frozenset[str]] | None = None
        self._cargar_desde_bd()

    def _cargar_desde_bd(self) -> None:
        """Carga en memoria los roles y catálogos de MariaDB si están disponibles."""
        try:
            sql_roles = (
                "SELECT dominio, nombre_rol FROM dirpoles_knowledge.conocimiento_roles_prompts "
                "WHERE sistema_id = :sistema_id AND activo = 1"
            )
            filas_roles = consultar(sql_roles, {"sistema_id": self.sistema_id})
            for f in filas_roles:
                dom = str(f.get("dominio", "")).strip().lower()
                rol = str(f.get("nombre_rol", "")).strip()
                if dom and rol:
                    self._roles_cache[dom] = rol

            sql_pnf = (
                "SELECT nombre_oficial FROM dirpoles_knowledge.conocimiento_catalogos_autorizados "
                "WHERE sistema_id = :sistema_id AND tipo_catalogo = 'pnf' AND activo = 1"
            )
            filas_pnf = consultar(sql_pnf, {"sistema_id": self.sistema_id})
            if filas_pnf:
                nombres = {str(f.get("nombre_oficial", "")).strip() for f in filas_pnf if f.get("nombre_oficial")}
                self._pnf_cache = frozenset(nombres)
        except Exception:
            # En caso de no poder conectar o tablas inexistentes, opera con fallback silencioso
            pass

    def obtener_rol(self, modulo: Any) -> str:
        """Obtiene el nombre del rol desde MariaDB o desde el fallback local."""
        clave_modulo = modulo.value if isinstance(modulo, Modulo) else str(modulo).lower()
        if clave_modulo in self._roles_cache:
            return self._roles_cache[clave_modulo]
        return self._fallback.obtener_rol(modulo)

    def obtener_enfoque(self, intencion: Any) -> str:
        """Retorna el enfoque analítico según la intención del reporte."""
        return self._fallback.obtener_enfoque(intencion)

    def obtener_dominios_distribuciones(self) -> dict[str, frozenset[str]]:
        """Retorna dominios de distribuciones, enriqueciendo con los PNF de MariaDB."""
        doms = dict(self._fallback.obtener_dominios_distribuciones())
        if self._pnf_cache:
            doms["por_pnf"] = self._pnf_cache
        return doms

    def es_alerta_autorizada(self, mensaje: str, nivel: str) -> bool:
        """Verifica si un mensaje de alerta se ajusta a las plantillas canónicas autorizadas."""
        return self._fallback.es_alerta_autorizada(mensaje, nivel)

    def resolver_directriz(self, texto: str | None) -> str:
        """Resuelve la directriz canónica autorizada para la observación del usuario."""
        return self._fallback.resolver_directriz(texto)
