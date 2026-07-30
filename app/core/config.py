from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.prompts.ticket_classification import PromptStrategy


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

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_prompt_strategy: PromptStrategy = PromptStrategy.ONE_SHOT


@lru_cache
def get_settings() -> Settings:
    """Retorna uma instância reutilizável das configurações."""

    return Settings()
