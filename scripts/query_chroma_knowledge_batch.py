import argparse
import asyncio
from collections.abc import Sequence

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.knowledge.chroma_runtime import load_persisted_knowledge_backend
from app.schemas.knowledge import KnowledgeSearchFilter
from app.schemas.tickets import TicketCategory
from app.services.embedding_service import EmbeddingService


async def main() -> None:
    """Consulta manualmente a coleção Chroma em lote."""

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

    backend = load_persisted_knowledge_backend(
        settings,
    )
    queries = [query.strip() for query in args.queries]

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as openai_client:
        embedding_service = EmbeddingService(
            client=openai_client,
            model=settings.openai_embedding_model,
        )
        query_embeddings = await embedding_service.embed_texts(
            queries,
        )

    search_filter = (
        KnowledgeSearchFilter(
            category=args.category,
        )
        if args.category is not None
        else None
    )
    results = backend.search_many(
        query_embeddings,
        top_k=args.top_k,
        search_filter=search_filter,
    )

    print(f"Coleção: {settings.chroma_collection_name}")
    print(f"Modelo: {settings.openai_embedding_model}")
    print(f"Consultas: {len(queries)}")
    print(f"Artigos indexados: {backend.size}")

    for query_index, (query, matches) in enumerate(
        zip(
            queries,
            results,
            strict=True,
        ),
        start=1,
    ):
        print("")
        print(f"Consulta {query_index}: {query}")
        print(f"Resultados: {len(matches)}")

        for match_index, match in enumerate(
            matches,
            start=1,
        ):
            print(
                f"{match_index}. id={match.article.id}; "
                f"título={match.article.title}; "
                f"categoria={match.article.category.value}; "
                f"score={match.score:.4f}"
            )


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta em lote a coleção Chroma persistente.",
    )
    parser.add_argument(
        "queries",
        nargs="+",
        help="Textos das consultas semânticas.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Quantidade de resultados por consulta.",
    )
    parser.add_argument(
        "--category",
        type=TicketCategory,
        choices=list(TicketCategory),
        default=None,
        help="Categoria opcional para filtrar os resultados.",
    )

    args = parser.parse_args(
        argv,
    )

    if args.top_k < 1:
        parser.error(
            "--top-k deve ser maior que zero.",
        )

    args.queries = [query.strip() for query in args.queries]

    if any(not query for query in args.queries):
        parser.error(
            "As consultas não podem estar vazias.",
        )

    return args


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
