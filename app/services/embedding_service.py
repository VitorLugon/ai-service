from collections.abc import Sequence
from math import isfinite

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from app.core.exceptions import (
    AIProviderConfigurationError,
    AIProviderConnectionError,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderRequestError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)


class EmbeddingService:
    """Gera e valida embeddings usando a OpenAI."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
    ) -> None:
        self._client = client
        self._model = model

    @property
    def model(self) -> str:
        """Retorna o modelo de embeddings configurado."""

        return self._model

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        """Gera o embedding de um único texto."""

        embeddings = await self.embed_texts([text])

        return embeddings[0]

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Gera embeddings em lote preservando a ordem."""

        if isinstance(texts, str):
            raise TypeError(
                "Use embed_text para enviar um único texto.",
            )

        normalized_texts = [text.strip() for text in texts]

        if not normalized_texts:
            raise ValueError(
                "É necessário informar ao menos um texto.",
            )

        if any(not text for text in normalized_texts):
            raise ValueError(
                "Os textos não podem estar vazios.",
            )

        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=normalized_texts,
                encoding_format="float",
            )
        except APITimeoutError as error:
            raise AIProviderTimeoutError() from error
        except RateLimitError as error:
            raise AIProviderRateLimitError() from error
        except (
            AuthenticationError,
            PermissionDeniedError,
            NotFoundError,
        ) as error:
            raise AIProviderConfigurationError() from error
        except APIConnectionError as error:
            raise AIProviderConnectionError() from error
        except InternalServerError as error:
            raise AIProviderUnavailableError() from error
        except (APIStatusError, APIError) as error:
            raise AIProviderRequestError() from error

        try:
            ordered_items = sorted(
                response.data,
                key=lambda item: item.index,
            )
        except AttributeError as error:
            raise AIProviderInvalidResponseError() from error

        expected_indices = list(
            range(len(normalized_texts)),
        )
        received_indices = [item.index for item in ordered_items]

        if received_indices != expected_indices:
            raise AIProviderInvalidResponseError()

        try:
            embeddings = [list(item.embedding) for item in ordered_items]
        except AttributeError as error:
            raise AIProviderInvalidResponseError() from error

        if len(embeddings) != len(normalized_texts):
            raise AIProviderInvalidResponseError()

        if any(not embedding for embedding in embeddings):
            raise AIProviderInvalidResponseError()

        dimensions = {len(embedding) for embedding in embeddings}

        if len(dimensions) != 1:
            raise AIProviderInvalidResponseError()

        if any(not isfinite(value) for embedding in embeddings for value in embedding):
            raise AIProviderInvalidResponseError()

        return embeddings
