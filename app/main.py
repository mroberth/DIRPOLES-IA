from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import reportes
from app.core.config import obtener_ajustes
from app.db import session


@asynccontextmanager
async def _ciclo_vida(_app: FastAPI) -> AsyncIterator[None]:
    yield
    session.cerrar_motor()


def crear_app() -> FastAPI:
    ajustes = obtener_ajustes()
    app = FastAPI(
        title="DIRPOLES-IA",
        version="1.0.0",
        description=(
            "Microservicio de analítica de datos e inteligencia artificial de DIRPOLES-4. "
            "Lectura exclusiva sobre la base de datos del monolito."
        ),
        lifespan=_ciclo_vida,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ajustes.origenes_cors,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    app.include_router(reportes.router)

    @app.get("/api/v1/salud", tags=["salud"])
    def salud() -> dict[str, object]:
        return {
            "estado": "ok",
            "servicio": "DIRPOLES-IA",
            "base_datos": "ok" if session.ping() else "no_disponible",
            "modo_llm": "gemini" if ajustes.usar_gemini_real else "simulado",
        }

    return app


app = crear_app()
