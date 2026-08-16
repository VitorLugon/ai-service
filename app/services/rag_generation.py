from typing import Protocol

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from app.core.exceptions import (
    AIProviderConfigurationError,
    AIProviderConnectionError,
    AIProviderIncompleteResponseError,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderRequestError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.schemas.rag import RagGenerationResult, RagPrompt

MIN_RAG_MAX_OUTPUT_TOKENS = 100
MAX_RAG_MAX_OUTPUT_TOKENS = 4_000


class ResponsesResource(Protocol):
    """Parte da Responses API usada pela geração RAG."""

    async def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
        max_output_tokens: int,
        store: bool,
    ) -> object:
        """Cria uma resposta textual no provider."""


class ResponsesClient(Protocol):
    """Cliente com recurso de Responses API injetado no serviço."""

    responses: ResponsesResource


class RagGenerationService:
    """Gera respostas RAG a partir de um prompt já montado."""

    def __init__(
        self,
        *,
        client: ResponsesClient,
        model: str,
        max_output_tokens: int,
    ) -> None:
        normalized_model = model.strip()

        if not normalized_model:
            raise ValueError(
                "model não pode estar vazio.",
            )

        if (
            max_output_tokens < MIN_RAG_MAX_OUTPUT_TOKENS
            or max_output_tokens > MAX_RAG_MAX_OUTPUT_TOKENS
        ):
            raise ValueError(
                "max_output_tokens deve estar entre 100 e 4000.",
            )

        self._client = client
        self._model = normalized_model
        self._max_output_tokens = max_output_tokens

    @property
    def model(self) -> str:
        """Retorna o modelo generativo RAG configurado."""

        return self._model

    async def generate(
        self,
        prompt: RagPrompt,
    ) -> RagGenerationResult:
        """Envia o prompt ao provider e retorna resposta validada."""

        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=prompt.system_instructions,
                input=prompt.user_message,
                max_output_tokens=self._max_output_tokens,
                store=False,
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

        _validate_response_status(
            response,
        )
        answer = _extract_output_text(
            response,
        )

        return RagGenerationResult(
            answer=answer,
            model=self._model,
        )


def _validate_response_status(
    response: object,
) -> None:
    status = getattr(
        response,
        "status",
        None,
    )

    if status is None or status == "completed":
        return

    if status == "incomplete":
        raise AIProviderIncompleteResponseError()

    raise AIProviderInvalidResponseError()


def _extract_output_text(
    response: object,
) -> str:
    output_text = getattr(
        response,
        "output_text",
        None,
    )

    if not isinstance(
        output_text,
        str,
    ):
        raise AIProviderInvalidResponseError()

    normalized_output_text = output_text.strip()

    if not normalized_output_text:
        raise AIProviderInvalidResponseError()

    return normalized_output_text
