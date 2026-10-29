from dataclasses import dataclass
from functools import lru_cache
import hmac
import json
import os
from typing import Any

from app.core.config import obtener_ajustes


@dataclass(frozen=True)
class PerfilConsumidor:
    """Perfil de configuración y permisos de un sistema consumidor autorizado."""

    id: str
    nombre: str
    api_key: str
    modo_acceso: str = "push"  # "sql_pull" o "push"
    conocimiento_id: str = "dirpoles4"
    adaptador_id: str = "en_memoria"
    activo: bool = True

    def __str__(self) -> str:
        return self.api_key


class RegistroConsumidores:
    """Registro y autenticador multitenant de sistemas consumidores B2B."""

    def __init__(self) -> None:
        self._consumidores: dict[str, PerfilConsumidor] = {}

    def registrar(self, perfil: PerfilConsumidor) -> None:
        """Registra o actualiza un perfil de consumidor en memoria."""
        self._consumidores[perfil.id] = perfil

    def obtener_por_id(self, consumidor_id: str) -> PerfilConsumidor | None:
        if consumidor_id in self._consumidores:
            return self._consumidores[consumidor_id]
        if consumidor_id == "dirpoles4":
            clave_actual = obtener_ajustes().dirpoles_ia_api_key
            return PerfilConsumidor(
                id="dirpoles4",
                nombre="DIRPOLES-4 Monolito Institucional (UPTAEB)",
                api_key=clave_actual,
                modo_acceso="sql_pull",
                conocimiento_id="dirpoles4",
                adaptador_id="dirpoles4_sql",
            )
        return None

    def listar_activos(self) -> list[PerfilConsumidor]:
        return [c for c in self._consumidores.values() if c.activo]

    def autenticar(self, api_key: str | None) -> PerfilConsumidor | None:
        """Autentica la API Key comparando en tiempo constante (timing-safe).

        Verifica los consumidores registrados y la clave activa de DIRPOLES-4.
        """
        if not api_key:
            return None

        candidato: PerfilConsumidor | None = None
        # 1. Comprobar contra todos los perfiles registrados en esta instancia
        for perfil in self._consumidores.values():
            if perfil.activo and hmac.compare_digest(api_key, perfil.api_key):
                candidato = perfil

        # 2. Si no coincide pero coincide con la clave configurada en Ajustes
        if candidato is None:
            clave_ajustes = obtener_ajustes().dirpoles_ia_api_key
            if clave_ajustes and hmac.compare_digest(api_key, clave_ajustes):
                candidato = self.obtener_por_id("dirpoles4")

        return candidato

    def cargar_desde_archivo(self, ruta: str) -> int:
        """Carga perfiles de consumidores desde un archivo JSON estructurado."""
        if not os.path.exists(ruta):
            return 0
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except Exception:
            return 0

        cargados = 0
        if isinstance(datos, list):
            for item in datos:
                if isinstance(item, dict) and "id" in item and "api_key" in item:
                    perfil = PerfilConsumidor(
                        id=str(item["id"]),
                        nombre=str(item.get("nombre", item["id"])),
                        api_key=str(item["api_key"]),
                        modo_acceso=str(item.get("modo_acceso", "push")),
                        conocimiento_id=str(item.get("conocimiento_id", "dirpoles4")),
                        adaptador_id=str(item.get("adaptador_id", "en_memoria")),
                        activo=bool(item.get("activo", True)),
                    )
                    self.registrar(perfil)
                    cargados += 1
        return cargados


@lru_cache
def obtener_registro_consumidores() -> RegistroConsumidores:
    """Singleton del registro de consumidores con carga inicial."""
    ajustes = obtener_ajustes()
    registro = RegistroConsumidores()

    # 1. Registrar al consumidor de referencia institucional (DIRPOLES-4)
    registro.registrar(
        PerfilConsumidor(
            id="dirpoles4",
            nombre="DIRPOLES-4 Monolito Institucional (UPTAEB)",
            api_key=ajustes.dirpoles_ia_api_key,
            modo_acceso="sql_pull",
            conocimiento_id="dirpoles4",
            adaptador_id="dirpoles4_sql",
            activo=True,
        )
    )

    # 2. Cargar perfiles declarativos si existe el archivo de configuración
    ruta_archivo = getattr(ajustes, "consumidores_file", "config/consumidores.json")
    if os.path.exists(ruta_archivo):
        registro.cargar_desde_archivo(ruta_archivo)

    return registro
