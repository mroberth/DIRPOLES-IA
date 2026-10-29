from typing import Annotated

from fastapi import Header, HTTPException

from app.core.consumers import PerfilConsumidor, obtener_registro_consumidores


async def validar_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> PerfilConsumidor:
    """Valida la cabecera X-API-Key contra el registro multitenant de consumidores.

    Retorna el PerfilConsumidor autenticado si la clave es válida, o lanza HTTP 401
    si es ausente o no autorizada.
    """
    registro = obtener_registro_consumidores()
    consumidor = registro.autenticar(x_api_key)
    if consumidor is None:
        raise HTTPException(
            status_code=401,
            detail="Cabecera X-API-Key ausente o inválida.",
        )
    return consumidor
