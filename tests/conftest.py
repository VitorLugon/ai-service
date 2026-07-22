from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.main import app
from app.prompts.ticket_classification import PromptStrategy

TEST_API_KEY = "test-internal-api-key"


@pytest.fixture
def api_key() -> str:
    """Retorna a chave utilizada nos testes."""

    return TEST_API_KEY


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cria um cliente com configurações isoladas para cada teste."""

    def override_get_settings() -> Settings:
        return Settings(
            _env_file=None,
            app_name="AI Service",
            app_version="0.1.0",
            environment="test",
            internal_api_key=SecretStr(TEST_API_KEY),
            openai_api_key=None,
            openai_model="test-model",
            openai_prompt_strategy=PromptStrategy.ONE_SHOT,
        )

    # Remove configurações que possam ter sido armazenadas
    # anteriormente pelo @lru_cache.
    get_settings.cache_clear()

    app.dependency_overrides[get_settings] = override_get_settings

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        get_settings.cache_clear()
