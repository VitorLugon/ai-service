from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.schemas.readiness import (
    ReadinessErrorResponse,
    ReadinessResponse,
)
from app.services.readiness import ReadinessService

router = APIRouter(tags=["Readiness"])


def get_readiness_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessService:
    """Cria o serviço responsável pelas verificações de prontidão."""

    return ReadinessService(settings)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessErrorResponse,
            "description": "Service is not ready.",
        },
    },
    summary="Check service readiness",
)
async def readiness_check(
    service: Annotated[
        ReadinessService,
        Depends(get_readiness_service),
    ],
) -> ReadinessResponse | JSONResponse:
    """Verifica se a aplicação está pronta para receber requisições."""

    checks = service.run_checks()

    if not service.is_ready(checks):
        error_response = ReadinessErrorResponse(
            status="not_ready",
            detail="One or more readiness checks failed.",
            checks=checks,
        )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response.model_dump(),
        )

    return ReadinessResponse(
        status="ready",
        checks=checks,
    )
