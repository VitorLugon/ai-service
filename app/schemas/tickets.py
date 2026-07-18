from typing import Annotated

from pydantic import BaseModel, StringConstraints

TicketTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=200,
    ),
]

TicketDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=10,
        max_length=5000,
    ),
]


class TicketClassificationInput(BaseModel):
    """Representa os dados de um chamado que será classificado."""

    title: TicketTitle
    description: TicketDescription


class TicketClassificationDraft(BaseModel):
    """Representa a resposta textual inicial do classificador."""

    model: str
    raw_output: str
