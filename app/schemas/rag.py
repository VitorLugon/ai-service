from math import isfinite
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.tickets import TicketCategory

RagText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]


class RagSource(BaseModel):
    """Fonte recuperada usada para montar o contexto RAG."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    article_id: RagText
    title: RagText
    category: TicketCategory
    score: float = Field(
        ge=-1.0,
        le=1.0,
        allow_inf_nan=False,
    )
    rank: int = Field(
        ge=1,
    )
    content: RagText

    @field_validator("score")
    @classmethod
    def reject_non_finite_score(
        cls,
        value: float,
    ) -> float:
        if not isfinite(value):
            raise ValueError(
                "O score deve ser finito.",
            )

        return value


class RagContext(BaseModel):
    """Contexto preparado para uma futura etapa generativa."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    text: str
    sources: list[RagSource]
    source_count: int = Field(
        ge=0,
    )

    @model_validator(mode="after")
    def validate_source_count(self) -> "RagContext":
        if self.source_count != len(self.sources):
            raise ValueError(
                "source_count deve corresponder à quantidade de sources.",
            )

        return self
