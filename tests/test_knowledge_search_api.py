import asyncio
from collections.abc import Iterator
from types import TracebackType
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.dependencies.knowledge_search import (
    get_knowledge_search_service,
)
from app.core.config import Settings
from app.core.exceptions import (
    AIProviderConfigurationError,
    AIProviderConnectionError,
    AIProviderError,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderRequestError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.main import app
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.knowledge import (
    KnowledgeArticle,
    KnowledgeSearchMatch,
)
from app.services.knowledge_search import KnowledgeSearchService


def create_match(
    article_id: str,
    score: float,
) -> KnowledgeSearchMatch:
    """Cria um resultado sintético para a API."""

    article = KnowledgeArticle.model_validate(
        {
            "id": article_id,
            "title": "Como recuperar o acesso à conta",
            "content": (
                "Utilize a recuperação de senha para voltar a acessar "
                "a plataforma com segurança."
            ),
            "category": "acesso_e_autenticacao",
            "keywords": [
                "senha",
                "login",
            ],
        },
    )

    return KnowledgeSearchMatch(
        article=article,
        score=score,
    )


class FakeKnowledgeSearchService:
    """Serviço previsível usado pelo endpoint."""

    model = "test-embedding-model"
    indexed_articles = 12

    def __init__(
        self,
        matches: list[KnowledgeSearchMatch] | None = None,
    ) -> None:
        self.matches = matches or [
            create_match(
                "recover-account-access",
                0.95,
            ),
        ]
        self.calls: list[tuple[str, int]] = []

    async def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        self.calls.append(
            (
                query,
                top_k,
            ),
        )

        return self.matches[:top_k]


class FakeEmbeddingItem:
    """Item de embedding compatível com a resposta da SDK."""

    def __init__(
        self,
        *,
        index: int,
        embedding: list[float],
    ) -> None:
        self.index = index
        self.embedding = embedding


class FakeEmbeddingResponse:
    """Resposta de embeddings compatível com a SDK."""

    def __init__(
        self,
        embeddings: list[list[float]],
    ) -> None:
        self.data = [
            FakeEmbeddingItem(
                index=index,
                embedding=embedding,
            )
            for index, embedding in enumerate(embeddings)
        ]


class FakeEmbeddingsResource:
    """Recurso falso para geração de embeddings."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(
        self,
        **kwargs: object,
    ) -> FakeEmbeddingResponse:
        self.calls.append(kwargs)
        texts = kwargs["input"]

        assert isinstance(texts, list)

        return FakeEmbeddingResponse(
            [
                [
                    1.0,
                    0.0,
                ]
                for _ in texts
            ],
        )


class FakeOpenAIClient:
    """Cliente falso com o recurso de embeddings."""

    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()


class FakeAsyncOpenAI:
    """Context manager falso para impedir chamadas externas."""

    instances: list["FakeAsyncOpenAI"] = []

    def __init__(
        self,
        **kwargs: object,
    ) -> None:
        self.kwargs = kwargs
        self.client = FakeOpenAIClient()
        self.closed = False
        self.__class__.instances.append(self)

    async def __aenter__(self) -> FakeOpenAIClient:
        return self.client

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.closed = True


@pytest.fixture
def fake_knowledge_search_service() -> FakeKnowledgeSearchService:
    """Retorna o serviço falso usado pela rota."""

    return FakeKnowledgeSearchService()


@pytest.fixture
def knowledge_search_client(
    client: TestClient,
    fake_knowledge_search_service: FakeKnowledgeSearchService,
) -> Iterator[TestClient]:
    """Substitui a busca real por um serviço falso."""

    app.dependency_overrides[get_knowledge_search_service] = lambda: (
        fake_knowledge_search_service
    )

    try:
        yield client
    finally:
        app.dependency_overrides.pop(
            get_knowledge_search_service,
            None,
        )


def test_search_knowledge_returns_matches(
    knowledge_search_client: TestClient,
    fake_knowledge_search_service: FakeKnowledgeSearchService,
    api_key: str,
) -> None:
    response = knowledge_search_client.post(
        "/internal/knowledge/search",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "query": "  Redefini minha senha e ainda não consigo entrar  ",
            "top_k": 1,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()

    assert body["query"] == "Redefini minha senha e ainda não consigo entrar"
    assert body["model"] == "test-embedding-model"
    assert body["indexed_articles"] == 12
    assert len(body["matches"]) == 1
    assert fake_knowledge_search_service.calls == [
        (
            "Redefini minha senha e ainda não consigo entrar",
            1,
        ),
    ]

    match = body["matches"][0]

    assert match["article"] == {
        "id": "recover-account-access",
        "title": "Como recuperar o acesso à conta",
        "content": (
            "Utilize a recuperação de senha para voltar a acessar "
            "a plataforma com segurança."
        ),
        "category": "acesso_e_autenticacao",
        "keywords": [
            "senha",
            "login",
        ],
    }
    assert match["score"] == 0.95


def test_search_knowledge_uses_default_top_k(
    knowledge_search_client: TestClient,
    fake_knowledge_search_service: FakeKnowledgeSearchService,
    api_key: str,
) -> None:
    response = knowledge_search_client.post(
        "/internal/knowledge/search",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "query": "Recuperar senha",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert fake_knowledge_search_service.calls == [
        (
            "Recuperar senha",
            3,
        ),
    ]


def test_search_knowledge_rejects_missing_api_key(
    knowledge_search_client: TestClient,
    fake_knowledge_search_service: FakeKnowledgeSearchService,
) -> None:
    response = knowledge_search_client.post(
        "/internal/knowledge/search",
        json={
            "query": "Recuperar senha",
            "top_k": 1,
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid or missing API key.",
    }
    assert fake_knowledge_search_service.calls == []


def test_search_knowledge_rejects_invalid_api_key(
    knowledge_search_client: TestClient,
    fake_knowledge_search_service: FakeKnowledgeSearchService,
) -> None:
    response = knowledge_search_client.post(
        "/internal/knowledge/search",
        headers={
            "X-API-Key": "invalid-key",
        },
        json={
            "query": "Recuperar senha",
            "top_k": 1,
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid or missing API key.",
    }
    assert fake_knowledge_search_service.calls == []


@pytest.mark.parametrize(
    "query",
    [
        "   ",
        "ab",
        "x" * 1001,
    ],
)
def test_search_knowledge_rejects_invalid_query(
    knowledge_search_client: TestClient,
    api_key: str,
    query: str,
) -> None:
    response = knowledge_search_client.post(
        "/internal/knowledge/search",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "query": query,
            "top_k": 3,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "top_k",
    [
        0,
        -1,
        11,
    ],
)
def test_search_knowledge_rejects_invalid_top_k(
    knowledge_search_client: TestClient,
    api_key: str,
    top_k: int,
) -> None:
    response = knowledge_search_client.post(
        "/internal/knowledge/search",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "query": "Recuperar senha",
            "top_k": top_k,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_search_knowledge_rejects_extra_field(
    knowledge_search_client: TestClient,
    api_key: str,
) -> None:
    response = knowledge_search_client.post(
        "/internal/knowledge/search",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "query": "Recuperar senha",
            "top_k": 3,
            "unexpected": True,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "payload",
    [
        {
            "query": ["Recuperar senha"],
            "top_k": 3,
        },
        {
            "query": "Recuperar senha",
            "top_k": {
                "value": 3,
            },
        },
    ],
)
def test_search_knowledge_rejects_invalid_types(
    knowledge_search_client: TestClient,
    api_key: str,
    payload: dict[str, object],
) -> None:
    response = knowledge_search_client.post(
        "/internal/knowledge/search",
        headers={
            "X-API-Key": api_key,
        },
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_search_knowledge_limits_results(
    client: TestClient,
    api_key: str,
) -> None:
    service = FakeKnowledgeSearchService(
        matches=[
            create_match(
                "recover-account-access",
                0.95,
            ),
            create_match(
                "configure-multi-factor-authentication",
                0.9,
            ),
            create_match(
                "identify-unsupported-request",
                0.2,
            ),
        ],
    )

    app.dependency_overrides[get_knowledge_search_service] = lambda: service

    try:
        response = client.post(
            "/internal/knowledge/search",
            headers={
                "X-API-Key": api_key,
            },
            json={
                "query": "Recuperar senha",
                "top_k": 2,
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_knowledge_search_service,
            None,
        )

    assert response.status_code == status.HTTP_200_OK
    assert [match["article"]["id"] for match in response.json()["matches"]] == [
        "recover-account-access",
        "configure-multi-factor-authentication",
    ]


def test_openapi_documents_knowledge_search(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == status.HTTP_200_OK

    schema = response.json()
    operation = schema["paths"]["/internal/knowledge/search"]["post"]

    assert operation["tags"] == [
        "Internal Knowledge",
    ]
    assert operation["security"] == [
        {
            "InternalApiKey": [],
        },
    ]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/KnowledgeSearchRequest",
    }

    responses = operation["responses"]

    assert responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/KnowledgeSearchResponse",
    }

    for response_code in [
        "200",
        "401",
        "422",
        "502",
        "503",
        "504",
    ]:
        assert response_code in responses


@pytest.mark.parametrize(
    (
        "provider_error",
        "expected_status",
        "expected_code",
        "expected_retryable",
    ),
    [
        (
            AIProviderConfigurationError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_not_configured",
            False,
        ),
        (
            AIProviderUnavailableError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_unavailable",
            True,
        ),
        (
            AIProviderConnectionError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_unreachable",
            True,
        ),
        (
            AIProviderTimeoutError(),
            status.HTTP_504_GATEWAY_TIMEOUT,
            "ai_provider_timeout",
            True,
        ),
        (
            AIProviderInvalidResponseError(),
            status.HTTP_502_BAD_GATEWAY,
            "ai_provider_invalid_response",
            False,
        ),
        (
            AIProviderRequestError(),
            status.HTTP_502_BAD_GATEWAY,
            "ai_provider_request_rejected",
            False,
        ),
        (
            AIProviderRateLimitError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_rate_limited",
            True,
        ),
    ],
)
def test_search_knowledge_maps_provider_errors(
    client: TestClient,
    api_key: str,
    provider_error: AIProviderError,
    expected_status: int,
    expected_code: str,
    expected_retryable: bool,
) -> None:
    service = FakeKnowledgeSearchService()

    async def raise_provider_error(
        query: str,
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        service.calls.append(
            (
                query,
                top_k,
            ),
        )

        raise provider_error

    service.search = raise_provider_error

    app.dependency_overrides[get_knowledge_search_service] = lambda: service

    try:
        response = client.post(
            "/internal/knowledge/search",
            headers={
                "X-API-Key": api_key,
            },
            json={
                "query": "Recuperar senha",
                "top_k": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_knowledge_search_service,
            None,
        )

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code
    assert response.json()["retryable"] is expected_retryable


def test_search_knowledge_rate_limit_includes_retry_after(
    client: TestClient,
    api_key: str,
) -> None:
    service = FakeKnowledgeSearchService()

    async def raise_rate_limit(
        query: str,
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        service.calls.append(
            (
                query,
                top_k,
            ),
        )

        raise AIProviderRateLimitError()

    service.search = raise_rate_limit

    app.dependency_overrides[get_knowledge_search_service] = lambda: service

    try:
        response = client.post(
            "/internal/knowledge/search",
            headers={
                "X-API-Key": api_key,
            },
            json={
                "query": "Recuperar senha",
                "top_k": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_knowledge_search_service,
            None,
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Retry-After"] == "30"


async def resolve_knowledge_search_service(
    settings: Settings,
) -> KnowledgeSearchService:
    """Resolve a dependência assíncrona em testes."""

    dependency = get_knowledge_search_service(settings)

    async for service in dependency:
        return service

    raise AssertionError("Dependency did not yield a search service.")


def create_settings(
    *,
    openai_api_key: SecretStr | None,
) -> Settings:
    """Cria settings isoladas para testar a dependência."""

    return Settings(
        _env_file=None,
        app_name="AI Service",
        app_version="0.1.0",
        environment="test",
        internal_api_key=SecretStr("test-internal-api-key"),
        openai_api_key=openai_api_key,
        openai_model="test-model",
        openai_embedding_model="test-embedding-model",
        openai_prompt_strategy=PromptStrategy.ONE_SHOT,
    )


def test_knowledge_search_dependency_builds_service_without_network() -> None:
    FakeAsyncOpenAI.instances = []
    settings = create_settings(
        openai_api_key=SecretStr("test-openai-api-key"),
    )

    with patch(
        "app.api.dependencies.knowledge_search.AsyncOpenAI",
        FakeAsyncOpenAI,
    ):
        service = asyncio.run(
            resolve_knowledge_search_service(settings),
        )

    assert service.model == "test-embedding-model"
    assert service.indexed_articles == 12

    openai_instance = FakeAsyncOpenAI.instances[0]

    assert openai_instance.kwargs["timeout"] == 30.0
    assert openai_instance.kwargs["max_retries"] == 2
    assert openai_instance.closed is True
    assert openai_instance.client.embeddings.calls[0]["model"] == (
        "test-embedding-model"
    )
    assert len(openai_instance.client.embeddings.calls[0]["input"]) == 12


def test_knowledge_search_dependency_rejects_missing_openai_key() -> None:
    settings = create_settings(
        openai_api_key=None,
    )

    with pytest.raises(AIProviderConfigurationError):
        asyncio.run(
            resolve_knowledge_search_service(settings),
        )


def test_knowledge_search_dependency_rejects_blank_openai_key() -> None:
    settings = create_settings(
        openai_api_key=SecretStr("   "),
    )

    with pytest.raises(AIProviderConfigurationError):
        asyncio.run(
            resolve_knowledge_search_service(settings),
        )
