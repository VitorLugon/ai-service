from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

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

TicketSummary = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=10,
        max_length=500,
    ),
]

TicketTag = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=40,
    ),
]

SuggestedTags = Annotated[
    list[TicketTag],
    Field(
        min_length=1,
        max_length=3,
        description="Entre uma e três tags curtas relacionadas ao chamado.",
    ),
]


class TicketCategory(StrEnum):
    """Categorias permitidas para um chamado."""

    ACCESS_AND_AUTHENTICATION = "acesso_e_autenticacao"
    TECHNICAL_ERROR = "erro_tecnico"
    BILLING = "cobranca"
    USAGE_QUESTION = "duvida_de_uso"
    REQUEST = "solicitacao"
    OTHER = "outro"


class TicketPriority(StrEnum):
    """Prioridades permitidas para um chamado."""

    LOW = "baixa"
    MEDIUM = "media"
    HIGH = "alta"
    CRITICAL = "critica"


class TicketClassificationInput(BaseModel):
    """Representa os dados de um chamado que será classificado."""

    title: TicketTitle
    description: TicketDescription


class TicketClassificationResult(BaseModel):
    """Representa a classificação estruturada gerada pelo modelo."""

    model_config = ConfigDict(extra="forbid")

    category: TicketCategory = Field(
        description="Categoria que melhor representa o chamado.",
    )
    priority: TicketPriority = Field(
        description="Prioridade determinada pelo impacto do chamado.",
    )
    summary: TicketSummary = Field(
        description="Resumo objetivo do problema em uma única frase.",
    )
    suggested_tags: SuggestedTags


class TicketClassificationResponse(TicketClassificationResult):
    """Resposta HTTP da classificação, incluindo o modelo utilizado."""

    model: str = Field(
        description="Modelo de linguagem utilizado na classificação.",
    )
