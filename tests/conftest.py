from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.main import app

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
            app_name="AI Service",
            app_version="0.1.0",
            environment="test",
            internal_api_key=SecretStr(TEST_API_KEY),
        )

    app.dependency_overrides[get_settings] = override_get_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()