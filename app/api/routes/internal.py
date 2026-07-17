from fastapi import APIRouter, Depends, status

from app.core.security import verify_api_key
from app.schemas.internal import InternalPingResponse

router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    dependencies=[Depends(verify_api_key)],
)


@router.get(
    "/ping",
    response_model=InternalPingResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate internal authentication",
)
async def internal_ping() -> InternalPingResponse:
    """Confirma que a autenticação interna foi realizada."""

    return InternalPingResponse(
        status="ok",
        message="Internal authentication succeeded.",
    )