from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.tickets import TicketCategory


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
