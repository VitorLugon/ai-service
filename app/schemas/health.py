from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Representa a resposta do endpoint de saúde da aplicação."""

    status: Literal["ok"]
    service: str
    version: str
