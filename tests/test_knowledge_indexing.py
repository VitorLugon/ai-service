import json

import pytest
from pydantic import ValidationError

from app.knowledge.indexing import (
    build_knowledge_index_record,
    build_knowledge_index_records,
)
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.knowledge_indexing import KnowledgeIndexMetadata
from app.schemas.tickets import TicketCategory


def create_article(
    article_id: str,
    *,
    keywords: list[str] | None = None,
) -> KnowledgeArticle:
    return KnowledgeArticle(
        id=article_id,
        title="Recuperação de acesso",
        content=(
            "Conteúdo sintético suficientemente longo para representar um artigo."
        ),
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        keywords=keywords
        or [
            "senha",
            "login",
        ],
    )


def test_build_knowledge_index_record_uses_article_data() -> None:
    article = create_article(
        "recover-access",
    )

    record = build_knowledge_index_record(
        article,
        schema_version=1,
        embedding_model="text-embedding-test",
    )

    assert record.id == "recover-access"
    assert record.document == article.content
    assert record.embedding_text == (
        "Título: Recuperação de acesso\n"
        "Categoria: acesso_e_autenticacao\n"
        "Palavras-chave: senha, login\n"
        "Conteúdo: Conteúdo sintético suficientemente longo "
        "para representar um artigo."
    )
    assert record.metadata.title == "Recuperação de acesso"
    assert record.metadata.category == "acesso_e_autenticacao"
    assert record.metadata.keywords_json == json.dumps(
        [
            "senha",
            "login",
        ],
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    )
    assert record.metadata.schema_version == 1
    assert record.metadata.embedding_model == "text-embedding-test"


def test_build_knowledge_index_records_preserves_order() -> None:
    records = build_knowledge_index_records(
        [
            create_article("first-article"),
            create_article("second-article"),
        ],
        schema_version=1,
        embedding_model="text-embedding-test",
    )

    assert [record.id for record in records] == [
        "first-article",
        "second-article",
    ]


def test_build_knowledge_index_records_rejects_empty_list() -> None:
    with pytest.raises(
        ValueError,
        match="ao menos um artigo",
    ):
        build_knowledge_index_records(
            [],
            schema_version=1,
            embedding_model="text-embedding-test",
        )


def test_build_knowledge_index_records_rejects_duplicate_ids() -> None:
    article = create_article(
        "duplicated-article",
    )

    with pytest.raises(
        ValueError,
        match="IDs duplicados",
    ):
        build_knowledge_index_records(
            [
                article,
                article,
            ],
            schema_version=1,
            embedding_model="text-embedding-test",
        )


def test_knowledge_index_metadata_rejects_extra_fields() -> None:
    with pytest.raises(
        ValidationError,
    ):
        KnowledgeIndexMetadata.model_validate(
            {
                "title": "Título",
                "category": "outro",
                "keywords_json": "[]",
                "schema_version": 1,
                "embedding_model": "text-embedding-test",
                "extra": "invalid",
            },
        )
