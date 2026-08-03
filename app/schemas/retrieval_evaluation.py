from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

KEBAB_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
KebabId = Annotated[
    str,
    Field(
        min_length=3,
        max_length=80,
        pattern=KEBAB_ID_PATTERN,
    ),
]


class RetrievalEvaluationCase(BaseModel):
    """Representa uma consulta com seus artigos relevantes."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    id: KebabId
    query: str = Field(
        min_length=1,
        max_length=1000,
    )
    relevant_article_ids: list[KebabId] = Field(
        min_length=1,
    )

    @field_validator(
        "query",
        mode="before",
    )
    @classmethod
    def normalize_query(cls, value: object) -> object:
        """Remove espaços externos da consulta."""

        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("relevant_article_ids")
    @classmethod
    def reject_duplicate_relevant_article_ids(
        cls,
        article_ids: list[str],
    ) -> list[str]:
        """Rejeita IDs relevantes duplicados sem alterar a ordem."""

        if len(article_ids) != len(set(article_ids)):
            raise ValueError(
                "Os IDs relevantes não podem conter duplicatas.",
            )

        return article_ids


class RetrievalCaseResult(BaseModel):
    """Representa o resultado individual de uma consulta avaliada."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    case_id: str
    query: str
    relevant_article_ids: list[str]
    retrieved_article_ids: list[str]
    first_relevant_rank: int | None = Field(
        default=None,
        ge=1,
    )
    reciprocal_rank: float = Field(
        ge=0.0,
        le=1.0,
    )


class RetrievalMetricsAtK(BaseModel):
    """Representa métricas agregadas em um valor de k."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    k: int = Field(ge=1)
    hit_rate: float = Field(
        ge=0.0,
        le=1.0,
    )
    mean_recall: float = Field(
        ge=0.0,
        le=1.0,
    )


class RetrievalEvaluationReport(BaseModel):
    """Representa o relatório agregado da avaliação de recuperação."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    model: str
    total_cases: int = Field(ge=1)
    indexed_articles: int = Field(ge=1)
    metrics: list[RetrievalMetricsAtK] = Field(
        min_length=1,
    )
    mrr: float = Field(
        ge=0.0,
        le=1.0,
    )
    cases: list[RetrievalCaseResult]

    @model_validator(mode="after")
    def validate_case_count(self) -> Self:
        """Garante que o total informado corresponda aos resultados."""

        if len(self.cases) != self.total_cases:
            raise ValueError(
                "A quantidade de resultados deve corresponder ao total de casos.",
            )

        return self
