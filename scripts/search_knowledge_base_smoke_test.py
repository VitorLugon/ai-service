import asyncio
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.knowledge.loader import load_knowledge_articles
from app.knowledge.text import (
    build_knowledge_article_embedding_text,
)
from app.knowledge.vector_index import KnowledgeVectorIndex
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_search import KnowledgeSearchService

KNOWLEDGE_BASE_PATH = Path(
    "knowledge/articles.json",
)

QUERY = "Redefini minha senha, mas ainda não consigo entrar na minha conta."

TOP_K = 3


async def main() -> None:
    """Executa uma busca semântica real na base."""

    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY não foi configurada.",
        )

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY está vazia.",
        )

    articles = load_knowledge_articles(
        KNOWLEDGE_BASE_PATH,
    )

    article_texts = [
        build_knowledge_article_embedding_text(
            article,
        )
        for article in articles
    ]

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        embedding_service = EmbeddingService(
            client=client,
            model=settings.openai_embedding_model,
        )

        article_embeddings = await embedding_service.embed_texts(
            article_texts,
        )

        index = KnowledgeVectorIndex(
            articles=articles,
            embeddings=article_embeddings,
        )

        search_service = KnowledgeSearchService(
            embedding_provider=embedding_service,
            index=index,
        )

        results = await search_service.search(
            QUERY,
            top_k=TOP_K,
        )

    print(f"Modelo: {embedding_service.model}")
    print(f"Artigos indexados: {index.size}")
    print(f"Dimensões: {index.dimensions}")
    print(f"Consulta: {QUERY}")
    print("")
    print(f"Top {len(results)} resultados:")

    for position, result in enumerate(
        results,
        start=1,
    ):
        print(f"{position}. {result.article.id} | {result.score:.4f}")
        print(f"   Título: {result.article.title}")
        print(f"   Categoria: {result.article.category.value}")

    expected_article_id = "recover-account-access"

    if results[0].article.id == expected_article_id:
        print("")
        print(
            "Resultado coerente: o artigo de recuperação "
            "de acesso ficou na primeira posição.",
        )
    else:
        print("")
        print(
            "Resultado divergente: revise a consulta, os "
            "artigos e a composição do texto de embedding.",
        )


if __name__ == "__main__":
    asyncio.run(main())
