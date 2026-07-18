from typing import Literal

from pydantic import BaseModel


class InternalPingResponse(BaseModel):
    """Representa a resposta de uma rota interna autenticada."""

    status: Literal["ok"]
    message: str
