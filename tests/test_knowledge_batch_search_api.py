from collections.abc import Iterator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies.knowledge_search import get_knowledge_batch_search_service
from app.main import app
from app.schemas.knowledge import (
    KnowledgeArticle,
    KnowledgeBatchSearchItem,
    KnowledgeBatchSearchResponse,
    KnowledgeSearchFilter,
    KnowledgeSearchMatch,
)
from app.schemas.tickets import TicketCategory


def create_match(
    article_id: str,
) -> KnowledgeSearchMatch:
    return KnowledgeSearchMatch(
        article=KnowledgeArticle(
            id=article_id,
            title="Como recuperar o acesso à conta",
            content=(
                "Utilize a recuperação de senha para voltar a acessar "
                "a plataforma com segurança."
            ),
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
            keywords=[
                "senha",
                "login",
            ],
        ),
        score=0.95,
    )


class FakeKnowledgeBatchSearchService:
    model = "test-embedding-model"
    indexed_articles = 12

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], int, KnowledgeSearchFilter | None]] = []

    async def search_many(
        self,
        queries: list[str],
        *,
        top_k: int = 3,
        search_filter: KnowledgeSearchFilter | None = None,
    ) -> KnowledgeBatchSearchResponse:
        self.calls.append(
            (
                list(queries),
                top_k,
                search_filter,
            ),
        )

        return KnowledgeBatchSearchResponse(
            model=self.model,
            indexed_articles=self.indexed_articles,
            results=[
                KnowledgeBatchSearchItem(
                    query=query,
                    matches=[
                        create_match(
                            f"article-{index}",
                        ),
                    ][:top_k],
                )
                for index, query in enumerate(
                    queries,
                    start=1,
                )
            ],
        )


@pytest.fixture
def fake_batch_service() -> FakeKnowledgeBatchSearchService:
    return FakeKnowledgeBatchSearchService()


@pytest.fixture
def batch_client(
    client: TestClient,
    fake_batch_service: FakeKnowledgeBatchSearchService,
) -> Iterator[TestClient]:
    app.dependency_overrides[get_knowledge_batch_search_service] = lambda: (
        fake_batch_service
    )

    try:
        yield client
    finally:
        app.dependency_overrides.pop(
            get_knowledge_batch_search_service,
            None,
        )


def test_batch_search_returns_results(
    batch_client: TestClient,
    fake_batch_service: FakeKnowledgeBatchSearchService,
    api_key: str,
) -> None:
    response = batch_client.post(
        "/internal/knowledge/search/batch",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "queries": [
                "não consigo entrar",
                "como exportar usuários?",
            ],
            "top_k": 2,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    body = response.json()

    assert body["model"] == "test-embedding-model"
    assert body["indexed_articles"] == 12
    assert [item["query"] for item in body["results"]] == [
        "não consigo entrar",
        "como exportar usuários?",
    ]
    assert fake_batch_service.calls == [
        (
            [
                "não consigo entrar",
                "como exportar usuários?",
            ],
            2,
            None,
        ),
    ]


def test_batch_search_normalizes_queries(
    batch_client: TestClient,
    fake_batch_service: FakeKnowledgeBatchSearchService,
    api_key: str,
) -> None:
    response = batch_client.post(
        "/internal/knowledge/search/batch",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "queries": [
                "  não consigo entrar  ",
                "como exportar usuários?   ",
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert fake_batch_service.calls[0] == (
        [
            "não consigo entrar",
            "como exportar usuários?",
        ],
        3,
        None,
    )


def test_batch_search_accepts_category_filter(
    batch_client: TestClient,
    fake_batch_service: FakeKnowledgeBatchSearchService,
    api_key: str,
) -> None:
    response = batch_client.post(
        "/internal/knowledge/search/batch",
        headers={
            "X-API-Key": api_key,
        },
        json={
            "queries": [
                "minha conta foi suspensa após pagamento",
            ],
            "category": "cobranca",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert fake_batch_service.calls[0] == (
        [
            "minha conta foi suspensa após pagamento",
        ],
        3,
        KnowledgeSearchFilter(
            category=TicketCategory.BILLING,
        ),
    )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "queries": [],
        },
        {
            "queries": [
                "válida",
            ],
            "top_k": 0,
        },
        {
            "queries": [
                "válida",
            ],
            "top_k": 11,
        },
        {
            "queries": [
                "válida",
                "   ",
            ],
        },
        {
            "queries": [
                f"consulta {index}"
                for index in range(
                    21,
                )
            ],
        },
        {
            "queries": [
                "válida",
            ],
            "category": "billing",
        },
        {
            "queries": [
                "válida",
            ],
            "unexpected": True,
        },
    ],
)
def test_batch_search_rejects_invalid_payload(
    batch_client: TestClient,
    api_key: str,
    payload: dict[str, object],
) -> None:
    response = batch_client.post(
        "/internal/knowledge/search/batch",
        headers={
            "X-API-Key": api_key,
        },
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_batch_search_requires_api_key(
    batch_client: TestClient,
) -> None:
    response = batch_client.post(
        "/internal/knowledge/search/batch",
        json={
            "queries": [
                "não consigo entrar",
            ],
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_batch_search_rejects_invalid_api_key(
    batch_client: TestClient,
) -> None:
    response = batch_client.post(
        "/internal/knowledge/search/batch",
        headers={
            "X-API-Key": "invalid-key",
        },
        json={
            "queries": [
                "não consigo entrar",
            ],
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_openapi_documents_batch_search(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == status.HTTP_200_OK

    operation = response.json()["paths"]["/internal/knowledge/search/batch"]["post"]

    assert operation["security"] == [
        {
            "InternalApiKey": [],
        },
    ]

    responses = operation["responses"]

    for response_code in [
        "200",
        "401",
        "422",
        "502",
        "503",
        "504",
    ]:
        assert response_code in responses
