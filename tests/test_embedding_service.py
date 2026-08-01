import asyncio
from collections.abc import Sequence
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import openai
import pytest

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
from app.services.embedding_service import EmbeddingService

REQUEST = httpx.Request(
    "POST",
    "https://api.openai.com/v1/embeddings",
)


def create_embedding_item(
    index: int,
    embedding: Sequence[float],
) -> SimpleNamespace:
    return SimpleNamespace(
        index=index,
        embedding=list(embedding),
    )


def create_client_with_response(
    response: SimpleNamespace,
) -> MagicMock:
    client = MagicMock()
    client.embeddings.create = AsyncMock(return_value=response)

    return client


def create_client_with_error(
    error: Exception,
) -> MagicMock:
    client = MagicMock()
    client.embeddings.create = AsyncMock(side_effect=error)

    return client


def test_embedding_service_returns_configured_model() -> None:
    service = EmbeddingService(
        client=MagicMock(),
        model="test-embedding-model",
    )

    assert service.model == "test-embedding-model"


def test_embedding_service_embed_text_returns_vector_and_strips_text() -> None:
    response = SimpleNamespace(
        data=[
            create_embedding_item(0, [0.1, 0.2]),
        ],
    )
    client = create_client_with_response(response)
    service = EmbeddingService(
        client=client,
        model="test-embedding-model",
    )

    embedding = asyncio.run(
        service.embed_text("  Recuperar senha  "),
    )

    assert embedding == [0.1, 0.2]
    client.embeddings.create.assert_awaited_once_with(
        model="test-embedding-model",
        input=["Recuperar senha"],
        encoding_format="float",
    )


def test_embedding_service_embed_texts_preserves_order() -> None:
    response = SimpleNamespace(
        data=[
            create_embedding_item(1, [0.3, 0.4]),
            create_embedding_item(0, [0.1, 0.2]),
        ],
    )
    client = create_client_with_response(response)
    service = EmbeddingService(
        client=client,
        model="test-embedding-model",
    )

    embeddings = asyncio.run(
        service.embed_texts(
            ["Primeiro", "Segundo"],
        ),
    )

    assert embeddings == [
        [0.1, 0.2],
        [0.3, 0.4],
    ]
    client.embeddings.create.assert_awaited_once_with(
        model="test-embedding-model",
        input=["Primeiro", "Segundo"],
        encoding_format="float",
    )


def test_embedding_service_does_not_mutate_original_input() -> None:
    texts = [
        "  Primeiro  ",
        " Segundo ",
    ]
    response = SimpleNamespace(
        data=[
            create_embedding_item(0, [0.1, 0.2]),
            create_embedding_item(1, [0.3, 0.4]),
        ],
    )
    client = create_client_with_response(response)
    service = EmbeddingService(
        client=client,
        model="test-embedding-model",
    )

    asyncio.run(
        service.embed_texts(texts),
    )

    assert texts == [
        "  Primeiro  ",
        " Segundo ",
    ]
    client.embeddings.create.assert_awaited_once_with(
        model="test-embedding-model",
        input=["Primeiro", "Segundo"],
        encoding_format="float",
    )


@pytest.mark.parametrize(
    "texts",
    [
        [],
        [""],
        ["   "],
        ["Texto válido", ""],
        ["Texto válido", "   "],
    ],
)
def test_embedding_service_rejects_invalid_text_batches(
    texts: list[str],
) -> None:
    client = MagicMock()
    client.embeddings.create = AsyncMock()
    service = EmbeddingService(
        client=client,
        model="test-embedding-model",
    )

    with pytest.raises(ValueError):
        asyncio.run(
            service.embed_texts(texts),
        )

    client.embeddings.create.assert_not_called()


def test_embedding_service_rejects_string_as_batch() -> None:
    client = MagicMock()
    client.embeddings.create = AsyncMock()
    service = EmbeddingService(
        client=client,
        model="test-embedding-model",
    )

    with pytest.raises(TypeError, match="embed_text"):
        asyncio.run(
            service.embed_texts("Texto enviado como lote incorreto"),
        )

    client.embeddings.create.assert_not_called()


@pytest.mark.parametrize(
    "response_data",
    [
        [],
        [
            SimpleNamespace(embedding=[0.1, 0.2]),
        ],
        [
            create_embedding_item(0, [0.1, 0.2]),
            create_embedding_item(2, [0.3, 0.4]),
        ],
        [
            create_embedding_item(0, [0.1, 0.2]),
            create_embedding_item(0, [0.3, 0.4]),
        ],
        [
            create_embedding_item(1, [0.1, 0.2]),
        ],
        [
            create_embedding_item(0, [0.1, 0.2]),
        ],
        [
            create_embedding_item(0, []),
            create_embedding_item(1, [0.1, 0.2]),
        ],
        [
            create_embedding_item(0, [0.1, 0.2]),
            create_embedding_item(1, [0.3, 0.4, 0.5]),
        ],
        [
            create_embedding_item(0, [0.1, float("nan")]),
        ],
        [
            create_embedding_item(0, [0.1, float("inf")]),
        ],
        [
            create_embedding_item(0, [0.1, float("-inf")]),
        ],
    ],
)
def test_embedding_service_rejects_invalid_responses(
    response_data: list[SimpleNamespace],
) -> None:
    client = create_client_with_response(
        SimpleNamespace(data=response_data),
    )
    service = EmbeddingService(
        client=client,
        model="test-embedding-model",
    )

    with pytest.raises(AIProviderInvalidResponseError):
        asyncio.run(
            service.embed_texts(
                ["Primeiro", "Segundo"],
            ),
        )


def test_embedding_service_rejects_missing_embedding() -> None:
    client = create_client_with_response(
        SimpleNamespace(
            data=[
                SimpleNamespace(index=0),
            ],
        ),
    )
    service = EmbeddingService(
        client=client,
        model="test-embedding-model",
    )

    with pytest.raises(AIProviderInvalidResponseError):
        asyncio.run(
            service.embed_text("Texto válido"),
        )


@pytest.mark.parametrize(
    ("sdk_error", "application_error"),
    [
        (
            openai.APITimeoutError(request=REQUEST),
            AIProviderTimeoutError,
        ),
        (
            openai.RateLimitError(
                "Rate limit",
                response=httpx.Response(
                    429,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderRateLimitError,
        ),
        (
            openai.AuthenticationError(
                "Invalid API key",
                response=httpx.Response(
                    401,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderConfigurationError,
        ),
        (
            openai.PermissionDeniedError(
                "Permission denied",
                response=httpx.Response(
                    403,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderConfigurationError,
        ),
        (
            openai.NotFoundError(
                "Model not found",
                response=httpx.Response(
                    404,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderConfigurationError,
        ),
        (
            openai.APIConnectionError(request=REQUEST),
            AIProviderConnectionError,
        ),
        (
            openai.InternalServerError(
                "Provider error",
                response=httpx.Response(
                    500,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderUnavailableError,
        ),
        (
            openai.APIStatusError(
                "Unexpected status",
                response=httpx.Response(
                    418,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderRequestError,
        ),
        (
            openai.APIError(
                "Generic API error",
                request=REQUEST,
                body=None,
            ),
            AIProviderRequestError,
        ),
    ],
)
def test_embedding_service_translates_openai_errors(
    sdk_error: Exception,
    application_error: type[AIProviderError],
) -> None:
    client = create_client_with_error(sdk_error)
    service = EmbeddingService(
        client=client,
        model="test-embedding-model",
    )

    with pytest.raises(application_error):
        asyncio.run(
            service.embed_text("Texto válido"),
        )
