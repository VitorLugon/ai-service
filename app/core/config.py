from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações gerais da aplicação."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Service"
    app_version: str = "0.1.0"
    environment: str = "development"
    internal_api_key: SecretStr = SecretStr("development-only-key")


@lru_cache
def get_settings() -> Settings:
    """Retorna uma instância reutilizável das configurações."""

    return Settings()