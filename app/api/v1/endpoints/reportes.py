import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import validar_api_key
from app.schemas.enums import (
    AreaGeneral,
    EstadoCita,
    EstadoInventario,
    EstadoJornada,
    EstadoReferencia,
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
from app.schemas.request import ReporteRequestDTO
from app.schemas.response import MetaDTO, ReporteResponseDTO
from app.services import etl_service, gemini_service, prompt_service

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])


@router.post("/generar", response_model=ReporteResponseDTO)
def generar_reporte(
    peticion: ReporteRequestDTO,
    _api_key: Annotated[str, Depends(validar_api_key)],
) -> ReporteResponseDTO:
    inicio = time.perf_counter()
    try:
        resumen = etl_service.procesar(
            modulo=peticion.modulo,
            filtros=peticion.filtros,
            id_empleado=peticion.id_empleado,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "exito": False,
                "detalle": "No fue posible extraer los datos de la base de datos.",
                "error": str(exc),
            },
        ) from exc

    system_prompt, user_prompt = prompt_service.construir_prompts(
        modulo=peticion.modulo,
        intencion=peticion.intencion,
        resumen=resumen,
        observacion_usuario=peticion.observacion_usuario,
    )
    contexto = {
        "resumen": resumen,
        "intencion": peticion.intencion.value,
        "modulo": peticion.modulo.value,
    }
    cliente = gemini_service.obtener_cliente()
    try:
        informe = cliente.generar_informe(system_prompt, user_prompt, contexto)
        modo = cliente.modo
    except Exception:
        informe = gemini_service.ClienteSimulado().generar_informe(
            system_prompt, user_prompt, contexto
        )
        modo = "simulado_fallback"

    transcurrido = time.perf_counter() - inicio
    return ReporteResponseDTO(
        exito=True,
        modulo=peticion.modulo,
        intencion=peticion.intencion,
        informe_markdown=informe,
        meta=MetaDTO(
            registros_procesados=int(resumen.get("registros_procesados", 0)),
            tiempo_procesamiento_seg=round(transcurrido, 2),
            modo_informe=modo,
        ),
    )


@router.get("/catalogos")
def catalogos(
    _api_key: Annotated[str, Depends(validar_api_key)],
) -> dict[str, list[str]]:
    return {
        "modulos": [valor.value for valor in Modulo],
        "intenciones": [valor.value for valor in Intencion],
        "areas": [valor.value for valor in AreaGeneral],
        "submodulos_trabajo_social": [valor.value for valor in SubmoduloTrabajoSocial],
        "tipos_consulta": [valor.value for valor in TipoConsultaPsicologica],
        "tipos_discapacidad": [valor.value for valor in TipoDiscapacidad],
        "grados_discapacidad": [valor.value for valor in GradoDiscapacidad],
        "estados_cita": [valor.value for valor in EstadoCita],
        "estados_referencia": [valor.value for valor in EstadoReferencia],
        "estados_jornada": [valor.value for valor in EstadoJornada],
        "estados_inventario": [valor.value for valor in EstadoInventario],
        "tipos_bien": [valor.value for valor in TipoBien],
        "tipos_vehiculo": [valor.value for valor in TipoVehiculo],
        "secciones_transporte": [valor.value for valor in SeccionTransporte],
    }
