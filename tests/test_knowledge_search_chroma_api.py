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

        return FakeEmbeddingResponse(
            [
                [
                    1.0,
                    0.0,
                ]
                for _ in texts
            ],
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


class SpyChromaCollection:
    def __init__(self) -> None:
        self.query_calls: list[dict[str, object]] = []
        self.upsert_calls: list[dict[str, object]] = []

    def count(self) -> int:
        return 3

    def upsert(
        self,
        **kwargs: object,
    ) -> None:
        self.upsert_calls.append(
            kwargs,
        )

    def query(
        self,
        *,
        query_embeddings: Sequence[Sequence[float]],
        n_results: int,
        include: Sequence[str],
    ) -> Mapping[str, object]:
        self.query_calls.append(
            {
                "query_embeddings": query_embeddings,
                "n_results": n_results,
                "include": include,
            },
        )

        return {
            "ids": [
                [
                    "recover-account-access",
                ],
            ],
            "documents": [
                [
                    VALID_DOCUMENT,
                ],
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ],
            ],
            "distances": [
                [
                    0.0,
                ],
            ],
        }


def create_settings(
    tmp_path: Path,
    *,
    collection_name: str = "knowledge-api-chroma-test",
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
        chroma_collection_name=collection_name,
        chroma_schema_version=1,
    )


def create_article(
    article_id: str,
    *,
    title: str,
    category: TicketCategory,
    keywords: list[str],
) -> KnowledgeArticle:
    return KnowledgeArticle(
        id=article_id,
        title=title,
        content=f"Conteúdo sintético suficiente para o artigo {article_id}.",
        category=category,
        keywords=keywords,
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


def test_knowledge_search_endpoint_uses_chroma_backend(
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
            title="Como recuperar o acesso à conta",
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
            keywords=[
                "senha",
                "login",
            ],
        ),
        [
            1.0,
            0.0,
        ],
    )
    add_article(
        collection,
        create_article(
            "configure-multi-factor-authentication",
            title="Como configurar autenticação em dois fatores",
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
            keywords=[
                "mfa",
                "segurança",
            ],
        ),
        [
            0.8,
            0.2,
        ],
    )
    add_article(
        collection,
        create_article(
            "identify-unsupported-request",
            title="Como tratar uma solicitação não suportada",
            category=TicketCategory.OTHER,
            keywords=[
                "triagem",
            ],
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
                "/internal/knowledge/search",
                headers={
                    "X-API-Key": "test-internal-api-key",
                },
                json={
                    "query": "  Redefini minha senha, mas ainda não consigo entrar  ",
                    "top_k": 2,
                },
            )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()

    assert body["query"] == "Redefini minha senha, mas ainda não consigo entrar"
    assert body["model"] == "text-embedding-test"
    assert body["indexed_articles"] == 3
    assert len(body["matches"]) == 2
    assert body["matches"][0]["article"]["id"] == "recover-account-access"
    assert FakeAsyncOpenAI.instances[0].client.embeddings.calls == [
        {
            "model": "text-embedding-test",
            "input": [
                "Redefini minha senha, mas ainda não consigo entrar",
            ],
            "encoding_format": "float",
        },
    ]


def test_search_request_embeds_only_the_query(
    tmp_path: Path,
) -> None:
    collection = SpyChromaCollection()
    settings = create_settings(
        tmp_path,
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
                "/internal/knowledge/search",
                headers={
                    "X-API-Key": "test-internal-api-key",
                },
                json={
                    "query": "Recuperar senha",
                    "top_k": 1,
                },
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["indexed_articles"] == 3
    assert FakeAsyncOpenAI.instances[0].client.embeddings.calls == [
        {
            "model": "text-embedding-test",
            "input": [
                "Recuperar senha",
            ],
            "encoding_format": "float",
        },
    ]
    assert collection.query_calls == [
        {
            "query_embeddings": [
                [
                    1.0,
                    0.0,
                ],
            ],
            "n_results": 1,
            "include": [
                "documents",
                "metadatas",
                "distances",
            ],
        },
    ]
    assert collection.upsert_calls == []
