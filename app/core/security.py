from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings

api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="InternalApiKey",
    description="API key used for communication between internal services.",
    auto_error=False,
)


def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Verifica a chave enviada por um serviço interno."""

    expected_api_key = settings.internal_api_key.get_secret_value()

    if api_key is None or not compare_digest(api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "APIKey"},
        )
