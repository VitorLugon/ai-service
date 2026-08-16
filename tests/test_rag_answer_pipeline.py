import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.rag.context_builder import RagContextBuilder
from app.rag.prompt_builder import EMPTY_CONTEXT_MESSAGE, RagPromptBuilder
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchMatch
from app.schemas.tickets import TicketCategory
from app.services.rag_answer import RagAnswerComposer
from app.services.rag_generation import RagGenerationService


def article(
    article_id: str,
    *,
    content: str,
    title: str | None = None,
) -> KnowledgeArticle:
    return KnowledgeArticle.model_construct(
        id=article_id,
        title=title or f"Artigo {article_id}",
        content=content,
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        keywords=[
            "acesso",
        ],
    )


def match(
    article_id: str,
    *,
    content: str,
    title: str | None = None,
    score: float = 0.91,
) -> KnowledgeSearchMatch:
    return KnowledgeSearchMatch(
        article=article(
            article_id,
            content=content,
            title=title,
        ),
        score=score,
    )


def fake_client(
    answer: str,
) -> MagicMock:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            output_text=answer,
            status="completed",
        ),
    )

    return client


def run_pipeline(
    matches: list[KnowledgeSearchMatch],
    *,
    client: MagicMock,
    question: str = "Como recupero minha conta?",
    max_characters: int = 2_000,
):
    context = RagContextBuilder(
        max_characters=max_characters,
    ).build(
        matches,
    )
    prompt = RagPromptBuilder(
        question_max_characters=2_000,
    ).build(
        question=question,
        context=context,
    )
    generation = asyncio.run(
        RagGenerationService(
            client=client,
            model="gpt-5-mini",
            max_output_tokens=800,
        ).generate(
            prompt,
        ),
    )

    return RagAnswerComposer().compose(
        generation=generation,
        context=context,
    )


def test_rag_answer_pipeline_returns_answer_and_source_provenance() -> None:
    client = fake_client(
        'Use a opção "Esqueci minha senha" na tela de login.',
    )

    answer = run_pipeline(
        [
            match(
                "recover-account-access",
                title="Recuperar acesso à conta",
                content='Para recuperar acesso, use "Esqueci minha senha".',
            ),
            match(
                "account-temporary-password",
                title="Senha temporária",
                content="A senha temporária expira após o primeiro acesso.",
                score=0.8,
            ),
        ],
        client=client,
    )

    assert answer.answer == 'Use a opção "Esqueci minha senha" na tela de login.'
    assert answer.source_count == 2
    assert [source.source_id for source in answer.sources] == [
        "recover-account-access",
        "account-temporary-password",
    ]
    assert [source.rank for source in answer.sources] == [
        1,
        2,
    ]
    assert answer.sources[0].title == "Recuperar acesso à conta"


def test_rag_answer_pipeline_handles_empty_evidence() -> None:
    client = fake_client(
        "Não encontrei informação suficiente na base de conhecimento.",
    )

    answer = run_pipeline(
        [],
        client=client,
        question="Como altero o idioma?",
    )

    assert (
        answer.answer == "Não encontrei informação suficiente na base de conhecimento."
    )
    assert answer.sources == []
    assert answer.source_count == 0
    assert EMPTY_CONTEXT_MESSAGE in client.responses.create.await_args.kwargs["input"]


def test_rag_answer_pipeline_ignores_source_hallucination() -> None:
    client = fake_client(
        "Segundo SOURCE 999, siga o procedimento secreto.",
    )

    answer = run_pipeline(
        [
            match(
                "recover-account-access",
                content="Procedimento público para recuperar acesso.",
            ),
        ],
        client=client,
    )

    assert answer.answer == "Segundo SOURCE 999, siga o procedimento secreto."
    assert [source.source_id for source in answer.sources] == [
        "recover-account-access",
    ]


def test_rag_answer_pipeline_does_not_reintroduce_budget_removed_source() -> None:
    client = fake_client(
        "Resposta baseada apenas na primeira fonte.",
    )

    answer = run_pipeline(
        [
            match(
                "included-article",
                content="A" * 350,
            ),
            match(
                "removed-by-budget",
                content="B" * 900,
            ),
        ],
        client=client,
        max_characters=1_000,
    )

    assert [source.source_id for source in answer.sources] == [
        "included-article",
    ]
    assert "removed-by-budget" not in client.responses.create.await_args.kwargs["input"]
