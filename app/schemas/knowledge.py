from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.tickets import TicketCategory

MAX_KNOWLEDGE_BATCH_QUERIES = 20


class KnowledgeArticle(BaseModel):
    """Representa um artigo da base de conhecimento."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    id: str = Field(
        min_length=3,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    title: str = Field(
        min_length=5,
        max_length=160,
    )
    content: str = Field(
        min_length=40,
        max_length=4000,
    )
    category: TicketCategory
    keywords: list[str] = Field(
        min_length=1,
        max_length=12,
    )

    @field_validator(
        "title",
        "content",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(
        cls,
        keywords: list[str],
    ) -> list[str]:
        normalized_keywords: list[str] = []
        seen_keywords: set[str] = set()

        for keyword in keywords:
            normalized_keyword = keyword.strip().lower()

            if not normalized_keyword:
                raise ValueError(
                    "As palavras-chave não podem estar vazias.",
                )

            if len(normalized_keyword) > 60:
                raise ValueError(
                    "Cada palavra-chave deve possuir no máximo 60 caracteres.",
                )

            if normalized_keyword in seen_keywords:
                continue

            seen_keywords.add(normalized_keyword)
            normalized_keywords.append(normalized_keyword)

        if not normalized_keywords:
            raise ValueError(
                "O artigo deve possuir ao menos uma palavra-chave.",
            )

        return normalized_keywords


class KnowledgeSearchMatch(BaseModel):
    """Representa um artigo recuperado pela busca semântica."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    article: KnowledgeArticle
    score: float = Field(
        ge=-1.0,
        le=1.0,
    )


class KnowledgeSearchFilter(BaseModel):
    """Filtro de domínio para busca semântica."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    category: TicketCategory | None = None


class KnowledgeSearchRequest(BaseModel):
    """Representa uma solicitação de busca semântica."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=3,
        max_length=1000,
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )
    category: TicketCategory | None = None

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


class KnowledgeSearchResponse(BaseModel):
    """Representa o resultado da busca semântica."""

    model_config = ConfigDict(extra="forbid")

    query: str
    model: str
    indexed_articles: int = Field(ge=1)
    matches: list[KnowledgeSearchMatch]


class KnowledgeBatchSearchRequest(BaseModel):
    """Representa uma solicitação de busca semântica em lote."""

    model_config = ConfigDict(extra="forbid")

    queries: list[str] = Field(
        min_length=1,
        max_length=MAX_KNOWLEDGE_BATCH_QUERIES,
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )
    category: TicketCategory | None = None

    @field_validator(
        "queries",
    )
    @classmethod
    def normalize_queries(cls, value: object) -> object:
        """Remove espaços externos de cada consulta."""

        if isinstance(value, list):
            normalized_queries = [
                item.strip() if isinstance(item, str) else item for item in value
            ]

            for query in normalized_queries:
                if not isinstance(
                    query,
                    str,
                ):
                    continue

                if len(query) < 3 or len(query) > 1000:
                    raise ValueError(
                        "Cada consulta deve possuir entre 3 e 1000 caracteres.",
                    )

            return normalized_queries

        return value


class KnowledgeBatchSearchItem(BaseModel):
    """Resultado de busca para uma consulta do lote."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    query: str = Field(
        min_length=1,
    )
    matches: list[KnowledgeSearchMatch]


class KnowledgeBatchSearchResponse(BaseModel):
    """Representa o resultado da busca semântica em lote."""

    model_config = ConfigDict(extra="forbid")

    model: str
    indexed_articles: int = Field(ge=1)
    results: list[KnowledgeBatchSearchItem] = Field(
        min_length=1,
        max_length=MAX_KNOWLEDGE_BATCH_QUERIES,
    )
