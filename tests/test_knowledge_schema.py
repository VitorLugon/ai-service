import pytest
from pydantic import ValidationError

from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory


def create_article(
    *,
    article_id: str = "recover-account-access",
    title: str = "Como recuperar o acesso",
    content: str = "Texto sintético suficientemente longo para validar o artigo.",
    category: TicketCategory | str = TicketCategory.ACCESS_AND_AUTHENTICATION,
    keywords: list[str] | None = None,
    extra_fields: dict[str, object] | None = None,
) -> KnowledgeArticle:
    data: dict[str, object] = {
        "id": article_id,
        "title": title,
        "content": content,
        "category": category,
        "keywords": keywords if keywords is not None else ["senha", "login"],
    }

    if extra_fields is not None:
        data.update(extra_fields)

    return KnowledgeArticle.model_validate(data)


def test_knowledge_article_accepts_valid_data() -> None:
    article = create_article()

    assert article.id == "recover-account-access"
    assert article.category is TicketCategory.ACCESS_AND_AUTHENTICATION
    assert article.keywords == ["senha", "login"]


def test_knowledge_article_normalizes_keywords() -> None:
    article = create_article(
        keywords=[
            " Senha ",
            "LOGIN",
            "senha",
            " Recuperação de Acesso ",
        ],
    )

    assert article.keywords == ["senha", "login", "recuperação de acesso"]


def test_knowledge_article_normalizes_title_and_content() -> None:
    article = create_article(
        title="  Como configurar MFA  ",
        content="  Conteúdo sintético suficientemente longo para validação.  ",
    )

    assert article.title == "Como configurar MFA"
    assert article.content == "Conteúdo sintético suficientemente longo para validação."


@pytest.mark.parametrize(
    "article_id",
    [
        "id com espaco",
        "id_com_underscore",
        "Id-Com-Maiuscula",
        "-invalid-start",
        "invalid-end-",
    ],
)
def test_knowledge_article_rejects_invalid_ids(article_id: str) -> None:
    with pytest.raises(ValidationError):
        create_article(article_id=article_id)


def test_knowledge_article_rejects_empty_keyword() -> None:
    with pytest.raises(ValidationError, match="não podem estar vazias"):
        create_article(keywords=["senha", " "])


def test_knowledge_article_rejects_empty_keyword_list() -> None:
    with pytest.raises(ValidationError):
        create_article(keywords=[])


def test_knowledge_article_rejects_long_keyword() -> None:
    with pytest.raises(ValidationError, match="60 caracteres"):
        create_article(keywords=["x" * 61])


def test_knowledge_article_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        create_article(extra_fields={"source": "manual"})


def test_knowledge_article_rejects_invalid_category() -> None:
    with pytest.raises(ValidationError):
        create_article(category="categoria_inexistente")


def test_knowledge_article_is_frozen() -> None:
    article = create_article()

    with pytest.raises(ValidationError):
        article.title = "Novo título"
