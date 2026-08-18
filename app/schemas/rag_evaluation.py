from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.retrieval_evaluation import RetrievalMetricsAtK

KEBAB_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class RagExpectedBehavior(StrEnum):
    """Comportamento esperado em um caso de avaliação RAG."""

    ANSWER = "answer"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class RagEvaluationCase(BaseModel):
    """Caso sintético de avaliação do pipeline RAG."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    id: str = Field(
        min_length=3,
        max_length=80,
        pattern=KEBAB_ID_PATTERN,
    )
    question: str = Field(
        min_length=1,
        max_length=1000,
    )
    relevant_article_ids: list[str] = Field(
        default_factory=list,
    )
    expected_answer_keywords: list[str] = Field(
        default_factory=list,
    )
    expected_behavior: RagExpectedBehavior
    notes: str | None = None

    @field_validator(
        "question",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: object,
    ) -> object:
        if isinstance(
            value,
            str,
        ):
            return value.strip()

        return value

    @field_validator("relevant_article_ids")
    @classmethod
    def reject_duplicate_relevant_article_ids(
        cls,
        article_ids: list[str],
    ) -> list[str]:
        if len(article_ids) != len(set(article_ids)):
            raise ValueError(
                "Os IDs relevantes não podem conter duplicatas.",
            )

        return article_ids

    @field_validator("expected_answer_keywords")
    @classmethod
    def normalize_expected_answer_keywords(
        cls,
        keywords: list[str],
    ) -> list[str]:
        normalized_keywords: list[str] = []
        seen_keywords: set[str] = set()

        for keyword in keywords:
            normalized_keyword = keyword.strip().casefold()

            if not normalized_keyword:
                raise ValueError(
                    "As keywords esperadas não podem estar vazias.",
                )

            if normalized_keyword in seen_keywords:
                continue

            seen_keywords.add(
                normalized_keyword,
            )
            normalized_keywords.append(
                normalized_keyword,
            )

        return normalized_keywords

    @model_validator(mode="after")
    def validate_behavior_consistency(self) -> Self:
        if self.expected_behavior is RagExpectedBehavior.ANSWER:
            if not self.relevant_article_ids:
                raise ValueError(
                    "Casos com resposta esperada devem possuir artigo relevante.",
                )

            if not self.expected_answer_keywords:
                raise ValueError(
                    "Casos com resposta esperada devem possuir keywords esperadas.",
                )

        if (
            self.expected_behavior is RagExpectedBehavior.INSUFFICIENT_EVIDENCE
            and self.relevant_article_ids
        ):
            raise ValueError(
                "Casos sem evidência não devem possuir artigos relevantes.",
            )

        return self


class RagEvaluationCaseResult(BaseModel):
    """Resultado individual de um caso avaliado no pipeline RAG."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    case_id: str
    expected_behavior: RagExpectedBehavior
    retrieved_article_ids: list[str]
    returned_source_ids: list[str]
    returned_article_ids: list[str]
    answer: str = Field(
        min_length=1,
    )
    retrieval_hit: bool
    source_hit: bool
    answer_keyword_coverage: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    correct_refusal: bool
    false_refusal: bool
    unsupported_answer: bool
    first_relevant_rank: int | None = Field(
        default=None,
        ge=1,
    )
    reciprocal_rank: float = Field(
        ge=0.0,
        le=1.0,
    )


class RagEvaluationReport(BaseModel):
    """Relatório agregado da avaliação RAG determinística."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    total_cases: int = Field(
        ge=1,
    )
    answer_cases: int = Field(
        ge=0,
    )
    insufficient_evidence_cases: int = Field(
        ge=0,
    )
    retrieval_hit_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    source_hit_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    mean_answer_keyword_coverage: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    correct_refusal_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    false_refusal_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    unsupported_answer_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    retrieval_metrics: list[RetrievalMetricsAtK]
    mrr: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    case_results: list[RagEvaluationCaseResult]

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.total_cases != len(self.case_results):
            raise ValueError(
                "total_cases deve corresponder à quantidade de resultados.",
            )

        if self.total_cases != self.answer_cases + self.insufficient_evidence_cases:
            raise ValueError(
                "total_cases deve corresponder à soma dos tipos de caso.",
            )

        return self
