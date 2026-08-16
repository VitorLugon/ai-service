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
    chunk_index: int | None = Field(
        default=None,
        ge=0,
    )
    chunk_id: RagText | None = None

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

    @model_validator(mode="after")
    def validate_chunk_identity(self) -> "RagSource":
        if (self.chunk_index is None) != (self.chunk_id is None):
            raise ValueError(
                "chunk_index e chunk_id devem ser informados juntos.",
            )

        if self.chunk_id is not None:
            expected_chunk_id = build_rag_chunk_id(
                self.article_id,
                self.chunk_index,
            )

            if self.chunk_id != expected_chunk_id:
                raise ValueError(
                    "chunk_id deve corresponder a article_id e chunk_index.",
                )

        return self


class RagChunk(BaseModel):
    """Trecho determinístico derivado de um artigo de conhecimento."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    article_id: RagText
    title: RagText
    category: TicketCategory
    chunk_index: int = Field(
        ge=0,
    )
    content: RagText
    chunk_id: RagText | None = None

    @model_validator(mode="after")
    def validate_chunk_id(self) -> "RagChunk":
        expected_chunk_id = build_rag_chunk_id(
            self.article_id,
            self.chunk_index,
        )

        if self.chunk_id is None:
            object.__setattr__(
                self,
                "chunk_id",
                expected_chunk_id,
            )
            return self

        if self.chunk_id != expected_chunk_id:
            raise ValueError(
                "chunk_id deve corresponder a article_id e chunk_index.",
            )

        return self


class RankedRagChunk(BaseModel):
    """Chunk recuperado com score e posição de ranking."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    chunk: RagChunk
    score: float = Field(
        ge=-1.0,
        le=1.0,
        allow_inf_nan=False,
    )
    rank: int = Field(
        ge=1,
    )

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


class RagPrompt(BaseModel):
    """Contrato explícito entre augmentation e futura geração RAG."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    system_instructions: RagText
    user_message: RagText


class RagGenerationResult(BaseModel):
    """Resultado textual validado da etapa generativa RAG."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    answer: RagText
    model: RagText


class RagAnswerSource(BaseModel):
    """Fonte controlada pela aplicação retornada com a resposta RAG."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    source_id: RagText
    article_id: RagText
    chunk_id: RagText | None = None
    title: RagText
    category: TicketCategory
    rank: int = Field(
        ge=1,
    )


class RagAnswer(BaseModel):
    """Resposta RAG final com fontes fornecidas à geração."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    answer: RagText
    sources: list[RagAnswerSource]
    source_count: int = Field(
        ge=0,
    )

    @model_validator(mode="after")
    def validate_sources(self) -> "RagAnswer":
        if self.source_count != len(self.sources):
            raise ValueError(
                "source_count deve corresponder à quantidade de sources.",
            )

        source_ids = [source.source_id for source in self.sources]

        if len(source_ids) != len(set(source_ids)):
            raise ValueError(
                "sources não podem conter source_id duplicado.",
            )

        return self


def build_rag_chunk_id(
    article_id: str,
    chunk_index: int | None,
) -> str:
    if chunk_index is None:
        raise ValueError(
            "chunk_index deve ser informado.",
        )

    return f"{article_id}#chunk-{chunk_index:03d}"
