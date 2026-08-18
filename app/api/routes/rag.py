from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    status,
)

from app.api.dependencies.rag import get_rag_service
from app.core.security import verify_api_key
from app.schemas.errors import ErrorResponse
from app.schemas.knowledge import KnowledgeSearchFilter
from app.schemas.rag import RagAnswerRequest, RagAnswerResponse
from app.services.rag_service import RagService

router = APIRouter(
    prefix="/internal/rag",
    tags=["Internal RAG"],
)


@router.post(
    "/answer",
    response_model=RagAnswerResponse,
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
            "description": "AI provider, configuration or knowledge store unavailable.",
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "model": ErrorResponse,
            "description": "AI provider timed out.",
        },
    },
    summary="Answer a question using the RAG pipeline",
)
async def answer_rag(
    payload: RagAnswerRequest,
    service: Annotated[
        RagService,
        Depends(get_rag_service),
    ],
) -> RagAnswerResponse:
    """Gera resposta RAG fundamentada em fontes recuperadas."""

    answer = await service.answer(
        question=payload.query,
        top_k=payload.top_k,
        search_filter=(
            KnowledgeSearchFilter(
                category=payload.category,
            )
            if payload.category is not None
            else None
        ),
    )

    return RagAnswerResponse.from_answer(
        answer,
    )
