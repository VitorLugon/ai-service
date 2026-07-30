from app.knowledge.text import build_knowledge_article_embedding_text
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory


def create_article() -> KnowledgeArticle:
    return KnowledgeArticle(
        id="recover-account-access",
        title="Como recuperar o acesso",
        content="Texto sintético suficientemente longo para validar o artigo.",
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        keywords=["senha", "login"],
    )


def test_build_knowledge_article_embedding_text_uses_expected_format() -> None:
    article = create_article()

    text = build_knowledge_article_embedding_text(article)

    assert text == (
        "Título: Como recuperar o acesso\n"
        "Categoria: acesso_e_autenticacao\n"
        "Palavras-chave: senha, login\n"
        "Conteúdo: Texto sintético suficientemente longo para validar o artigo."
    )


def test_build_knowledge_article_embedding_text_uses_stable_field_order() -> None:
    text = build_knowledge_article_embedding_text(create_article())

    assert text.splitlines() == [
        "Título: Como recuperar o acesso",
        "Categoria: acesso_e_autenticacao",
        "Palavras-chave: senha, login",
        "Conteúdo: Texto sintético suficientemente longo para validar o artigo.",
    ]


def test_build_knowledge_article_embedding_text_includes_searchable_fields() -> None:
    text = build_knowledge_article_embedding_text(create_article())

    assert "Como recuperar o acesso" in text
    assert "acesso_e_autenticacao" in text
    assert "senha, login" in text
    assert "Texto sintético suficientemente longo" in text


def test_build_knowledge_article_embedding_text_omits_technical_id() -> None:
    text = build_knowledge_article_embedding_text(create_article())

    assert "recover-account-access" not in text


def test_build_knowledge_article_embedding_text_is_deterministic() -> None:
    article = create_article()

    assert build_knowledge_article_embedding_text(
        article,
    ) == build_knowledge_article_embedding_text(article)
