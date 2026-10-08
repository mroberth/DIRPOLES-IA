from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    dirpoles_ia_api_key: str

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "dirpoles_ia_reader"
    db_password: str = ""
    db_name_business: str = "dirpoles_business"
    db_name_security: str = "dirpoles_security"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    mock_llm: bool = True

    umbral_stock_critico_insumos: int = Field(default=10, ge=1)
    umbral_stock_critico_repuestos: int = Field(default=5, ge=1)
    limite_registros: int = Field(default=5000, ge=1, le=20000)

    allowed_origins: str = "http://localhost,http://localhost:80"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _sin_espacios(cls, valor: object) -> object:
        if isinstance(valor, str):
            return valor.strip()
        return valor

    @property
    def usar_gemini_real(self) -> bool:
        return bool(self.gemini_api_key) and not self.mock_llm

    @property
    def origenes_cors(self) -> list[str]:
        return [origen.strip() for origen in self.allowed_origins.split(",") if origen.strip()]


@lru_cache(maxsize=1)
def obtener_ajustes() -> Ajustes:
    return Ajustes()
