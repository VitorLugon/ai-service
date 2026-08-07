from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeIndexMetadata(BaseModel):
    """Metadata persistida junto aos documentos no Chroma."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    title: str = Field(
        min_length=1,
        max_length=160,
    )
    category: str = Field(
        min_length=1,
    )
    keywords_json: str = Field(
        min_length=2,
    )
    schema_version: int = Field(
        ge=1,
    )
    embedding_model: str = Field(
        min_length=1,
    )

    @field_validator(
        "title",
        "category",
        "keywords_json",
        "embedding_model",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class KnowledgeIndexRecord(BaseModel):
    """Representa um artigo preparado para indexação vetorial."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    id: str = Field(
        min_length=3,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    document: str = Field(
        min_length=1,
    )
    embedding_text: str = Field(
        min_length=1,
    )
    metadata: KnowledgeIndexMetadata


class KnowledgeIndexingResult(BaseModel):
    """Resumo de uma execução de indexação no Chroma."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    indexed_articles: int = Field(
        ge=1,
    )
    collection_name: str = Field(
        min_length=1,
    )
    records_before: int = Field(
        ge=0,
    )
    records_after: int = Field(
        ge=0,
    )
    embedding_dimensions: int = Field(
        ge=1,
    )
