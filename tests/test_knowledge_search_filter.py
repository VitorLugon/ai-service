import pytest
from pydantic import ValidationError

from app.knowledge.chroma_backend import build_chroma_where
from app.schemas.knowledge import KnowledgeSearchFilter
from app.schemas.tickets import TicketCategory


def test_knowledge_search_filter_without_category_builds_no_where() -> None:
    assert (
        build_chroma_where(
            KnowledgeSearchFilter(),
        )
        is None
    )


def test_knowledge_search_filter_builds_category_where() -> None:
    search_filter = KnowledgeSearchFilter(
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
    )

    assert build_chroma_where(
        search_filter,
    ) == {
        "category": {
            "$eq": "acesso_e_autenticacao",
        },
    }


def test_knowledge_search_filter_rejects_extra_fields() -> None:
    with pytest.raises(
        ValidationError,
    ):
        KnowledgeSearchFilter.model_validate(
            {
                "category": "cobranca",
                "where": {
                    "category": {
                        "$eq": "cobranca",
                    },
                },
            },
        )


def test_knowledge_search_filter_rejects_invalid_category() -> None:
    with pytest.raises(
        ValidationError,
    ):
        KnowledgeSearchFilter.model_validate(
            {
                "category": "billing",
            },
        )
