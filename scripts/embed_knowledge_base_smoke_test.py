import asyncio
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.knowledge.loader import load_knowledge_articles
from app.knowledge.text import build_knowledge_article_embedding_text
from app.services.embedding_service import EmbeddingService

DEFAULT_KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")


async def main() -> None:
    """Gera embeddings temporários para a base sintética."""

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

    articles = load_knowledge_articles(DEFAULT_KNOWLEDGE_BASE_PATH)
    embedding_texts = [
        build_knowledge_article_embedding_text(article) for article in articles
    ]

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        service = EmbeddingService(
            client=client,
            model=settings.openai_embedding_model,
        )
        embeddings = await service.embed_texts(embedding_texts)

    dimensions = sorted({len(embedding) for embedding in embeddings})

    if len(articles) != 12:
        raise RuntimeError(
            "A base de conhecimento deve possuir 12 artigos.",
        )

    if len(embeddings) != len(articles):
        raise RuntimeError(
            "A quantidade de embeddings não corresponde aos artigos.",
        )

    if len(dimensions) != 1:
        raise RuntimeError(
            "Os embeddings retornaram dimensões inconsistentes.",
        )

    print(f"Modelo: {settings.openai_embedding_model}")
    print(f"Artigos processados: {len(articles)}")
    print(f"Embeddings gerados: {len(embeddings)}")
    print(f"Dimensões encontradas: {dimensions}")
    print("Base de conhecimento processada com sucesso.")


if __name__ == "__main__":
    asyncio.run(main())
