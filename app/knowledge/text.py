from app.schemas.knowledge import KnowledgeArticle


def build_knowledge_article_embedding_text(
    article: KnowledgeArticle,
) -> str:
    """Cria uma representação textual estável para embeddings."""

    keywords = ", ".join(article.keywords)

    return (
        f"Título: {article.title}\n"
        f"Categoria: {article.category.value}\n"
        f"Palavras-chave: {keywords}\n"
        f"Conteúdo: {article.content}"
    )
