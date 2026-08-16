import math

import pytest
from pydantic import ValidationError

from app.schemas.rag import RagChunk, RagContext, RagPrompt, RagSource, RankedRagChunk
from app.schemas.tickets import TicketCategory


def valid_source(**overrides: object) -> RagSource:
    data: dict[str, object] = {
        "article_id": "recover-account-access",
        "title": "Recuperar acesso à conta",
        "category": TicketCategory.ACCESS_AND_AUTHENTICATION,
        "score": 0.87,
        "rank": 1,
        "content": "Conteúdo completo do artigo usado como evidência recuperada.",
    }
    data.update(
        overrides,
    )

    return RagSource(
        **data,
    )


def valid_chunk(**overrides: object) -> RagChunk:
    data: dict[str, object] = {
        "article_id": "recover-account-access",
        "title": "Recuperar acesso à conta",
        "category": TicketCategory.ACCESS_AND_AUTHENTICATION,
        "chunk_index": 0,
        "content": "Trecho recuperado do artigo com conteúdo suficiente.",
    }
    data.update(
        overrides,
    )

    return RagChunk(
        **data,
    )


def test_rag_source_accepts_valid_data() -> None:
    source = valid_source(
        article_id=" recover-account-access ",
        title=" Recuperar acesso à conta ",
        content=" Conteúdo completo do artigo usado como evidência recuperada. ",
    )

    assert source.article_id == "recover-account-access"
    assert source.title == "Recuperar acesso à conta"
    assert source.category is TicketCategory.ACCESS_AND_AUTHENTICATION
    assert source.score == 0.87
    assert source.rank == 1
    assert source.content == (
        "Conteúdo completo do artigo usado como evidência recuperada."
    )
    assert source.chunk_index is None
    assert source.chunk_id is None


def test_rag_source_accepts_chunk_origin() -> None:
    source = valid_source(
        chunk_index=2,
        chunk_id="recover-account-access#chunk-002",
    )

    assert source.chunk_index == 2
    assert source.chunk_id == "recover-account-access#chunk-002"


def test_rag_source_rejects_incomplete_chunk_origin() -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            chunk_index=0,
        )


def test_rag_source_rejects_incompatible_chunk_id() -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            chunk_index=1,
            chunk_id="recover-account-access#chunk-999",
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("article_id", "   "),
        ("title", "   "),
        ("content", "   "),
    ],
)
def test_rag_source_rejects_empty_strings(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            **{field_name: value},
        )


@pytest.mark.parametrize(
    "rank",
    [
        0,
        -1,
    ],
)
def test_rag_source_rejects_invalid_rank(
    rank: int,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            rank=rank,
        )


@pytest.mark.parametrize(
    "score",
    [
        1.01,
        -1.01,
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_rag_source_rejects_invalid_score(
    score: float,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            score=score,
        )


def test_rag_source_rejects_extra_field() -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            unexpected=True,
        )


def test_rag_context_accepts_valid_data() -> None:
    source = valid_source()
    context = RagContext(
        text="Texto de contexto.",
        sources=[
            source,
        ],
        source_count=1,
    )

    assert context.text == "Texto de contexto."
    assert context.sources == [
        source,
    ]
    assert context.source_count == 1


def test_rag_context_accepts_empty_context() -> None:
    context = RagContext(
        text="",
        sources=[],
        source_count=0,
    )

    assert context.text == ""
    assert context.sources == []
    assert context.source_count == 0


def test_rag_context_rejects_inconsistent_source_count() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagContext(
            text="Texto de contexto.",
            sources=[
                valid_source(),
            ],
            source_count=0,
        )


def test_rag_context_rejects_extra_field() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagContext(
            text="Texto de contexto.",
            sources=[],
            source_count=0,
            unexpected=True,
        )


def test_rag_objects_are_immutable() -> None:
    source = valid_source()
    context = RagContext(
        text="Texto de contexto.",
        sources=[
            source,
        ],
        source_count=1,
    )

    with pytest.raises(
        ValidationError,
    ):
        source.rank = 2

    with pytest.raises(
        ValidationError,
    ):
        context.source_count = 2


def test_rag_chunk_accepts_valid_data() -> None:
    chunk = valid_chunk(
        article_id=" recover-account-access ",
        title=" Recuperar acesso à conta ",
        content=" Trecho recuperado do artigo com conteúdo suficiente. ",
    )

    assert chunk.article_id == "recover-account-access"
    assert chunk.title == "Recuperar acesso à conta"
    assert chunk.category is TicketCategory.ACCESS_AND_AUTHENTICATION
    assert chunk.chunk_index == 0
    assert chunk.content == "Trecho recuperado do artigo com conteúdo suficiente."
    assert chunk.chunk_id == "recover-account-access#chunk-000"


def test_rag_chunk_accepts_matching_chunk_id() -> None:
    chunk = valid_chunk(
        chunk_index=2,
        chunk_id="recover-account-access#chunk-002",
    )

    assert chunk.chunk_id == "recover-account-access#chunk-002"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("article_id", "   "),
        ("title", "   "),
        ("content", "   "),
    ],
)
def test_rag_chunk_rejects_empty_strings(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_chunk(
            **{field_name: value},
        )


def test_rag_chunk_rejects_negative_index() -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_chunk(
            chunk_index=-1,
        )


def test_rag_chunk_rejects_incompatible_chunk_id() -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_chunk(
            chunk_index=1,
            chunk_id="recover-account-access#chunk-999",
        )


def test_rag_chunk_rejects_invalid_category() -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_chunk(
            category="categoria-invalida",
        )


def test_rag_chunk_rejects_extra_field() -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_chunk(
            unexpected=True,
        )


def test_rag_chunk_is_immutable() -> None:
    chunk = valid_chunk()

    with pytest.raises(
        ValidationError,
    ):
        chunk.chunk_index = 2


def test_ranked_rag_chunk_accepts_valid_data() -> None:
    ranked_chunk = RankedRagChunk(
        chunk=valid_chunk(),
        score=0.76,
        rank=1,
    )

    assert ranked_chunk.chunk.chunk_id == "recover-account-access#chunk-000"
    assert ranked_chunk.score == 0.76
    assert ranked_chunk.rank == 1


@pytest.mark.parametrize(
    "score",
    [
        1.01,
        -1.01,
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_ranked_rag_chunk_rejects_invalid_score(
    score: float,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        RankedRagChunk(
            chunk=valid_chunk(),
            score=score,
            rank=1,
        )


def test_ranked_rag_chunk_rejects_invalid_rank() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RankedRagChunk(
            chunk=valid_chunk(),
            score=0.76,
            rank=0,
        )


def test_ranked_rag_chunk_rejects_extra_field() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RankedRagChunk(
            chunk=valid_chunk(),
            score=0.76,
            rank=1,
            unexpected=True,
        )


def test_rag_prompt_accepts_valid_data() -> None:
    prompt = RagPrompt(
        system_instructions=" Instruções estáveis do sistema. ",
        user_message=" Mensagem estruturada do usuário. ",
    )

    assert prompt.system_instructions == "Instruções estáveis do sistema."
    assert prompt.user_message == "Mensagem estruturada do usuário."


@pytest.mark.parametrize(
    "system_instructions",
    [
        "",
        "   ",
        "\n\t",
    ],
)
def test_rag_prompt_rejects_empty_system_instructions(
    system_instructions: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagPrompt(
            system_instructions=system_instructions,
            user_message="Mensagem estruturada do usuário.",
        )


@pytest.mark.parametrize(
    "user_message",
    [
        "",
        "   ",
        "\n\t",
    ],
)
def test_rag_prompt_rejects_empty_user_message(
    user_message: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagPrompt(
            system_instructions="Instruções estáveis do sistema.",
            user_message=user_message,
        )


def test_rag_prompt_rejects_extra_field() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagPrompt(
            system_instructions="Instruções estáveis do sistema.",
            user_message="Mensagem estruturada do usuário.",
            unexpected=True,
        )


def test_rag_prompt_is_immutable() -> None:
    prompt = RagPrompt(
        system_instructions="Instruções estáveis do sistema.",
        user_message="Mensagem estruturada do usuário.",
    )

    with pytest.raises(
        ValidationError,
    ):
        prompt.user_message = "Outra mensagem."
