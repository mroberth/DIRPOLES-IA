from pydantic import BaseModel, Field

from app.schemas.enums import Intencion, Modulo


class MetaDTO(BaseModel):
    registros_procesados: int = Field(ge=0)
    tiempo_procesamiento_seg: float = Field(ge=0)
    modo_informe: str


class ReporteResponseDTO(BaseModel):
    exito: bool
    modulo: Modulo
    intencion: Intencion
    informe_markdown: str
    meta: MetaDTO
