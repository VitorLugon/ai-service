import json
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.knowledge.loader import load_knowledge_articles
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory


def raw_article(
    article_id: str = "recover-account-access",
) -> dict[str, object]:
    return {
        "id": article_id,
        "title": "Como recuperar o acesso",
        "content": "Texto sintético suficientemente longo para validar o artigo.",
        "category": TicketCategory.ACCESS_AND_AUTHENTICATION.value,
        "keywords": ["senha", "login"],
    }


def write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_load_knowledge_articles_returns_valid_articles(tmp_path: Path) -> None:
    path = tmp_path / "articles.json"
    write_json(
        path,
        [
            raw_article("recover-account-access"),
            {
                **raw_article("payment-approved-account-suspended"),
                "category": TicketCategory.BILLING.value,
            },
        ],
    )

    articles = load_knowledge_articles(path)

    assert len(articles) == 2
    assert all(isinstance(article, KnowledgeArticle) for article in articles)
    assert articles[0].category is TicketCategory.ACCESS_AND_AUTHENTICATION
    assert articles[1].category is TicketCategory.BILLING


def test_load_knowledge_articles_rejects_empty_base(tmp_path: Path) -> None:
    path = tmp_path / "articles.json"
    write_json(path, [])

    with pytest.raises(ValueError, match="não pode estar vazia"):
        load_knowledge_articles(path)


def test_load_knowledge_articles_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "articles.json"
    write_json(
        path,
        [
            raw_article("duplicated-id"),
            raw_article("duplicated-id"),
        ],
    )

    with pytest.raises(ValueError, match="IDs duplicados"):
        load_knowledge_articles(path)


def test_load_knowledge_articles_rejects_invalid_category(tmp_path: Path) -> None:
    path = tmp_path / "articles.json"
    write_json(
        path,
        [
            {
                **raw_article(),
                "category": "categoria_inexistente",
            },
        ],
    )

    with pytest.raises(ValidationError):
        load_knowledge_articles(path)


def test_load_knowledge_articles_rejects_invalid_schema(tmp_path: Path) -> None:
    path = tmp_path / "articles.json"
    article = raw_article()
    article.pop("title")
    write_json(path, [article])

    with pytest.raises(ValidationError):
        load_knowledge_articles(path)


def test_load_knowledge_articles_preserves_json_error(tmp_path: Path) -> None:
    path = tmp_path / "articles.json"
    path.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_knowledge_articles(path)


def test_load_knowledge_articles_preserves_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_knowledge_articles(Path("missing-knowledge-base.json"))


def test_repository_knowledge_base_is_valid() -> None:
    project_root = Path(__file__).resolve().parents[1]
    path = project_root / "knowledge" / "articles.json"

    articles = load_knowledge_articles(path)
    article_ids = [article.id for article in articles]
    category_counts = Counter(article.category for article in articles)

    assert len(articles) == 12
    assert len(article_ids) == len(set(article_ids))
    assert set(category_counts) == set(TicketCategory)

    for category in TicketCategory:
        assert category_counts[category] == 2
