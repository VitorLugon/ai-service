from typing import Literal

from pydantic import BaseModel


class ReadinessCheck(BaseModel):
    """Representa o resultado de uma verificação de prontidão."""

    name: str
    status: Literal["ok", "error"]


class ReadinessResponse(BaseModel):
    """Representa a resposta de um serviço pronto."""

    status: Literal["ready"]
    checks: list[ReadinessCheck]


class ReadinessErrorResponse(BaseModel):
    """Representa a resposta de um serviço que não está pronto."""

    status: Literal["not_ready"]
    detail: str
    checks: list[ReadinessCheck]