"""Base de Conocimiento respaldada por MariaDB (esquema ``dirpoles_knowledge``).

Esta implementación es la fuente de verdad declarativa del sistema:

- ``conocimiento_roles_prompts``: roles, instrucciones, enfoque y privacidad.
- ``conocimiento_catalogos_autorizados``: catálogos cerrados (PNF, estados, tipos).
- ``conocimiento_hechos_sintomas``: variables observables.
- ``conocimiento_conclusiones``: diagnósticos, alertas y plantillas de mensajes.
- ``conocimiento_reglas_inferencia`` + ``conocimiento_regla_hecho_pivote``: umbrales.
- ``conocimiento_enfoques_intencion``: enfoque analítico por intención.
- ``conocimiento_directrices``: directrices canónicas autorizadas.
- ``conocimiento_plantillas_alertas``: expresiones regulares de alertas válidas.

Si la base de datos no está disponible o una tabla no existe, cada consulta
registra el problema y degrada a ``ConocimientoDirpoles4`` (patrón fallback).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import consultar
from app.knowledge.base import BaseConocimiento, formatear_plantilla
from app.knowledge.dirpoles4.conocimiento import ConocimientoDirpoles4
from app.schemas.enums import Intencion, Modulo


@dataclass(frozen=True)
class RolConocimiento:
    nombre_rol: str
    instrucciones_sistema: str
    enfoque_por_defecto: str
    directrices_privacidad: str


@dataclass(frozen=True)
class ConclusionConocimiento:
    codigo: str
    dominio: str
    nivel: str
    titulo: str
    plantilla: str
    recomendacion: str


@dataclass(frozen=True)
class CondicionRegla:
    hecho_codigo: str
    operador: str
    valor_umbral: float
    operador_logico_siguiente: str
    orden: int


@dataclass
class ReglaConocimiento:
    codigo: str
    dominio: str
    nombre: str
    descripcion: str
    prioridad: int
    conclusion_codigo: str
    condiciones: list[CondicionRegla] = field(default_factory=list)


# Mapa declarativo de tipo de catálogo -> claves de distribución del motor.
# El motor conoce *cómo* se agrupan; la base de datos define *qué valores* son válidos.
_MAPA_CATALOGOS_A_DISTRIBUCIONES: dict[str, tuple[str, ...]] = {
    "pnf": ("por_pnf",),
    "genero": ("por_genero",),
    "area": ("por_area",),
    "submodulo": ("por_submodulo",),
    "tipo_consulta_psicologica": ("morbilidad_por_tipo_consulta",),
    "estado_cita": ("citas_por_estado",),
    "tipo_bien": ("por_tipo_bien",),
    "grado_discapacidad": ("por_grado",),
    "tipo_discapacidad": ("por_tipo",),
    "tipo_vehiculo": ("por_tipo",),
    "estado_referencia": ("por_estado",),
    "estado_jornada": ("por_estatus",),
    "estado_inventario": ("por_estatus",),
}

_LOGGER = logging.getLogger("dirpoles_ia.knowledge")


class ConocimientoMariaDB(BaseConocimiento):
    """Base de conocimiento dinámica con persistencia física en MariaDB."""

    def __init__(self, sistema_id: str = "dirpoles4") -> None:
        self.sistema_id = str(sistema_id).strip() or "dirpoles4"
        self._fallback = ConocimientoDirpoles4()
        self._roles: dict[str, RolConocimiento] = {}
        self._enfoques: dict[str, str] = {}
        self._catalogos: dict[str, frozenset[str]] = {}
        self._hechos: dict[str, dict[str, Any]] = {}
        self._conclusiones: dict[str, ConclusionConocimiento] = {}
        self._reglas: dict[str, ReglaConocimiento] = {}
        self._umbrales: dict[str, float] = {}
        self._plantillas_alerta: tuple[tuple[str, re.Pattern[str]], ...] = ()
        self._directrices: dict[str, str] = {}
        self._cargar_desde_bd()

    # ------------------------------------------------------------------
    # Carga declarativa desde MariaDB
    # ------------------------------------------------------------------
    def _consultar_seguro(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        try:
            return consultar(sql, params or {})
        except SQLAlchemyError as exc:
            _LOGGER.warning(
                "No se pudo cargar conocimiento declarativo de MariaDB para %s; "
                "se usará el fallback estático para este dato (%s).",
                self.sistema_id,
                type(exc).__name__,
            )
            return []

    def _cargar_desde_bd(self) -> None:
        self._cargar_roles()
        self._cargar_enfoques()
        self._cargar_catalogos()
        self._cargar_hechos()
        self._cargar_conclusiones()
        self._cargar_reglas()
        self._cargar_plantillas_alerta()
        self._cargar_directrices()

    def _cargar_roles(self) -> None:
        filas = self._consultar_seguro(
            "SELECT dominio, nombre_rol, instrucciones_sistema, enfoque_por_defecto, "
            "directrices_privacidad "
            "FROM dirpoles_knowledge.conocimiento_roles_prompts "
            "WHERE sistema_id = :sistema_id AND activo = 1",
            {"sistema_id": self.sistema_id},
        )
        for fila in filas:
            dominio = str(fila.get("dominio", "")).strip().lower()
            nombre_rol = str(fila.get("nombre_rol", "")).strip()
            if not dominio or not nombre_rol:
                continue
            self._roles[dominio] = RolConocimiento(
                nombre_rol=nombre_rol,
                instrucciones_sistema=str(fila.get("instrucciones_sistema", "")).strip(),
                enfoque_por_defecto=str(fila.get("enfoque_por_defecto", "")).strip(),
                directrices_privacidad=str(fila.get("directrices_privacidad", "")).strip(),
            )

    def _cargar_enfoques(self) -> None:
        filas = self._consultar_seguro(
            "SELECT intencion, enfoque FROM dirpoles_knowledge.conocimiento_enfoques_intencion "
            "WHERE sistema_id = :sistema_id AND activo = 1",
            {"sistema_id": self.sistema_id},
        )
        for fila in filas:
            intencion = str(fila.get("intencion", "")).strip().lower()
            enfoque = str(fila.get("enfoque", "")).strip()
            if intencion and enfoque:
                self._enfoques[intencion] = enfoque

    @staticmethod
    def _normalizar_catalogo(tipo_catalogo: str, nombre_oficial: str) -> str:
        valor = str(nombre_oficial).strip()
        if (
            str(tipo_catalogo).strip().lower() == "pnf"
            and valor
            and not valor.upper().startswith("PNF ")
        ):
            valor = f"PNF {valor}"
        return valor

    def _cargar_catalogos(self) -> None:
        filas = self._consultar_seguro(
            "SELECT tipo_catalogo, codigo, nombre_oficial "
            "FROM dirpoles_knowledge.conocimiento_catalogos_autorizados "
            "WHERE sistema_id = :sistema_id AND activo = 1",
            {"sistema_id": self.sistema_id},
        )
        agrupados: dict[str, set[str]] = {}
        for fila in filas:
            tipo = str(fila.get("tipo_catalogo", "")).strip().lower()
            valor = self._normalizar_catalogo(tipo, str(fila.get("nombre_oficial", "")))
            if tipo and valor:
                agrupados.setdefault(tipo, set()).add(valor)
        self._catalogos = {
            tipo: frozenset(valores) for tipo, valores in agrupados.items() if valores
        }

    def _cargar_hechos(self) -> None:
        filas = self._consultar_seguro(
            "SELECT codigo_hecho, dominio, nombre, tipo_dato, unidad_medida, descripcion "
            "FROM dirpoles_knowledge.conocimiento_hechos_sintomas "
            "WHERE sistema_id = :sistema_id AND activo = 1",
            {"sistema_id": self.sistema_id},
        )
        for fila in filas:
            codigo = str(fila.get("codigo_hecho", "")).strip()
            if codigo:
                self._hechos[codigo] = dict(fila)

    def _cargar_conclusiones(self) -> None:
        filas = self._consultar_seguro(
            "SELECT codigo_conclusion, dominio, nivel_severidad, titulo_diagnostico, "
            "plantilla_mensaje, recomendacion_sugerida "
            "FROM dirpoles_knowledge.conocimiento_conclusiones "
            "WHERE sistema_id = :sistema_id AND activo = 1",
            {"sistema_id": self.sistema_id},
        )
        for fila in filas:
            codigo = str(fila.get("codigo_conclusion", "")).strip()
            if not codigo:
                continue
            self._conclusiones[codigo] = ConclusionConocimiento(
                codigo=codigo,
                dominio=str(fila.get("dominio", "")).strip().lower(),
                nivel=str(fila.get("nivel_severidad", "info")).strip().lower(),
                titulo=str(fila.get("titulo_diagnostico", "")).strip(),
                plantilla=str(fila.get("plantilla_mensaje", "")).strip(),
                recomendacion=str(fila.get("recomendacion_sugerida", "")).strip(),
            )

    def _cargar_reglas(self) -> None:
        filas = self._consultar_seguro(
            "SELECT r.codigo_regla, r.dominio, r.nombre_regla, r.descripcion_logica, "
            "r.prioridad, c.codigo_conclusion, h.codigo_hecho, p.operador_comparacion, "
            "p.valor_umbral, p.operador_logico_siguiente, p.orden "
            "FROM dirpoles_knowledge.conocimiento_reglas_inferencia r "
            "JOIN dirpoles_knowledge.conocimiento_conclusiones c "
            "ON c.id = r.conclusion_id AND c.sistema_id = r.sistema_id AND c.activo = 1 "
            "JOIN dirpoles_knowledge.conocimiento_regla_hecho_pivote p ON p.regla_id = r.id "
            "JOIN dirpoles_knowledge.conocimiento_hechos_sintomas h "
            "ON h.id = p.hecho_id AND h.sistema_id = r.sistema_id AND h.activo = 1 "
            "WHERE r.sistema_id = :sistema_id AND r.activa = 1 "
            "ORDER BY r.prioridad DESC, p.orden ASC",
            {"sistema_id": self.sistema_id},
        )
        for fila in filas:
            codigo = str(fila.get("codigo_regla", "")).strip()
            if not codigo:
                continue
            regla = self._reglas.get(codigo)
            if regla is None:
                regla = ReglaConocimiento(
                    codigo=codigo,
                    dominio=str(fila.get("dominio", "")).strip().lower(),
                    nombre=str(fila.get("nombre_regla", "")).strip(),
                    descripcion=str(fila.get("descripcion_logica", "")).strip(),
                    prioridad=int(fila.get("prioridad", 1) or 1),
                    conclusion_codigo=str(fila.get("codigo_conclusion", "")).strip(),
                )
                self._reglas[codigo] = regla
            condicion = CondicionRegla(
                hecho_codigo=str(fila.get("codigo_hecho", "")).strip(),
                operador=str(fila.get("operador_comparacion", "<")).strip(),
                valor_umbral=float(fila.get("valor_umbral", 0) or 0),
                operador_logico_siguiente=str(fila.get("operador_logico_siguiente", "FIN")).strip(),
                orden=int(fila.get("orden", 1) or 1),
            )
            if condicion.hecho_codigo:
                regla.condiciones.append(condicion)
                # El primer umbral (mayor prioridad) es el que usa el motor ETL.
                self._umbrales.setdefault(condicion.hecho_codigo, condicion.valor_umbral)

    def _cargar_plantillas_alerta(self) -> None:
        filas = self._consultar_seguro(
            "SELECT nivel, patron_regex FROM dirpoles_knowledge.conocimiento_plantillas_alertas "
            "WHERE sistema_id = :sistema_id AND activo = 1",
            {"sistema_id": self.sistema_id},
        )
        plantillas: list[tuple[str, re.Pattern[str]]] = []
        for fila in filas:
            nivel = str(fila.get("nivel", "")).strip().lower()
            patron = str(fila.get("patron_regex", "")).strip()
            if not nivel or not patron:
                continue
            try:
                plantillas.append((nivel, re.compile(patron)))
            except re.error as exc:
                _LOGGER.warning(
                    "Se ignoró una plantilla regex inválida del conocimiento %s (%s).",
                    self.sistema_id,
                    type(exc).__name__,
                )
                continue
        self._plantillas_alerta = tuple(plantillas)

    def _cargar_directrices(self) -> None:
        filas = self._consultar_seguro(
            "SELECT clave, directriz FROM dirpoles_knowledge.conocimiento_directrices "
            "WHERE sistema_id = :sistema_id AND activo = 1",
            {"sistema_id": self.sistema_id},
        )
        for fila in filas:
            clave = str(fila.get("clave", "")).strip()
            directriz = str(fila.get("directriz", "")).strip()
            if clave and directriz:
                self._directrices[clave] = directriz

    # ------------------------------------------------------------------
    # Contrato BaseConocimiento
    # ------------------------------------------------------------------
    @staticmethod
    def _clave_modulo(modulo: Any) -> str:
        return modulo.value if isinstance(modulo, Modulo) else str(modulo).lower()

    @staticmethod
    def _clave_intencion(intencion: Any) -> str:
        return intencion.value if isinstance(intencion, Intencion) else str(intencion).lower()

    def obtener_rol(self, modulo: Any) -> str:
        clave = self._clave_modulo(modulo)
        rol = self._roles.get(clave)
        if rol is not None:
            return rol.nombre_rol
        return self._fallback.obtener_rol(modulo)

    def obtener_instrucciones_sistema(self, modulo: Any) -> str:
        clave = self._clave_modulo(modulo)
        rol = self._roles.get(clave)
        if rol is not None and rol.instrucciones_sistema:
            return rol.instrucciones_sistema
        return self._fallback.obtener_instrucciones_sistema(modulo)

    def obtener_directrices_privacidad(self, modulo: Any) -> str:
        clave = self._clave_modulo(modulo)
        rol = self._roles.get(clave)
        if rol is not None and rol.directrices_privacidad:
            return rol.directrices_privacidad
        return self._fallback.obtener_directrices_privacidad(modulo)

    def obtener_enfoque(self, intencion: Any) -> str:
        clave = self._clave_intencion(intencion)
        if clave in self._enfoques:
            return self._enfoques[clave]
        return self._fallback.obtener_enfoque(intencion)

    def obtener_dominios_distribuciones(self) -> dict[str, frozenset[str]]:
        """Usa los catálogos configurados en BD y el fallback para los ausentes.

        Cuando la BD define un catálogo, este reemplaza el dominio correspondiente;
        así sus altas y bajas se aplican sin despliegue. Los dominios no configurados
        conservan el fallback estático.
        """
        dominios: dict[str, set[str]] = {
            clave: set(valores)
            for clave, valores in self._fallback.obtener_dominios_distribuciones().items()
        }
        tipos_por_distribucion: dict[str, list[str]] = {}
        for tipo_catalogo, distribuciones in _MAPA_CATALOGOS_A_DISTRIBUCIONES.items():
            for clave_dist in distribuciones:
                tipos_por_distribucion.setdefault(clave_dist, []).append(tipo_catalogo)

        for clave_dist, tipos_catalogo in tipos_por_distribucion.items():
            tipos_configurados = [tipo for tipo in tipos_catalogo if tipo in self._catalogos]
            if tipos_configurados:
                dominios[clave_dist] = set().union(
                    *(self._catalogos[tipo] for tipo in tipos_configurados)
                )
        return {clave: frozenset(valores) for clave, valores in dominios.items()}

    def obtener_catalogo(self, tipo_catalogo: str) -> frozenset[str]:
        tipo = str(tipo_catalogo).strip().lower()
        if tipo in self._catalogos:
            return self._catalogos[tipo]
        return self._fallback.obtener_catalogo(tipo)

    def obtener_umbral(self, codigo_hecho: str, por_defecto: float) -> float:
        codigo = str(codigo_hecho).strip()
        if codigo in self._umbrales:
            return float(self._umbrales[codigo])
        return self._fallback.obtener_umbral(codigo, por_defecto)

    def obtener_mensaje(self, codigo_conclusion: str, por_defecto: str, **valores: Any) -> str:
        codigo = str(codigo_conclusion).strip()
        conclusion = self._conclusiones.get(codigo)
        if conclusion is not None and conclusion.plantilla:
            return formatear_plantilla(conclusion.plantilla, valores, por_defecto)
        return self._fallback.obtener_mensaje(codigo, por_defecto, **valores)

    def es_alerta_autorizada(self, mensaje: str, nivel: str) -> bool:
        msg = mensaje.strip()
        niv = nivel.strip().lower()
        for nivel_esperado, patron in self._plantillas_alerta:
            if niv == nivel_esperado and patron.match(msg):
                return True
        return self._fallback.es_alerta_autorizada(mensaje, nivel)

    def resolver_directriz(self, texto: str | None) -> str:
        if not texto:
            return "Ninguna indicación adicional."
        clave = texto.strip()
        if clave in self._directrices:
            return self._directrices[clave]
        return self._fallback.resolver_directriz(texto)

    def sanitizar_observacion(self, texto: str | None) -> str:
        # El filtro de PII es procedimental y vive en código, no en la BD.
        return self._fallback.sanitizar_observacion(texto)

    # ------------------------------------------------------------------
    # Motor de inferencia declarativo
    # ------------------------------------------------------------------
    @staticmethod
    def _comparar(valor: float | None, condicion: CondicionRegla) -> bool:
        if valor is None:
            return False
        umbral = condicion.valor_umbral
        operador = condicion.operador
        if operador == "<":
            return valor < umbral
        if operador == "<=":
            return valor <= umbral
        if operador == ">":
            return valor > umbral
        if operador == ">=":
            return valor >= umbral
        if operador == "==":
            return valor == umbral
        if operador == "!=":
            return valor != umbral
        return False

    @classmethod
    def _evaluar_condiciones(
        cls, condiciones: list[CondicionRegla], hechos: dict[str, float]
    ) -> bool:
        """Evalúa condiciones con lógica AND/OR secuencial (sin paréntesis)."""
        if not condiciones:
            return False
        grupos: list[list[CondicionRegla]] = []
        actual: list[CondicionRegla] = []
        for condicion in condiciones:
            actual.append(condicion)
            if condicion.operador_logico_siguiente in {"OR", "FIN"}:
                grupos.append(actual)
                actual = []
        if actual:
            grupos.append(actual)
        for grupo in grupos:
            if all(
                cls._comparar(hechos.get(condicion.hecho_codigo), condicion) for condicion in grupo
            ):
                return True
        return False

    def evaluar_reglas(self, hechos: dict[str, float]) -> list[dict[str, str]]:
        """Evalúa las reglas activas y devuelve alertas con su conclusión."""
        resultados: list[dict[str, str]] = []
        for regla in sorted(self._reglas.values(), key=lambda r: r.prioridad, reverse=True):
            if not self._evaluar_condiciones(regla.condiciones, hechos):
                continue
            conclusion = self._conclusiones.get(regla.conclusion_codigo)
            if conclusion is None:
                continue
            primera = regla.condiciones[0] if regla.condiciones else None
            valores: dict[str, Any] = dict(hechos)
            if primera is not None:
                valores["umbral"] = primera.valor_umbral
                valores["valor"] = hechos.get(primera.hecho_codigo, 0)
                valores["cantidad"] = valores["valor"]
            mensaje = formatear_plantilla(conclusion.plantilla, valores, conclusion.plantilla)
            resultados.append(
                {
                    "nivel": conclusion.nivel,
                    "mensaje": mensaje,
                    "codigo_regla": regla.codigo,
                    "codigo_conclusion": conclusion.codigo,
                }
            )
        return resultados
