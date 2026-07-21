from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies.ticket_classifier import (
    get_ticket_classifier,
)
from app.core.security import verify_api_key
from app.schemas.errors import ErrorResponse
from app.schemas.tickets import (
    TicketClassificationInput,
    TicketClassificationResponse,
)
from app.services.ticket_classifier import TicketClassifierService

router = APIRouter(
    prefix="/internal/tickets",
    tags=["Tickets"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "/classify",
    response_model=TicketClassificationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
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
    summary="Classify a support ticket",
)
async def classify_ticket(
    ticket: TicketClassificationInput,
    classifier: Annotated[
        TicketClassifierService,
        Depends(get_ticket_classifier),
    ],
) -> TicketClassificationResponse:
    """Classifica um chamado por categoria, prioridade e tags."""

    result = await classifier.classify(ticket)

    return TicketClassificationResponse(
        **result.model_dump(),
        model=classifier.model,
    )
