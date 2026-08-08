from collections.abc import Mapping, Sequence
from pathlib import Path
from types import TracebackType
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.knowledge.chroma_backend import ChromaKnowledgeSearchBackend
from app.knowledge.indexing import build_knowledge_index_record
from app.main import create_application
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory

VALID_DOCUMENT = "Conteúdo sintético suficiente para reconstruir o artigo."
VALID_METADATA = {
    "title": "Como recuperar o acesso à conta",
    "category": "acesso_e_autenticacao",
    "keywords_json": '["senha","login"]',
    "schema_version": 1,
    "embedding_model": "text-embedding-test",
}


class FakeEmbeddingItem:
    def __init__(
        self,
        *,
        index: int,
        embedding: list[float],
    ) -> None:
        self.index = index
        self.embedding = embedding


class FakeEmbeddingResponse:
    def __init__(
        self,
        embeddings: list[list[float]],
    ) -> None:
        self.data = [
            FakeEmbeddingItem(
                index=index,
                embedding=embedding,
            )
            for index, embedding in enumerate(
                embeddings,
            )
        ]


class FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(
        self,
        **kwargs: object,
    ) -> FakeEmbeddingResponse:
        self.calls.append(
            kwargs,
        )
        texts = kwargs["input"]

        assert isinstance(
            texts,
            list,
        )

        embeddings = [
            [
                0.0,
                1.0,
            ]
            if "erro" in text or "técnico" in text
            else [
                1.0,
                0.0,
            ]
            for text in texts
        ]

        return FakeEmbeddingResponse(
            embeddings,
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()


class FakeAsyncOpenAI:
    instances: list["FakeAsyncOpenAI"] = []

    def __init__(
        self,
        **kwargs: object,
    ) -> None:
        self.kwargs = kwargs
        self.client = FakeOpenAIClient()
        self.__class__.instances.append(
            self,
        )

    async def __aenter__(self) -> FakeOpenAIClient:
        return self.client

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class SpyBatchCollection:
    def __init__(self) -> None:
        self.query_calls: list[dict[str, object]] = []

    def count(self) -> int:
        return 12

    def query(
        self,
        *,
        query_embeddings: Sequence[Sequence[float]],
        n_results: int,
        where: dict[str, object] | None = None,
        include: Sequence[str],
    ) -> Mapping[str, object]:
        self.query_calls.append(
            {
                "query_embeddings": [list(embedding) for embedding in query_embeddings],
                "n_results": n_results,
                "where": where,
                "include": list(include),
            },
        )

        return {
            "ids": [
                [
                    "recover-account-access",
                ]
                for _ in query_embeddings
            ],
            "documents": [
                [
                    VALID_DOCUMENT,
                ]
                for _ in query_embeddings
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ]
                for _ in query_embeddings
            ],
            "distances": [
                [
                    0.0,
                ]
                for _ in query_embeddings
            ],
        }


def create_settings(
    tmp_path: Path,
) -> Settings:
    return Settings(
        _env_file=None,
        app_name="AI Service",
        app_version="0.1.0",
        environment="test",
        internal_api_key=SecretStr("test-internal-api-key"),
        openai_api_key=SecretStr("test-openai-api-key"),
        openai_model="test-model",
        openai_embedding_model="text-embedding-test",
        openai_prompt_strategy=PromptStrategy.ONE_SHOT,
        chroma_persist_directory=tmp_path,
        chroma_collection_name="knowledge-batch-api-test",
        chroma_schema_version=1,
    )


def create_article(
    article_id: str,
    *,
    category: TicketCategory,
) -> KnowledgeArticle:
    return KnowledgeArticle(
        id=article_id,
        title=f"Artigo {article_id}",
        content=f"Conteúdo sintético suficiente para validar {article_id}.",
        category=category,
        keywords=[
            "teste",
        ],
    )


def add_article(
    collection: object,
    article: KnowledgeArticle,
    embedding: list[float],
) -> None:
    record = build_knowledge_index_record(
        article,
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    collection.upsert(
        ids=[
            record.id,
        ],
        embeddings=[
            embedding,
        ],
        documents=[
            record.document,
        ],
        metadatas=[
            record.metadata.model_dump(),
        ],
    )


def test_batch_search_endpoint_uses_chroma_backend(
    tmp_path: Path,
) -> None:
    settings = create_settings(
        tmp_path,
    )
    client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name=settings.chroma_collection_name,
        schema_version=settings.chroma_schema_version,
        embedding_model=settings.openai_embedding_model,
    )
    add_article(
        collection,
        create_article(
            "recover-account-access",
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        ),
        [
            1.0,
            0.0,
        ],
    )
    add_article(
        collection,
        create_article(
            "solve-technical-error",
            category=TicketCategory.TECHNICAL_ERROR,
        ),
        [
            0.0,
            1.0,
        ],
    )
    app = create_application(
        settings=settings,
        knowledge_search_backend=ChromaKnowledgeSearchBackend(
            collection,
        ),
    )
    FakeAsyncOpenAI.instances = []

    with patch(
        "app.api.dependencies.knowledge_search.AsyncOpenAI",
        FakeAsyncOpenAI,
    ):
        with TestClient(app) as test_client:
            response = test_client.post(
                "/internal/knowledge/search/batch",
                headers={
                    "X-API-Key": "test-internal-api-key",
                },
                json={
                    "queries": [
                        "não consigo entrar",
                        "erro técnico no sistema",
                    ],
                    "top_k": 1,
                },
            )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()

    assert body["indexed_articles"] == 2
    assert [item["query"] for item in body["results"]] == [
        "não consigo entrar",
        "erro técnico no sistema",
    ]
    assert body["results"][0]["matches"][0]["article"]["id"] == (
        "recover-account-access"
    )
    assert body["results"][1]["matches"][0]["article"]["id"] == (
        "solve-technical-error"
    )
    assert FakeAsyncOpenAI.instances[0].client.embeddings.calls == [
        {
            "model": "text-embedding-test",
            "input": [
                "não consigo entrar",
                "erro técnico no sistema",
            ],
            "encoding_format": "float",
        },
    ]


def test_batch_search_uses_single_embedding_and_vector_query_batch(
    tmp_path: Path,
) -> None:
    collection = SpyBatchCollection()
    settings = create_settings(
        tmp_path,
    )
    app = create_application(
        settings=settings,
        knowledge_search_backend=ChromaKnowledgeSearchBackend(
            collection,
        ),
    )
    queries = [
        f"consulta {index}"
        for index in range(
            10,
        )
    ]
    FakeAsyncOpenAI.instances = []

    with patch(
        "app.api.dependencies.knowledge_search.AsyncOpenAI",
        FakeAsyncOpenAI,
    ):
        with TestClient(app) as test_client:
            response = test_client.post(
                "/internal/knowledge/search/batch",
                headers={
                    "X-API-Key": "test-internal-api-key",
                },
                json={
                    "queries": queries,
                    "top_k": 3,
                    "category": "acesso_e_autenticacao",
                },
            )

    assert response.status_code == status.HTTP_200_OK
    assert len(FakeAsyncOpenAI.instances[0].client.embeddings.calls) == 1
    assert FakeAsyncOpenAI.instances[0].client.embeddings.calls[0]["input"] == queries
    assert len(collection.query_calls) == 1
    assert len(collection.query_calls[0]["query_embeddings"]) == 10
    assert collection.query_calls[0]["where"] == {
        "category": {
            "$eq": "acesso_e_autenticacao",
        },
    }
