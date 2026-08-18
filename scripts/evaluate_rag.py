import argparse
import asyncio
import sys
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.evaluation.rag_dataset import load_rag_evaluation_cases
from app.knowledge.chroma_runtime import load_persisted_knowledge_backend
from app.knowledge.loader import load_knowledge_articles
from app.rag.context_builder import RagContextBuilder
from app.rag.prompt_builder import RagPromptBuilder
from app.schemas.rag_evaluation import RagEvaluationCase
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_search import KnowledgeSearchService
from app.services.rag_answer import RagAnswerComposer
from app.services.rag_evaluator import (
    RagEvaluationPipelineOutput,
    RagEvaluator,
)
from app.services.rag_generation import RagGenerationService
from scripts.evaluate_rag_offline import print_report

KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")
RAG_EVALUATION_DATASET_PATH = Path("evaluation/rag_cases.json")
DEFAULT_TOP_K = 5


class RealRagEvaluationPipeline:
    """Executa o pipeline RAG real para avaliação controlada por script."""

    def __init__(
        self,
        *,
        search_service: KnowledgeSearchService,
        context_builder: RagContextBuilder,
        prompt_builder: RagPromptBuilder,
        generation_service: RagGenerationService,
        answer_composer: RagAnswerComposer,
        top_k: int,
    ) -> None:
        self._search_service = search_service
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._generation_service = generation_service
        self._answer_composer = answer_composer
        self._top_k = top_k

    async def run(
        self,
        question: str,
    ) -> RagEvaluationPipelineOutput:
        matches = await self._search_service.search(
            question,
            top_k=self._top_k,
        )
        context = self._context_builder.build(
            matches,
        )
        prompt = self._prompt_builder.build(
            question=question,
            context=context,
        )
        generation = await self._generation_service.generate(
            prompt,
        )
        answer = self._answer_composer.compose(
            generation=generation,
            context=context,
        )

        return RagEvaluationPipelineOutput(
            retrieved_article_ids=[match.article.id for match in matches],
            answer=answer,
        )


async def main() -> None:
    """Executa avaliação RAG real usando OpenAI e Chroma persistente."""

    _configure_stdout()

    args = _parse_args()
    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY não foi configurada.",
        )

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY está vazia.",
        )

    backend = load_persisted_knowledge_backend(
        settings,
    )
    articles = load_knowledge_articles(
        KNOWLEDGE_BASE_PATH,
    )
    cases = load_rag_evaluation_cases(
        RAG_EVALUATION_DATASET_PATH,
        known_article_ids={article.id for article in articles},
    )
    selected_cases = _select_cases(
        cases,
        max_cases=args.max_cases,
        case_id=args.case_id,
    )

    print(f"Cases selected: {len(selected_cases)}")
    print(f"Embedding calls expected: {len(selected_cases)}")
    print(f"Generation calls expected: {len(selected_cases)}")
    print(f"Embedding model: {settings.openai_embedding_model}")
    print(f"Generation model: {settings.openai_rag_model}")
    print("Vector store: Chroma")
    print(f"Collection: {settings.chroma_collection_name}")
    print(f"Indexed articles: {backend.size}")
    print()

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=60.0,
        max_retries=2,
    ) as client:
        search_service = KnowledgeSearchService(
            embedding_provider=EmbeddingService(
                client=client,
                model=settings.openai_embedding_model,
            ),
            index=backend,
        )
        pipeline = RealRagEvaluationPipeline(
            search_service=search_service,
            context_builder=RagContextBuilder(
                max_characters=settings.rag_context_max_characters,
            ),
            prompt_builder=RagPromptBuilder(
                question_max_characters=settings.rag_question_max_characters,
            ),
            generation_service=RagGenerationService(
                client=client,
                model=settings.openai_rag_model,
                max_output_tokens=settings.rag_max_output_tokens,
            ),
            answer_composer=RagAnswerComposer(),
            top_k=args.top_k,
        )
        evaluator = RagEvaluator(
            pipeline,
        )
        report = await evaluator.evaluate(
            selected_cases,
        )

    print_report(
        report,
    )
    print()
    print("Cases:")

    for result in report.case_results:
        print(f"- {result.case_id}")
        print(f"  retrieved: {', '.join(result.retrieved_article_ids) or 'none'}")
        print(f"  sources: {', '.join(result.returned_source_ids) or 'none'}")
        print(f"  answer: {result.answer}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Avalia o pipeline RAG real com custo controlado.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Quantidade máxima de casos a executar.",
    )
    parser.add_argument(
        "--case-id",
        default=None,
        help="Executa apenas um caso específico.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Quantidade de resultados recuperados por pergunta.",
    )

    args = parser.parse_args()

    if args.max_cases is not None and args.max_cases < 1:
        parser.error(
            "--max-cases deve ser maior que zero.",
        )

    if args.top_k < 1:
        parser.error(
            "--top-k deve ser maior que zero.",
        )

    return args


def _configure_stdout() -> None:
    if hasattr(
        sys.stdout,
        "reconfigure",
    ):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )


def _select_cases(
    cases: list[RagEvaluationCase],
    *,
    max_cases: int | None,
    case_id: str | None,
) -> list[RagEvaluationCase]:
    selected_cases = cases

    if case_id is not None:
        selected_cases = [case for case in selected_cases if case.id == case_id]

        if not selected_cases:
            raise ValueError(
                f"Caso RAG não encontrado: {case_id}",
            )

    if max_cases is not None:
        selected_cases = selected_cases[:max_cases]

    return selected_cases


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
