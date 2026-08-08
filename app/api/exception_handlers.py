from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AIProviderConfigurationError,
    AIProviderConnectionError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    KnowledgeStoreError,
)
from app.schemas.errors import ErrorResponse


def get_provider_error_status_code(
    error: AIProviderError,
) -> int:
    """Converte uma falha do provedor em um código HTTP."""

    if isinstance(error, AIProviderTimeoutError):
        return status.HTTP_504_GATEWAY_TIMEOUT

    if isinstance(
        error,
        (
            AIProviderConfigurationError,
            AIProviderConnectionError,
            AIProviderRateLimitError,
            AIProviderUnavailableError,
        ),
    ):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    return status.HTTP_502_BAD_GATEWAY


async def ai_provider_error_handler(
    _: Request,
    error: Exception,
) -> JSONResponse:
    """Transforma falhas do provedor em respostas HTTP seguras."""

    provider_error = cast(AIProviderError, error)

    headers: dict[str, str] | None = None

    if isinstance(provider_error, AIProviderRateLimitError):
        headers = {"Retry-After": "30"}

    response = ErrorResponse(
        code=provider_error.code,
        detail=provider_error.public_message,
        retryable=provider_error.retryable,
    )

    return JSONResponse(
        status_code=get_provider_error_status_code(
            provider_error,
        ),
        content=response.model_dump(),
        headers=headers,
    )


async def knowledge_store_error_handler(
    _: Request,
    error: Exception,
) -> JSONResponse:
    """Transforma falhas do Chroma em respostas HTTP seguras."""

    store_error = cast(KnowledgeStoreError, error)
    response = ErrorResponse(
        code=store_error.code,
        detail=store_error.public_message,
        retryable=store_error.retryable,
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )


def register_exception_handlers(
    application: FastAPI,
) -> None:
    """Registra os handlers globais da aplicação."""

    application.add_exception_handler(
        AIProviderError,
        ai_provider_error_handler,
    )
    application.add_exception_handler(
        KnowledgeStoreError,
        knowledge_store_error_handler,
    )
