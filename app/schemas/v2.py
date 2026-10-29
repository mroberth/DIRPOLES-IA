import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.enums import Intencion
from app.schemas.response import MetaDTO


class PeriodoV2DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha_inicio: str | None = None
    fecha_fin: str | None = None


class DistribucionItemV2DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valor: str = Field(min_length=1, max_length=150)
    cantidad: int = Field(ge=0)
    porcentaje: float | None = Field(default=None, ge=0.0, le=100.0)


class PuntoMesV2DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mes: str = Field(pattern=r"^\d{4}-\d{2}$")
    cantidad: int = Field(ge=0)


class AlertaEntradaV2DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nivel: str = Field(default="advertencia", pattern=r"^(critico|advertencia|info)$")
    mensaje: str = Field(min_length=3, max_length=500)


class ReglasAnaliticasV2DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    umbral_concentracion_pct: float = Field(default=40.0, ge=10.0, le=100.0)
    umbral_variacion_mensual_pct: float = Field(default=25.0, ge=5.0, le=500.0)


class MetricasEntradaV2DTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    totales: dict[str, int] = Field(default_factory=dict)
    distribuciones: dict[str, list[DistribucionItemV2DTO]] = Field(default_factory=dict)
    serie_mensual: list[PuntoMesV2DTO] = Field(default_factory=list)
    indicadores: dict[str, Any] = Field(default_factory=dict)
    alertas: list[AlertaEntradaV2DTO] = Field(default_factory=list)

    @field_validator("totales")
    @classmethod
    def validar_totales(cls, v: dict[str, int]) -> dict[str, int]:
        for k, val in v.items():
            if val < 0:
                raise ValueError(f"El total '{k}' no puede ser negativo.")
        return v


class AnalisisRequestV2DTO(BaseModel):
    """Contrato de entrada universal (Modo Push) para la API V2.

    Permite a cualquier sistema consumidor enviar sus métricas agregadas
    directamente sin requerir conexión a base de datos externa.
    """

    model_config = ConfigDict(extra="forbid")

    dominio: str = Field(
        min_length=2,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Identificador del dominio o módulo analizado (ej: urgencias, inventario, ventas).",
    )
    intencion: Intencion = Field(
        default=Intencion.RESUMEN_EJECUTIVO,
        description="Objetivo del informe analítico.",
    )
    periodo: PeriodoV2DTO = Field(default_factory=PeriodoV2DTO)
    metricas: MetricasEntradaV2DTO
    rol_analista: str | None = Field(
        default=None,
        max_length=200,
        description="Definición opcional del rol institucional/profesional para el prompt del LLM.",
    )
    observacion_usuario: str | None = Field(
        default=None,
        max_length=1000,
        description="Foco o directriz analítica adicional del usuario.",
    )
    reglas_analiticas: ReglasAnaliticasV2DTO = Field(default_factory=ReglasAnaliticasV2DTO)


class AnalisisResponseV2DTO(BaseModel):
    """Contrato de respuesta universal para la API V2."""

    model_config = ConfigDict(extra="forbid")

    exito: bool = True
    dominio: str
    intencion: Intencion
    informe_markdown: str
    meta: MetaDTO
