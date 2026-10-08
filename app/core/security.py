import hmac
from typing import Annotated

from fastapi import Header, HTTPException

from app.core.config import obtener_ajustes


async def validar_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    esperada = obtener_ajustes().dirpoles_ia_api_key
    if not x_api_key or not hmac.compare_digest(x_api_key, esperada):
        raise HTTPException(
            status_code=401,
            detail="Cabecera X-API-Key ausente o inválida.",
        )
    return x_api_key
