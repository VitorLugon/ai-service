import argparse
import asyncio
from collections.abc import Sequence

import chromadb
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.knowledge.chroma_backend import ChromaKnowledgeSearchBackend
from app.services.embedding_service import EmbeddingService


async def main() -> None:
    """Consulta manualmente a coleção Chroma usando embeddings externos."""

    args = parse_args()
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

    client = chromadb.PersistentClient(
        path=settings.chroma_persist_directory,
    )

    try:
        collection = client.get_collection(
            name=settings.chroma_collection_name,
            embedding_function=None,
        )
    except Exception as error:
        raise RuntimeError(
            "A coleção Chroma não foi encontrada. Execute primeiro "
            "python -m scripts.index_knowledge_base.",
        ) from error

    if collection.count() < 1:
        raise RuntimeError(
            "A coleção Chroma está vazia. Execute primeiro "
            "python -m scripts.index_knowledge_base.",
        )

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as openai_client:
        embedding_service = EmbeddingService(
            client=openai_client,
            model=settings.openai_embedding_model,
        )
        query_embedding = await embedding_service.embed_text(
            args.query,
        )

    backend = ChromaKnowledgeSearchBackend(
        collection,
    )
    matches = backend.search(
        query_embedding,
        top_k=args.top_k,
    )

    print(f"Coleção: {collection.name}")
    print(f"Consulta: {args.query}")
    print(f"Resultados: {len(matches)}")

    for index, match in enumerate(
        matches,
        start=1,
    ):
        print(
            f"{index}. id={match.article.id}; "
            f"título={match.article.title}; "
            f"categoria={match.article.category.value}; "
            f"score={match.score:.4f}"
        )


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta a coleção Chroma persistente da base de conhecimento.",
    )
    parser.add_argument(
        "query",
        help="Texto da consulta semântica.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Quantidade de resultados a retornar.",
    )

    args = parser.parse_args(
        argv,
    )

    if args.top_k < 1:
        parser.error(
            "--top-k deve ser maior que zero.",
        )

    return args


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
