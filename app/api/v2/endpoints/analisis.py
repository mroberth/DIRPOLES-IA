from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.consumers import PerfilConsumidor
from app.core.security import validar_api_key
from app.schemas.v2 import AnalisisRequestV2DTO, AnalisisResponseV2DTO
from app.services.analisis_v2_service import ejecutar_analisis_v2

router = APIRouter(prefix="/api/v2", tags=["analisis_v2"])


@router.post("/analizar", response_model=AnalisisResponseV2DTO)
def analizar(
    peticion: AnalisisRequestV2DTO,
    _consumidor: Annotated[PerfilConsumidor, Depends(validar_api_key)],
) -> AnalisisResponseV2DTO:
    """Endpoint universal de análisis asistido por IA (Modo Push sin base de datos).

    Permite a cualquier sistema consumidor externo (PHP, Python, Node.js, Go, etc.)
    enviar un dataset o métricas agregadas normalizadas para obtener:
    1. Resumen ejecutivo con tablas comparativas.
    2. Detección automática de anomalías y alertas por concentración o variación.
    3. Visualizaciones gráficas nativas en bloques Mermaid.js (`pie` o `xychart-beta`).
    4. Recomendaciones operativas accionables para la toma de decisiones.
    """
    return ejecutar_analisis_v2(peticion)
