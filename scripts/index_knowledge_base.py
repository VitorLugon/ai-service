import asyncio
from decimal import Decimal
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.knowledge.indexing import build_knowledge_index_records
from app.knowledge.loader import load_knowledge_articles
from app.services.embedding_cost import (
    count_embedding_tokens,
    estimate_embedding_cost_usd,
)
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_indexer import KnowledgeIndexer

KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")


async def main() -> None:
    """Indexa a base de conhecimento no Chroma local persistente."""

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
    records = build_knowledge_index_records(
        articles,
        schema_version=settings.chroma_schema_version,
        embedding_model=settings.openai_embedding_model,
    )
    embedding_texts = [record.embedding_text for record in records]
    token_count = count_embedding_tokens(
        embedding_texts,
        model=settings.openai_embedding_model,
    )
    estimated_cost = estimate_embedding_cost_usd(
        token_count,
        cost_per_million_tokens_usd=(
            settings.openai_embedding_cost_per_million_tokens_usd
        ),
    )

    client = create_persistent_chroma_client(
        settings.chroma_persist_directory,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name=settings.chroma_collection_name,
        schema_version=settings.chroma_schema_version,
        embedding_model=settings.openai_embedding_model,
    )

    print(f"Modelo de embeddings: {settings.openai_embedding_model}")
    print(f"Artigos planejados: {len(records)}")
    print(f"Tokens estimados: {token_count}")
    print(f"Custo estimado em USD: {_format_decimal(estimated_cost)}")
    print(f"Coleção: {collection.name}")
    print(f"Registros antes: {collection.count()}")

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as openai_client:
        embedding_service = EmbeddingService(
            client=openai_client,
            model=settings.openai_embedding_model,
        )
        indexer = KnowledgeIndexer(
            embedding_provider=embedding_service,
            collection=collection,
            schema_version=settings.chroma_schema_version,
        )
        result = await indexer.index(
            articles,
        )

    print(f"Artigos indexados: {result.indexed_articles}")
    print(f"Dimensões dos embeddings: {result.embedding_dimensions}")
    print(f"Registros depois: {result.records_after}")
    print("Base de conhecimento indexada com sucesso.")


def _format_decimal(
    value: Decimal,
) -> str:
    return format(
        value,
        "f",
    )


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
