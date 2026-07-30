from collections import Counter
from pathlib import Path

from app.knowledge.loader import load_knowledge_articles
from app.knowledge.text import build_knowledge_article_embedding_text
from app.schemas.tickets import TicketCategory

DEFAULT_KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")
EXPECTED_ARTICLE_COUNT = 12
EXPECTED_ARTICLES_PER_CATEGORY = 2


def main() -> None:
    """Inspeciona a base de conhecimento sintética."""

    articles = load_knowledge_articles(DEFAULT_KNOWLEDGE_BASE_PATH)
    category_counts = Counter(article.category for article in articles)

    if len(articles) != EXPECTED_ARTICLE_COUNT:
        raise RuntimeError(
            "A base de conhecimento deve possuir exatamente 12 artigos.",
        )

    missing_categories = [
        category for category in TicketCategory if category_counts[category] == 0
    ]

    if missing_categories:
        raise RuntimeError(
            "A base de conhecimento não cobre todas as categorias.",
        )

    invalid_counts = {
        category.value: count
        for category, count in category_counts.items()
        if count != EXPECTED_ARTICLES_PER_CATEGORY
    }

    if invalid_counts:
        raise RuntimeError(
            "Cada categoria deve possuir exatamente 2 artigos.",
        )

    embedding_text_lengths = [
        len(build_knowledge_article_embedding_text(article)) for article in articles
    ]

    print(f"Total de artigos: {len(articles)}")
    print("Artigos por categoria:")

    for category in TicketCategory:
        print(f"- {category.value}: {category_counts[category]}")

    print(f"Menor texto para embedding: {min(embedding_text_lengths)} caracteres")
    print(f"Maior texto para embedding: {max(embedding_text_lengths)} caracteres")
    print("Validação: base de conhecimento sintética válida.")


if __name__ == "__main__":
    main()
