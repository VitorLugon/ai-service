import json
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas.knowledge import KnowledgeArticle

_knowledge_articles_adapter = TypeAdapter(
    list[KnowledgeArticle],
)


def load_knowledge_articles(
    path: Path,
) -> list[KnowledgeArticle]:
    """Carrega e valida artigos da base de conhecimento."""

    raw_content = path.read_text(encoding="utf-8")
    raw_articles = json.loads(raw_content)

    articles = _knowledge_articles_adapter.validate_python(
        raw_articles,
    )

    if not articles:
        raise ValueError(
            "A base de conhecimento não pode estar vazia.",
        )

    article_ids = [article.id for article in articles]

    if len(article_ids) != len(set(article_ids)):
        raise ValueError(
            "A base de conhecimento contém IDs duplicados.",
        )

    return articles
