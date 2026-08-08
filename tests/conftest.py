from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.app_state import ApplicationResources
from app.core.config import Settings, get_settings
from app.main import app
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.knowledge import KnowledgeSearchMatch

TEST_API_KEY = "test-internal-api-key"


class TestKnowledgeSearchBackend:
    """Backend fake para impedir acesso ao Chroma real na suíte."""

    @property
    def size(self) -> int:
        return 0

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        return []


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
            openai_embedding_model="test-embedding-model",
            openai_prompt_strategy=PromptStrategy.ONE_SHOT,
        )

    # Remove configurações que possam ter sido armazenadas
    # anteriormente pelo @lru_cache.
    get_settings.cache_clear()

    app.dependency_overrides[get_settings] = override_get_settings
    app.state.resources = ApplicationResources(
        knowledge_search_backend=TestKnowledgeSearchBackend(),
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.state._state.pop(
            "resources",
            None,
        )
        get_settings.cache_clear()
