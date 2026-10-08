from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.enums import (
    ESTADOS_CONCATABLES,
    AreaGeneral,
    Genero,
    GradoDiscapacidad,
    Intencion,
    Modulo,
    SeccionTransporte,
    SubmoduloTrabajoSocial,
    TipoBien,
    TipoConsultaPsicologica,
    TipoDiscapacidad,
    TipoVehiculo,
)


class FiltrosDTO(BaseModel):
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    genero: Genero | None = None
    pnf: int | None = Field(default=None, ge=1)
    area: AreaGeneral | None = None
    estado: str | None = Field(default=None, max_length=60)
    tipo_consulta: TipoConsultaPsicologica | None = None
    submodulo: SubmoduloTrabajoSocial | None = None
    grado: GradoDiscapacidad | None = None
    tipo_discapacidad: TipoDiscapacidad | None = None
    tipo_bien: TipoBien | None = None
    tipo_vehiculo: TipoVehiculo | None = None
    seccion_transporte: SeccionTransporte | None = None
    servicio_destino: int | None = Field(default=None, ge=1)
    limit: int | None = Field(default=None, ge=1, le=20000)

    @field_validator("estado")
    @classmethod
    def _estado_seguro(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = valor.strip()
        if not limpio:
            return None
        if "<" in limpio or ">" in limpio:
            raise ValueError("El filtro estado no puede contener los caracteres '<' ni '>'")
        return limpio

    @model_validator(mode="after")
    def _validar_rango_fechas(self) -> "FiltrosDTO":
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser mayor que fecha_fin")
        return self


class ReporteRequestDTO(BaseModel):
    modulo: Modulo
    intencion: Intencion
    filtros: FiltrosDTO = Field(default_factory=FiltrosDTO)
    observacion_usuario: str | None = Field(default=None, max_length=1000)
    id_empleado: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validar_estado_por_modulo(self) -> "ReporteRequestDTO":
        catalogo = ESTADOS_CONCATABLES.get(self.modulo)
        estado = self.filtros.estado
        if catalogo is not None and estado is not None and estado not in catalogo:
            permitidos = ", ".join(catalogo)
            raise ValueError(
                f"estado '{estado}' no es válido para {self.modulo.value}; use: {permitidos}"
            )
        return self
