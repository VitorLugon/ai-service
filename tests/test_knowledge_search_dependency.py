import asyncio
from collections.abc import Sequence
from types import SimpleNamespace, TracebackType
from typing import cast

import pytest
from fastapi import Request
from pydantic import SecretStr

import app.api.dependencies.knowledge_search as dependency_module
from app.api.dependencies.knowledge_search import (
    get_knowledge_search_backend,
    get_knowledge_search_service,
)
from app.core.app_state import ApplicationResources
from app.core.config import Settings
from app.core.exceptions import (
    AIProviderConfigurationError,
    KnowledgeStoreUnavailableError,
)
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.knowledge import KnowledgeSearchMatch
from app.services.knowledge_search import KnowledgeSearchService


class FakeKnowledgeSearchBackend:
    def __init__(self) -> None:
        self.received_embeddings: list[list[float]] = []
        self.received_top_k: list[int] = []

    @property
    def size(self) -> int:
        return 5

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        self.received_embeddings.append(
            list(query_embedding),
        )
        self.received_top_k.append(
            top_k,
        )

        return []


class FakeEmbeddingItem:
    def __init__(
        self,
        *,
        index: int,
        embedding: list[float],
    ) -> None:
        self.index = index
        self.embedding = embedding


class FakeEmbeddingResponse:
    def __init__(
        self,
        embeddings: list[list[float]],
    ) -> None:
        self.data = [
            FakeEmbeddingItem(
                index=index,
                embedding=embedding,
            )
            for index, embedding in enumerate(
                embeddings,
            )
        ]


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

        return FakeEmbeddingResponse(
            [
                [
                    1.0,
                    0.0,
                ],
            ],
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()


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


def create_settings(
    *,
    openai_api_key: SecretStr | None = None,
    configured: bool = True,
) -> Settings:
    resolved_openai_api_key = (
        openai_api_key
        if openai_api_key is not None or not configured
        else SecretStr("test-openai-api-key")
    )

    return Settings(
        _env_file=None,
        app_name="AI Service",
        app_version="0.1.0",
        environment="test",
        internal_api_key=SecretStr("test-internal-api-key"),
        openai_api_key=resolved_openai_api_key,
        openai_model="test-model",
        openai_embedding_model="test-embedding-model",
        openai_prompt_strategy=PromptStrategy.ONE_SHOT,
    )


async def resolve_service(
    *,
    backend: FakeKnowledgeSearchBackend,
    settings: Settings,
) -> KnowledgeSearchService:
    dependency = get_knowledge_search_service(
        backend,
        settings,
    )

    async for service in dependency:
        return service

    raise AssertionError(
        "Dependency did not yield a search service.",
    )


def test_get_knowledge_search_backend_reads_app_state() -> None:
    backend = FakeKnowledgeSearchBackend()
    request = cast(
        Request,
        SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    resources=ApplicationResources(
                        knowledge_search_backend=backend,
                    ),
                ),
            ),
        ),
    )

    assert (
        get_knowledge_search_backend(
            request,
        )
        is backend
    )


def test_get_knowledge_search_backend_rejects_missing_state() -> None:
    request = cast(
        Request,
        SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(),
            ),
        ),
    )

    with pytest.raises(
        KnowledgeStoreUnavailableError,
    ):
        get_knowledge_search_backend(
            request,
        )


@pytest.mark.parametrize(
    "openai_api_key",
    [
        None,
        SecretStr("   "),
    ],
)
def test_knowledge_search_service_rejects_missing_openai_key(
    openai_api_key: SecretStr | None,
) -> None:
    with pytest.raises(
        AIProviderConfigurationError,
    ):
        asyncio.run(
            resolve_service(
                backend=FakeKnowledgeSearchBackend(),
                settings=create_settings(
                    openai_api_key=openai_api_key,
                    configured=openai_api_key is not None,
                ),
            ),
        )


def test_knowledge_search_service_uses_state_backend_without_article_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_loader_call(*_: object) -> object:
        raise AssertionError(
            "knowledge/articles.json must not be loaded by the dependency",
        )

    monkeypatch.setattr(
        dependency_module,
        "load_knowledge_articles",
        fail_loader_call,
        raising=False,
    )
    monkeypatch.setattr(
        dependency_module,
        "AsyncOpenAI",
        FakeAsyncOpenAI,
    )
    FakeAsyncOpenAI.instances = []
    backend = FakeKnowledgeSearchBackend()

    service = asyncio.run(
        resolve_service(
            backend=backend,
            settings=create_settings(),
        ),
    )

    matches = asyncio.run(
        service.search(
            "  consulta de teste  ",
            top_k=2,
        ),
    )

    assert matches == []
    assert service.indexed_articles == 5
    assert backend.received_embeddings == [
        [
            1.0,
            0.0,
        ],
    ]
    assert backend.received_top_k == [
        2,
    ]

    openai_instance = FakeAsyncOpenAI.instances[0]

    assert openai_instance.kwargs["timeout"] == 30.0
    assert openai_instance.kwargs["max_retries"] == 2
    assert openai_instance.closed is True
    assert openai_instance.client.embeddings.calls == [
        {
            "model": "test-embedding-model",
            "input": [
                "consulta de teste",
            ],
            "encoding_format": "float",
        },
    ]
