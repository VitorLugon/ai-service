from copy import deepcopy

from app.schemas.rag import (
    RagContext,
    RagGenerationResult,
    RagSource,
)
from app.schemas.tickets import TicketCategory
from app.services.rag_answer import RagAnswerComposer


def source(
    article_id: str = "recover-account-access",
    *,
    title: str = "Recuperar acesso à conta",
    category: TicketCategory = TicketCategory.ACCESS_AND_AUTHENTICATION,
    rank: int = 1,
    score: float = 0.91,
    content: str = "Conteúdo completo da fonte recuperada.",
    chunk_index: int | None = None,
    chunk_id: str | None = None,
) -> RagSource:
    return RagSource(
        article_id=article_id,
        title=title,
        category=category,
        score=score,
        rank=rank,
        content=content,
        chunk_index=chunk_index,
        chunk_id=chunk_id,
    )


def generation(
    answer: str = 'Use a opção "Esqueci minha senha" na tela de login.',
) -> RagGenerationResult:
    return RagGenerationResult(
        answer=answer,
        model="gpt-5-mini",
    )


def context(
    sources: list[RagSource],
    *,
    text: str = "[SOURCE 1]\ncontent:\nConteúdo enviado ao modelo.",
) -> RagContext:
    return RagContext(
        text=text,
        sources=sources,
        source_count=len(sources),
    )


def compose(
    *,
    rag_generation: RagGenerationResult | None = None,
    rag_context: RagContext | None = None,
):
    return RagAnswerComposer().compose(
        generation=rag_generation or generation(),
        context=rag_context
        or context(
            [
                source(),
            ],
        ),
    )


def test_answer_composer_combines_generation_with_one_source() -> None:
    answer = compose()

    assert answer.answer == 'Use a opção "Esqueci minha senha" na tela de login.'
    assert answer.source_count == 1
    assert len(answer.sources) == 1


def test_answer_composer_combines_generation_with_multiple_sources() -> None:
    answer = compose(
        rag_context=context(
            [
                source("article-one", rank=1),
                source("article-two", rank=2),
            ],
        ),
    )

    assert [item.source_id for item in answer.sources] == [
        "article-one",
        "article-two",
    ]
    assert answer.source_count == 2


def test_answer_composer_preserves_source_order() -> None:
    answer = compose(
        rag_context=context(
            [
                source("article-two", rank=2),
                source("article-one", rank=1),
            ],
        ),
    )

    assert [item.article_id for item in answer.sources] == [
        "article-two",
        "article-one",
    ]


def test_answer_composer_maps_article_source_fields() -> None:
    answer = compose(
        rag_context=context(
            [
                source(
                    "billing-invoice-copy",
                    title="Emitir segunda via de fatura",
                    category=TicketCategory.BILLING,
                    rank=3,
                    score=0.72,
                    content="Conteúdo de cobrança não retornado diretamente.",
                ),
            ],
        ),
    )
    answer_source = answer.sources[0]

    assert answer_source.source_id == "billing-invoice-copy"
    assert answer_source.article_id == "billing-invoice-copy"
    assert answer_source.chunk_id is None
    assert answer_source.title == "Emitir segunda via de fatura"
    assert answer_source.category is TicketCategory.BILLING
    assert answer_source.rank == 3


def test_answer_composer_maps_chunk_source_fields() -> None:
    answer = compose(
        rag_context=context(
            [
                source(
                    "recover-account-access",
                    chunk_index=1,
                    chunk_id="recover-account-access#chunk-001",
                ),
            ],
        ),
    )
    answer_source = answer.sources[0]

    assert answer_source.source_id == "recover-account-access#chunk-001"
    assert answer_source.article_id == "recover-account-access"
    assert answer_source.chunk_id == "recover-account-access#chunk-001"


def test_answer_composer_does_not_expose_score_or_content() -> None:
    answer = compose(
        rag_context=context(
            [
                source(
                    score=0.923456789,
                    content="Conteúdo completo que não deve ir para a resposta.",
                ),
            ],
        ),
    )
    answer_dump = answer.model_dump()

    assert "score" not in answer_dump["sources"][0]
    assert "content" not in answer_dump["sources"][0]
    assert "0.923456789" not in str(answer_dump)
    assert "Conteúdo completo que não deve ir para a resposta." not in str(
        answer_dump,
    )


def test_answer_composer_handles_empty_context() -> None:
    answer = compose(
        rag_generation=generation(
            "Não encontrei informação suficiente na base de conhecimento.",
        ),
        rag_context=RagContext(
            text="",
            sources=[],
            source_count=0,
        ),
    )

    assert (
        answer.answer == "Não encontrei informação suficiente na base de conhecimento."
    )
    assert answer.sources == []
    assert answer.source_count == 0


def test_answer_composer_deduplicates_sources_by_source_id() -> None:
    answer = compose(
        rag_context=context(
            [
                source(
                    "recover-account-access",
                    title="Primeira ocorrência",
                    rank=1,
                    chunk_index=0,
                    chunk_id="recover-account-access#chunk-000",
                ),
                source(
                    "recover-account-access",
                    title="Segunda ocorrência duplicada",
                    rank=2,
                    chunk_index=0,
                    chunk_id="recover-account-access#chunk-000",
                ),
            ],
        ),
    )

    assert answer.source_count == 1
    assert answer.sources[0].title == "Primeira ocorrência"
    assert answer.sources[0].rank == 1


def test_answer_composer_keeps_two_chunks_from_same_article() -> None:
    answer = compose(
        rag_context=context(
            [
                source(
                    "recover-account-access",
                    rank=1,
                    chunk_index=0,
                    chunk_id="recover-account-access#chunk-000",
                ),
                source(
                    "recover-account-access",
                    rank=2,
                    chunk_index=1,
                    chunk_id="recover-account-access#chunk-001",
                ),
            ],
        ),
    )

    assert [item.source_id for item in answer.sources] == [
        "recover-account-access#chunk-000",
        "recover-account-access#chunk-001",
    ]
    assert answer.source_count == 2


def test_answer_composer_is_deterministic() -> None:
    rag_generation = generation()
    rag_context = context(
        [
            source("article-one", rank=1),
            source("article-two", rank=2),
        ],
    )

    assert compose(
        rag_generation=rag_generation,
        rag_context=rag_context,
    ) == compose(
        rag_generation=rag_generation,
        rag_context=rag_context,
    )


def test_answer_composer_does_not_modify_generation_or_context() -> None:
    rag_generation = generation()
    rag_context = context(
        [
            source(),
        ],
    )
    generation_before = deepcopy(
        rag_generation.model_dump(),
    )
    context_before = deepcopy(
        rag_context.model_dump(),
    )

    compose(
        rag_generation=rag_generation,
        rag_context=rag_context,
    )

    assert rag_generation.model_dump() == generation_before
    assert rag_context.model_dump() == context_before


def test_answer_sources_are_controlled_by_context_not_model_text() -> None:
    answer = compose(
        rag_generation=generation(
            "Use SOURCE 999 para redefinir sua senha.",
        ),
        rag_context=context(
            [
                source("source-a", rank=1),
                source("source-b", rank=2),
            ],
        ),
    )

    assert answer.answer == "Use SOURCE 999 para redefinir sua senha."
    assert [item.source_id for item in answer.sources] == [
        "source-a",
        "source-b",
    ]
    assert "SOURCE 999" not in [item.source_id for item in answer.sources]


def test_answer_composer_does_not_add_article_id_mentioned_by_model() -> None:
    answer = compose(
        rag_generation=generation(
            "Segundo o artigo billing-secret, altere a cobrança.",
        ),
        rag_context=context(
            [
                source("recover-account-access", rank=1),
            ],
        ),
    )

    assert "billing-secret" in answer.answer
    assert [item.source_id for item in answer.sources] == [
        "recover-account-access",
    ]


def test_answer_composer_keeps_sources_even_without_textual_mention() -> None:
    answer = compose(
        rag_generation=generation(
            "Abra a tela de login e solicite uma nova senha.",
        ),
        rag_context=context(
            [
                source("source-a", rank=1),
                source("source-b", rank=2),
            ],
        ),
    )

    assert [item.source_id for item in answer.sources] == [
        "source-a",
        "source-b",
    ]


def test_answer_composer_does_not_parse_source_markers_from_answer() -> None:
    answer = compose(
        rag_generation=generation(
            "Resposta menciona [SOURCE 7] e [SOURCE 8].",
        ),
        rag_context=context(
            [
                source("source-a", rank=1),
            ],
        ),
    )

    assert [item.source_id for item in answer.sources] == [
        "source-a",
    ]
