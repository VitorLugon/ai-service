import asyncio
from collections.abc import Iterator, Sequence
from types import TracebackType
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.dependencies.rag import get_rag_service
from app.core.config import Settings
from app.core.exceptions import (
    AIProviderConfigurationError,
    AIProviderError,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    KnowledgeStoreUnavailableError,
)
from app.main import app
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.knowledge import KnowledgeSearchFilter, KnowledgeSearchMatch
from app.schemas.rag import RagAnswer, RagAnswerSource
from app.schemas.tickets import TicketCategory
from app.services.rag_service import RagService


class FakeRagService:
    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        self.error = error
        self.calls: list[tuple[str, int, KnowledgeSearchFilter | None]] = []

    async def answer(
        self,
        *,
        question: str,
        top_k: int = 3,
        search_filter: KnowledgeSearchFilter | None = None,
    ) -> RagAnswer:
        self.calls.append(
            (
                question,
                top_k,
                search_filter,
            ),
        )

        if self.error is not None:
            raise self.error

        return RagAnswer(
            answer="Use o fluxo de recuperação de senha antes de tentar novo login.",
            sources=[
                RagAnswerSource(
                    source_id="recover-account-access",
                    article_id="recover-account-access",
                    title="Como recuperar o acesso à conta",
                    category=TicketCategory.ACCESS_AND_AUTHENTICATION,
                    rank=1,
                ),
            ],
            source_count=1,
        )


class FakeKnowledgeSearchBackend:
    @property
    def size(self) -> int:
        return 5

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        return []


class FakeEmbeddingResponse:
    data: list[object] = []


class FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(
        self,
        **kwargs: object,
    ) -> FakeEmbeddingResponse:
        self.calls.append(
            kwargs,
        )
        return FakeEmbeddingResponse()


class FakeResponsesResource:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(
        self,
        **kwargs: object,
    ) -> object:
        self.calls.append(
            kwargs,
        )
        return object()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()
        self.responses = FakeResponsesResource()


class FakeAsyncOpenAI:
    instances: list["FakeAsyncOpenAI"] = []

    def __init__(
        self,
        **kwargs: object,
    ) -> None:
        self.kwargs = kwargs
        self.client = FakeOpenAIClient()
        self.closed = False
        self.__class__.instances.append(
            self,
        )

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
def fake_rag_service() -> FakeRagService:
    return FakeRagService()


@pytest.fixture
def rag_client(
    client: TestClient,
    fake_rag_service: FakeRagService,
) -> Iterator[TestClient]:
    app.dependency_overrides[get_rag_service] = lambda: fake_rag_service

    try:
        yield client
    finally:
        app.dependency_overrides.pop(
            get_rag_service,
            None,
        )


def test_rag_answer_endpoint_returns_grounded_answer(
    rag_client: TestClient,
    fake_rag_service: FakeRagService,
    api_key: str,
) -> None:
    response = rag_client.post(
        "/internal/rag/answer",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "query": "  Redefini minha senha e continuo sem acesso  ",
            "top_k": 1,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "answer": "Use o fluxo de recuperação de senha antes de tentar novo login.",
        "sources": [
            {
                "source_id": "recover-account-access",
                "article_id": "recover-account-access",
                "chunk_id": None,
                "title": "Como recuperar o acesso à conta",
                "category": "acesso_e_autenticacao",
                "rank": 1,
            },
        ],
        "source_count": 1,
    }
    assert fake_rag_service.calls == [
        (
            "Redefini minha senha e continuo sem acesso",
            1,
            None,
        ),
    ]


def test_rag_answer_endpoint_uses_default_top_k(
    rag_client: TestClient,
    fake_rag_service: FakeRagService,
    api_key: str,
) -> None:
    response = rag_client.post(
        "/internal/rag/answer",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "query": "Como recuperar acesso?",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert fake_rag_service.calls == [
        (
            "Como recuperar acesso?",
            3,
            None,
        ),
    ]


def test_rag_answer_endpoint_accepts_category_filter(
    rag_client: TestClient,
    fake_rag_service: FakeRagService,
    api_key: str,
) -> None:
    response = rag_client.post(
        "/internal/rag/answer",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "query": "Minha conta continua suspensa após pagamento",
            "top_k": 2,
            "category": "cobranca",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert fake_rag_service.calls == [
        (
            "Minha conta continua suspensa após pagamento",
            2,
            KnowledgeSearchFilter(
                category=TicketCategory.BILLING,
            ),
        ),
    ]


def test_rag_answer_endpoint_rejects_missing_api_key(
    rag_client: TestClient,
    fake_rag_service: FakeRagService,
) -> None:
    response = rag_client.post(
        "/internal/rag/answer",
        json={
            "query": "Como recuperar acesso?",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert fake_rag_service.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {
            "query": "   ",
        },
        {
            "query": "x" * 2001,
        },
        {
            "query": "Como recuperar acesso?",
            "top_k": 0,
        },
        {
            "query": "Como recuperar acesso?",
            "top_k": 11,
        },
        {
            "query": "Como recuperar acesso?",
            "category": "billing",
        },
        {
            "query": "Como recuperar acesso?",
            "unexpected": True,
        },
    ],
)
def test_rag_answer_endpoint_rejects_invalid_payloads(
    rag_client: TestClient,
    api_key: str,
    payload: dict[str, object],
) -> None:
    response = rag_client.post(
        "/internal/rag/answer",
        headers={
            "X-API-Key": api_key,
        },
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    (
        "provider_error",
        "expected_status",
        "expected_code",
    ),
    [
        (
            AIProviderConfigurationError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_not_configured",
        ),
        (
            AIProviderTimeoutError(),
            status.HTTP_504_GATEWAY_TIMEOUT,
            "ai_provider_timeout",
        ),
        (
            AIProviderInvalidResponseError(),
            status.HTTP_502_BAD_GATEWAY,
            "ai_provider_invalid_response",
        ),
        (
            AIProviderRateLimitError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_rate_limited",
        ),
    ],
)
def test_rag_answer_endpoint_maps_provider_errors(
    client: TestClient,
    api_key: str,
    provider_error: AIProviderError,
    expected_status: int,
    expected_code: str,
) -> None:
    service = FakeRagService(
        error=provider_error,
    )
    app.dependency_overrides[get_rag_service] = lambda: service

    try:
        response = client.post(
            "/internal/rag/answer",
            headers={
                "X-API-Key": api_key,
            },
            json={
                "query": "Como recuperar acesso?",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_rag_service,
            None,
        )

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code


def test_rag_answer_endpoint_rate_limit_includes_retry_after(
    client: TestClient,
    api_key: str,
) -> None:
    service = FakeRagService(
        error=AIProviderRateLimitError(),
    )
    app.dependency_overrides[get_rag_service] = lambda: service

    try:
        response = client.post(
            "/internal/rag/answer",
            headers={
                "X-API-Key": api_key,
            },
            json={
                "query": "Como recuperar acesso?",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_rag_service,
            None,
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Retry-After"] == "30"


def test_rag_answer_endpoint_maps_knowledge_store_errors(
    client: TestClient,
    api_key: str,
) -> None:
    service = FakeRagService(
        error=KnowledgeStoreUnavailableError(),
    )
    app.dependency_overrides[get_rag_service] = lambda: service

    try:
        response = client.post(
            "/internal/rag/answer",
            headers={
                "X-API-Key": api_key,
            },
            json={
                "query": "Como recuperar acesso?",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_rag_service,
            None,
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "knowledge_store_unavailable"


def test_openapi_documents_rag_answer(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == status.HTTP_200_OK

    operation = response.json()["paths"]["/internal/rag/answer"]["post"]

    assert operation["tags"] == [
        "Internal RAG",
    ]
    assert operation["security"] == [
        {
            "InternalApiKey": [],
        },
    ]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RagAnswerRequest",
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RagAnswerResponse",
    }


async def resolve_rag_service(
    settings: Settings,
    backend: FakeKnowledgeSearchBackend,
) -> RagService:
    dependency = get_rag_service(
        backend,
        settings,
    )

    async for service in dependency:
        return service

    raise AssertionError("Dependency did not yield a RAG service.")


async def collect_dependency_error(
    settings: Settings,
) -> Exception:
    try:
        await resolve_rag_service(
            settings,
            FakeKnowledgeSearchBackend(),
        )
    except Exception as error:
        return error

    raise AssertionError("Dependency did not fail.")


def create_settings(
    *,
    openai_api_key: SecretStr | None,
) -> Settings:
    return Settings(
        _env_file=None,
        app_name="AI Service",
        app_version="0.1.0",
        environment="test",
        internal_api_key=SecretStr("test-internal-api-key"),
        openai_api_key=openai_api_key,
        openai_model="test-model",
        openai_rag_model="test-rag-model",
        openai_embedding_model="test-embedding-model",
        openai_prompt_strategy=PromptStrategy.ONE_SHOT,
    )


def test_rag_dependency_builds_service_without_network() -> None:
    FakeAsyncOpenAI.instances = []
    settings = create_settings(
        openai_api_key=SecretStr("test-openai-api-key"),
    )

    with patch(
        "app.api.dependencies.rag.AsyncOpenAI",
        FakeAsyncOpenAI,
    ):
        service = asyncio.run(
            resolve_rag_service(
                settings,
                FakeKnowledgeSearchBackend(),
            ),
        )

    assert isinstance(
        service,
        RagService,
    )
    assert FakeAsyncOpenAI.instances[0].kwargs["timeout"] == 60.0
    assert FakeAsyncOpenAI.instances[0].kwargs["max_retries"] == 2
    assert FakeAsyncOpenAI.instances[0].closed is True
    assert FakeAsyncOpenAI.instances[0].client.embeddings.calls == []
    assert FakeAsyncOpenAI.instances[0].client.responses.calls == []


def test_rag_dependency_rejects_missing_openai_key() -> None:
    error = asyncio.run(
        collect_dependency_error(
            create_settings(
                openai_api_key=None,
            ),
        ),
    )

    assert isinstance(
        error,
        AIProviderConfigurationError,
    )


def test_rag_dependency_rejects_blank_openai_key() -> None:
    error = asyncio.run(
        collect_dependency_error(
            create_settings(
                openai_api_key=SecretStr("   "),
            ),
        ),
    )

    assert isinstance(
        error,
        AIProviderConfigurationError,
    )
