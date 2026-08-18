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


class FakeResponse:
    status = "completed"
    output_text = "Use a recuperação de senha e confirme o e-mail recebido."


class FakeResponsesResource:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(
        self,
        **kwargs: object,
    ) -> FakeResponse:
        self.calls.append(
            kwargs,
        )
        return FakeResponse()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()
        self.responses = FakeResponsesResource()


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
        return 2

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
                "query_embeddings": query_embeddings,
                "n_results": n_results,
                "where": where,
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
                    (
                        "Use a recuperação de senha e aguarde o e-mail de "
                        "confirmação antes de tentar acessar novamente."
                    ),
                ],
            ],
            "metadatas": [
                [
                    {
                        "title": "Como recuperar o acesso à conta",
                        "category": "acesso_e_autenticacao",
                        "keywords_json": '["senha","login"]',
                        "schema_version": 1,
                        "embedding_model": "text-embedding-test",
                    },
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
) -> Settings:
    return Settings(
        _env_file=None,
        app_name="AI Service",
        app_version="0.1.0",
        environment="test",
        internal_api_key=SecretStr("test-internal-api-key"),
        openai_api_key=SecretStr("test-openai-api-key"),
        openai_model="test-model",
        openai_rag_model="test-rag-model",
        openai_embedding_model="text-embedding-test",
        openai_prompt_strategy=PromptStrategy.ONE_SHOT,
        chroma_persist_directory=tmp_path,
        chroma_collection_name="rag-api-chroma-test",
        chroma_schema_version=1,
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


def test_rag_endpoint_uses_chroma_and_fake_openai_end_to_end(
    tmp_path: Path,
) -> None:
    settings = create_settings(
        tmp_path,
    )
    chroma_client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        chroma_client,
        name=settings.chroma_collection_name,
        schema_version=settings.chroma_schema_version,
        embedding_model=settings.openai_embedding_model,
    )
    add_article(
        collection,
        KnowledgeArticle(
            id="recover-account-access",
            title="Como recuperar o acesso à conta",
            content=(
                "Use a recuperação de senha e aguarde o e-mail de confirmação "
                "antes de tentar acessar novamente."
            ),
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
        KnowledgeArticle(
            id="billing-payment-confirmation",
            title="Como confirmar pagamento",
            content=(
                "Pagamentos podem levar um período de compensação antes da "
                "liberação automática do acesso."
            ),
            category=TicketCategory.BILLING,
            keywords=[
                "pagamento",
                "fatura",
            ],
        ),
        [
            0.0,
            1.0,
        ],
    )
    test_app = create_application(
        settings=settings,
        knowledge_search_backend=ChromaKnowledgeSearchBackend(
            collection,
        ),
    )
    FakeAsyncOpenAI.instances = []

    with patch(
        "app.api.dependencies.rag.AsyncOpenAI",
        FakeAsyncOpenAI,
    ):
        with TestClient(
            test_app,
        ) as test_client:
            response = test_client.post(
                "/internal/rag/answer",
                headers={
                    "X-API-Key": "test-internal-api-key",
                },
                json={
                    "query": "Redefini minha senha e continuo sem acesso",
                    "top_k": 1,
                },
            )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()

    assert body["answer"] == (
        "Use a recuperação de senha e confirme o e-mail recebido."
    )
    assert body["source_count"] == 1
    assert body["sources"][0]["source_id"] == "recover-account-access"
    assert FakeAsyncOpenAI.instances[0].client.embeddings.calls == [
        {
            "model": "text-embedding-test",
            "input": [
                "Redefini minha senha e continuo sem acesso",
            ],
            "encoding_format": "float",
        },
    ]
    assert len(FakeAsyncOpenAI.instances[0].client.responses.calls) == 1


def test_rag_request_embeds_only_query_and_queries_chroma_once(
    tmp_path: Path,
) -> None:
    settings = create_settings(
        tmp_path,
    )
    collection = SpyChromaCollection()
    test_app = create_application(
        settings=settings,
        knowledge_search_backend=ChromaKnowledgeSearchBackend(
            collection,
        ),
    )
    FakeAsyncOpenAI.instances = []

    with patch(
        "app.api.dependencies.rag.AsyncOpenAI",
        FakeAsyncOpenAI,
    ):
        with TestClient(
            test_app,
        ) as test_client:
            response = test_client.post(
                "/internal/rag/answer",
                headers={
                    "X-API-Key": "test-internal-api-key",
                },
                json={
                    "query": "Como recuperar acesso?",
                    "top_k": 1,
                    "category": "acesso_e_autenticacao",
                },
            )

    assert response.status_code == status.HTTP_200_OK
    assert FakeAsyncOpenAI.instances[0].client.embeddings.calls == [
        {
            "model": "text-embedding-test",
            "input": [
                "Como recuperar acesso?",
            ],
            "encoding_format": "float",
        },
    ]
    assert len(FakeAsyncOpenAI.instances[0].client.responses.calls) == 1
    assert collection.query_calls == [
        {
            "query_embeddings": [
                [
                    1.0,
                    0.0,
                ],
            ],
            "n_results": 1,
            "where": {
                "category": {
                    "$eq": "acesso_e_autenticacao",
                },
            },
            "include": [
                "documents",
                "metadatas",
                "distances",
            ],
        },
    ]
    assert collection.upsert_calls == []
