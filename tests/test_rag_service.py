import asyncio
from collections.abc import Sequence

import pytest

from app.core.exceptions import AIProviderTimeoutError
from app.schemas.knowledge import (
    KnowledgeArticle,
    KnowledgeSearchFilter,
    KnowledgeSearchMatch,
)
from app.schemas.rag import (
    RagAnswer,
    RagAnswerSource,
    RagContext,
    RagGenerationResult,
    RagPrompt,
    RagSource,
)
from app.schemas.tickets import TicketCategory
from app.services.rag_service import RagService


def create_match(
    article_id: str,
    *,
    score: float = 0.95,
) -> KnowledgeSearchMatch:
    article = KnowledgeArticle(
        id=article_id,
        title="Como recuperar o acesso à conta",
        content=(
            "Utilize a recuperação de senha e aguarde o e-mail de confirmação "
            "antes de tentar entrar novamente."
        ),
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        keywords=[
            "senha",
            "login",
        ],
    )

    return KnowledgeSearchMatch(
        article=article,
        score=score,
    )


class FakeSearchService:
    def __init__(
        self,
        matches: list[KnowledgeSearchMatch],
    ) -> None:
        self.matches = matches
        self.calls: list[tuple[str, int, KnowledgeSearchFilter | None]] = []

    async def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        search_filter: KnowledgeSearchFilter | None = None,
    ) -> list[KnowledgeSearchMatch]:
        self.calls.append(
            (
                query,
                top_k,
                search_filter,
            ),
        )

        return self.matches


class FakeContextBuilder:
    def __init__(self) -> None:
        self.calls: list[list[KnowledgeSearchMatch]] = []

    def build(
        self,
        matches: Sequence[KnowledgeSearchMatch],
    ) -> RagContext:
        match_list = list(
            matches,
        )
        self.calls.append(
            match_list,
        )

        sources = [
            RagSource(
                article_id=match.article.id,
                title=match.article.title,
                category=match.article.category,
                score=match.score,
                rank=index,
                content=match.article.content,
            )
            for index, match in enumerate(
                match_list,
                start=1,
            )
        ]

        return RagContext(
            text="\n".join(source.content for source in sources),
            sources=sources,
            source_count=len(sources),
        )


class FakePromptBuilder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, RagContext]] = []

    def build(
        self,
        *,
        question: str,
        context: RagContext,
    ) -> RagPrompt:
        self.calls.append(
            (
                question,
                context,
            ),
        )

        return RagPrompt(
            system_instructions="Responda somente com base no contexto.",
            user_message=f"{context.text}\n\n{question}",
        )


class FakeGenerationService:
    def __init__(
        self,
        *,
        answer: str = "Use a recuperação de senha e valide o e-mail recebido.",
        error: Exception | None = None,
    ) -> None:
        self.answer = answer
        self.error = error
        self.calls: list[RagPrompt] = []

    async def generate(
        self,
        prompt: RagPrompt,
    ) -> RagGenerationResult:
        self.calls.append(
            prompt,
        )

        if self.error is not None:
            raise self.error

        return RagGenerationResult(
            answer=self.answer,
            model="test-rag-model",
        )


class FakeAnswerComposer:
    def __init__(self) -> None:
        self.calls: list[tuple[RagGenerationResult, RagContext]] = []

    def compose(
        self,
        *,
        generation: RagGenerationResult,
        context: RagContext,
    ) -> RagAnswer:
        self.calls.append(
            (
                generation,
                context,
            ),
        )

        return RagAnswer(
            answer=generation.answer,
            sources=[
                RagAnswerSource(
                    source_id=source.article_id,
                    article_id=source.article_id,
                    title=source.title,
                    category=source.category,
                    rank=source.rank,
                )
                for source in context.sources
            ],
            source_count=context.source_count,
        )


def create_service(
    *,
    matches: list[KnowledgeSearchMatch],
    generation_error: Exception | None = None,
) -> tuple[
    RagService,
    FakeSearchService,
    FakeContextBuilder,
    FakePromptBuilder,
    FakeGenerationService,
    FakeAnswerComposer,
]:
    search_service = FakeSearchService(
        matches,
    )
    context_builder = FakeContextBuilder()
    prompt_builder = FakePromptBuilder()
    generation_service = FakeGenerationService(
        error=generation_error,
    )
    answer_composer = FakeAnswerComposer()
    service = RagService(
        search_service=search_service,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        generation_service=generation_service,
        answer_composer=answer_composer,
    )

    return (
        service,
        search_service,
        context_builder,
        prompt_builder,
        generation_service,
        answer_composer,
    )


def test_rag_service_runs_pipeline_in_order() -> None:
    matches = [
        create_match(
            "recover-account-access",
        ),
        create_match(
            "configure-multi-factor-authentication",
            score=0.87,
        ),
    ]
    (
        service,
        search_service,
        context_builder,
        prompt_builder,
        generation_service,
        answer_composer,
    ) = create_service(
        matches=matches,
    )
    search_filter = KnowledgeSearchFilter(
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
    )

    answer = asyncio.run(
        service.answer(
            question="  Não consigo acessar minha conta  ",
            top_k=2,
            search_filter=search_filter,
        ),
    )

    assert search_service.calls == [
        (
            "  Não consigo acessar minha conta  ",
            2,
            search_filter,
        ),
    ]
    assert context_builder.calls == [
        matches,
    ]
    assert prompt_builder.calls[0][0] == "  Não consigo acessar minha conta  "
    assert len(generation_service.calls) == 1
    assert generation_service.calls[0].system_instructions == (
        "Responda somente com base no contexto."
    )
    assert generation_service.calls[0].user_message.endswith(
        "Não consigo acessar minha conta",
    )
    assert answer_composer.calls[0][0].answer == (
        "Use a recuperação de senha e valide o e-mail recebido."
    )
    assert answer.source_count == 2
    assert [source.source_id for source in answer.sources] == [
        "recover-account-access",
        "configure-multi-factor-authentication",
    ]


def test_rag_service_supports_empty_context() -> None:
    service, *_ = create_service(
        matches=[],
    )

    answer = asyncio.run(
        service.answer(
            question="Pergunta sem fonte relevante",
        ),
    )

    assert answer.answer == "Use a recuperação de senha e valide o e-mail recebido."
    assert answer.sources == []
    assert answer.source_count == 0


def test_rag_service_propagates_generation_errors() -> None:
    (
        service,
        _search_service,
        _context_builder,
        _prompt_builder,
        _generation_service,
        answer_composer,
    ) = create_service(
        matches=[
            create_match(
                "recover-account-access",
            ),
        ],
        generation_error=AIProviderTimeoutError(),
    )

    with pytest.raises(AIProviderTimeoutError):
        asyncio.run(
            service.answer(
                question="Não consigo acessar minha conta",
            ),
        )

    assert answer_composer.calls == []


def test_rag_service_does_not_parse_generated_source_markers() -> None:
    match = create_match(
        "recover-account-access",
    )
    (
        service,
        _search_service,
        _context_builder,
        _prompt_builder,
        generation_service,
        _answer_composer,
    ) = create_service(
        matches=[
            match,
        ],
    )
    generation_service.answer = "Resposta citando [SOURCE 999] sem autoridade."

    answer = asyncio.run(
        service.answer(
            question="Não consigo acessar minha conta",
        ),
    )

    assert answer.answer == "Resposta citando [SOURCE 999] sem autoridade."
    assert [source.source_id for source in answer.sources] == [
        "recover-account-access",
    ]
