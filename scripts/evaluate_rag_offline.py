import asyncio
from pathlib import Path

from app.evaluation.rag_dataset import load_rag_evaluation_cases
from app.knowledge.loader import load_knowledge_articles
from app.rag.context_builder import RagContextBuilder
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchMatch
from app.schemas.rag import RagGenerationResult
from app.services.rag_answer import RagAnswerComposer
from app.services.rag_evaluator import (
    RagEvaluationPipelineOutput,
    RagEvaluator,
)

KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")
RAG_EVALUATION_DATASET_PATH = Path("evaluation/rag_cases.json")


class OfflineRagEvaluationPipeline:
    """Pipeline determinístico para validar a avaliação RAG sem rede."""

    def __init__(
        self,
        articles: list[KnowledgeArticle],
    ) -> None:
        self._articles_by_id = {article.id: article for article in articles}

    async def run(
        self,
        question: str,
    ) -> RagEvaluationPipelineOutput:
        matching_case = _cases_by_question[question]

        matches = [
            KnowledgeSearchMatch(
                article=self._articles_by_id[article_id],
                score=1.0 - (index * 0.01),
            )
            for index, article_id in enumerate(
                matching_case.relevant_article_ids,
            )
        ]
        context = RagContextBuilder(
            max_characters=12_000,
        ).build(
            matches,
        )
        generation = RagGenerationResult(
            answer=_fake_answer_for_case(
                matching_case,
            ),
            model="offline-deterministic",
        )
        answer = RagAnswerComposer().compose(
            generation=generation,
            context=context,
        )

        return RagEvaluationPipelineOutput(
            retrieved_article_ids=[match.article.id for match in matches],
            answer=answer,
        )


async def main() -> None:
    """Executa avaliação RAG offline com dataset versionado e fakes."""

    articles = load_knowledge_articles(
        KNOWLEDGE_BASE_PATH,
    )
    cases = load_rag_evaluation_cases(
        RAG_EVALUATION_DATASET_PATH,
        known_article_ids={article.id for article in articles},
    )

    global _cases_by_question
    _cases_by_question = {case.question: case for case in cases}

    evaluator = RagEvaluator(
        OfflineRagEvaluationPipeline(
            articles,
        ),
    )
    report = await evaluator.evaluate(
        cases,
    )

    print_report(
        report,
    )


def _fake_answer_for_case(
    case,
) -> str:
    if not case.relevant_article_ids:
        return "Não encontrei informação suficiente na base de conhecimento."

    return "Resposta offline cobrindo: " + ", ".join(
        case.expected_answer_keywords,
    )


def print_report(
    report,
) -> None:
    print(f"Cases: {report.total_cases}")
    print(f"Answer cases: {report.answer_cases}")
    print(f"No-evidence cases: {report.insufficient_evidence_cases}")
    print()
    print(f"Retrieval hit rate: {_format_optional_rate(report.retrieval_hit_rate)}")
    print(f"Source hit rate: {_format_optional_rate(report.source_hit_rate)}")
    print(
        "Mean keyword coverage: "
        f"{_format_optional_rate(report.mean_answer_keyword_coverage)}",
    )
    print(f"Correct refusal rate: {_format_optional_rate(report.correct_refusal_rate)}")
    print(f"False refusal rate: {_format_optional_rate(report.false_refusal_rate)}")
    print(
        "Unsupported answer rate: "
        f"{_format_optional_rate(report.unsupported_answer_rate)}",
    )


def _format_optional_rate(
    value: float | None,
) -> str:
    if value is None:
        return "N/A"

    return f"{value:.4f}"


_cases_by_question = {}


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
