from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    status,
)

from app.api.dependencies.knowledge_search import (
    get_knowledge_batch_search_service,
    get_knowledge_search_service,
)
from app.core.security import verify_api_key
from app.schemas.errors import ErrorResponse
from app.schemas.knowledge import (
    KnowledgeBatchSearchRequest,
    KnowledgeBatchSearchResponse,
    KnowledgeSearchFilter,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge_batch_search import KnowledgeBatchSearchService
from app.services.knowledge_search import (
    KnowledgeSearchService,
)

router = APIRouter(
    prefix="/internal/knowledge",
    tags=["Internal Knowledge"],
)


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(verify_api_key),
    ],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Invalid or missing internal API key.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "AI provider returned an invalid response.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "AI provider is unavailable or not configured.",
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "model": ErrorResponse,
            "description": "AI provider timed out.",
        },
    },
    summary="Search the knowledge base semantically",
)
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    service: Annotated[
        KnowledgeSearchService,
        Depends(get_knowledge_search_service),
    ],
) -> KnowledgeSearchResponse:
    """Busca artigos semanticamente relacionados."""

    matches = await service.search(
        payload.query,
        top_k=payload.top_k,
        search_filter=(
            KnowledgeSearchFilter(
                category=payload.category,
            )
            if payload.category is not None
            else None
        ),
    )

    return KnowledgeSearchResponse(
        query=payload.query,
        model=service.model,
        indexed_articles=service.indexed_articles,
        matches=matches,
    )


@router.post(
    "/search/batch",
    response_model=KnowledgeBatchSearchResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(verify_api_key),
    ],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Invalid or missing internal API key.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "AI provider returned an invalid response.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "AI provider is unavailable or not configured.",
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "model": ErrorResponse,
            "description": "AI provider timed out.",
        },
    },
    summary="Search the knowledge base semantically in batch",
)
async def search_knowledge_batch(
    payload: KnowledgeBatchSearchRequest,
    service: Annotated[
        KnowledgeBatchSearchService,
        Depends(get_knowledge_batch_search_service),
    ],
) -> KnowledgeBatchSearchResponse:
    """Busca artigos semanticamente relacionados para várias consultas."""

    return await service.search_many(
        payload.queries,
        top_k=payload.top_k,
        search_filter=(
            KnowledgeSearchFilter(
                category=payload.category,
            )
            if payload.category is not None
            else None
        ),
    )
