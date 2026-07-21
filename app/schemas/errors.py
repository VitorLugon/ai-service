from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Representa uma falha previsível da aplicação."""

    code: str
    detail: str
    retryable: bool
