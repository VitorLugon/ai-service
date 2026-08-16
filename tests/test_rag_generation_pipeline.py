import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.rag.context_builder import RagContextBuilder
from app.rag.prompt_builder import EMPTY_CONTEXT_MESSAGE, RagPromptBuilder
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchMatch
from app.schemas.tickets import TicketCategory
from app.services.rag_generation import RagGenerationService


def article(
    article_id: str,
    *,
    content: str,
) -> KnowledgeArticle:
    return KnowledgeArticle.model_construct(
        id=article_id,
        title="Recuperar acesso à conta",
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
    score: float = 0.91,
) -> KnowledgeSearchMatch:
    return KnowledgeSearchMatch(
        article=article(
            article_id,
            content=content,
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


def run_generation(
    client: MagicMock,
    matches: list[KnowledgeSearchMatch],
    *,
    question: str = "Como recupero minha conta?",
    max_characters: int = 2_000,
) -> str:
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
    result = asyncio.run(
        RagGenerationService(
            client=client,
            model="gpt-5-mini",
            max_output_tokens=800,
        ).generate(
            prompt,
        ),
    )

    return result.answer


def test_rag_generation_pipeline_uses_context_and_returns_answer() -> None:
    client = fake_client(
        'Use a opção "Esqueci minha senha" na tela de login.',
    )

    answer = run_generation(
        client,
        [
            match(
                "recover-account-access",
                content='Para recuperar acesso, use "Esqueci minha senha".',
            ),
        ],
    )

    call_kwargs = client.responses.create.await_args.kwargs
    assert answer == 'Use a opção "Esqueci minha senha" na tela de login.'
    assert "[SOURCE 1]" in call_kwargs["input"]
    assert "Esqueci minha senha" in call_kwargs["input"]
    assert "usando somente" in call_kwargs["instructions"]


def test_rag_generation_pipeline_handles_empty_evidence() -> None:
    client = fake_client(
        "Não encontrei informação suficiente na base de conhecimento para responder.",
    )

    answer = run_generation(
        client,
        [],
        question="Como altero o idioma?",
    )

    assert answer == (
        "Não encontrei informação suficiente na base de conhecimento para responder."
    )
    assert EMPTY_CONTEXT_MESSAGE in client.responses.create.await_args.kwargs["input"]


def test_rag_generation_pipeline_preserves_budget_until_provider_request() -> None:
    removed_by_budget = "CONTEUDO_FORA_DO_ORCAMENTO_NAO_DEVE_APARECER"
    long_content = ("Conteúdo permitido. " * 60) + removed_by_budget
    client = fake_client(
        "Resposta baseada apenas no trecho permitido.",
    )

    run_generation(
        client,
        [
            match(
                "recover-account-access",
                content=long_content,
            ),
        ],
        max_characters=1_000,
    )

    provider_input = client.responses.create.await_args.kwargs["input"]
    assert "Conteúdo permitido." in provider_input
    assert removed_by_budget not in provider_input
