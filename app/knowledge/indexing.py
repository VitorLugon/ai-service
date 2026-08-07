import json
from collections.abc import Sequence

from app.knowledge.text import build_knowledge_article_embedding_text
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.knowledge_indexing import (
    KnowledgeIndexMetadata,
    KnowledgeIndexRecord,
)


def build_knowledge_index_record(
    article: KnowledgeArticle,
    *,
    schema_version: int,
    embedding_model: str,
) -> KnowledgeIndexRecord:
    """Converte um artigo em registro determinístico para indexação."""

    return KnowledgeIndexRecord(
        id=article.id,
        document=article.content,
        embedding_text=build_knowledge_article_embedding_text(
            article,
        ),
        metadata=KnowledgeIndexMetadata(
            title=article.title,
            category=article.category.value,
            keywords_json=json.dumps(
                list(article.keywords),
                ensure_ascii=False,
                separators=(
                    ",",
                    ":",
                ),
            ),
            schema_version=schema_version,
            embedding_model=embedding_model,
        ),
    )


def build_knowledge_index_records(
    articles: Sequence[KnowledgeArticle],
    *,
    schema_version: int,
    embedding_model: str,
) -> list[KnowledgeIndexRecord]:
    """Converte artigos em registros preservando a ordem de entrada."""

    if not articles:
        raise ValueError(
            "É necessário informar ao menos um artigo.",
        )

    article_ids = [article.id for article in articles]

    if len(article_ids) != len(set(article_ids)):
        raise ValueError(
            "Os artigos não podem conter IDs duplicados.",
        )

    return [
        build_knowledge_index_record(
            article,
            schema_version=schema_version,
            embedding_model=embedding_model,
        )
        for article in articles
    ]
