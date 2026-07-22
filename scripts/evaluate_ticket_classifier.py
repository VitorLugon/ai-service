import argparse
import asyncio
import json
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.evaluation.dataset import (
    load_ticket_evaluation_cases,
)
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.evaluation import TicketEvaluationReport
from app.services.ticket_classifier import TicketClassifierService
from app.services.ticket_evaluator import TicketEvaluatorService

DEFAULT_DATASET_PATH = Path("evaluation/tickets.json")
DEFAULT_REPORT_PATH = Path(
    "reports/ticket-classification-evaluation.json",
)


def parse_arguments() -> argparse.Namespace:
    """Lê os argumentos da execução."""

    parser = argparse.ArgumentParser(
        description=("Avalia as estratégias do classificador de chamados."),
    )

    parser.add_argument(
        "--strategy",
        choices=[strategy.value for strategy in PromptStrategy],
        default=PromptStrategy.ONE_SHOT.value,
        help="Estratégia que será avaliada.",
    )
    parser.add_argument(
        "--all-strategies",
        action="store_true",
        help="Avalia zero-shot, one-shot e few-shot.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de casos executados.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Caminho do conjunto de avaliação.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Arquivo no qual o relatório será salvo.",
    )

    return parser.parse_args()


def print_report(
    report: TicketEvaluationReport,
) -> None:
    """Exibe as métricas e os casos incorretos."""

    print("")
    print("=" * 64)
    print(f"Estratégia: {report.strategy}")
    print(f"Modelo: {report.model}")
    print(f"Casos: {report.total_cases}")
    print(
        "Categoria: "
        f"{report.category_correct_count}/"
        f"{report.total_cases} "
        f"({report.category_accuracy:.1%})"
    )
    print(
        "Prioridade: "
        f"{report.priority_correct_count}/"
        f"{report.total_cases} "
        f"({report.priority_accuracy:.1%})"
    )
    print(
        "Conjunto: "
        f"{report.joint_correct_count}/"
        f"{report.total_cases} "
        f"({report.joint_accuracy:.1%})"
    )

    incorrect_results = [
        result for result in report.results if not result.joint_correct
    ]

    if not incorrect_results:
        print("Nenhuma divergência encontrada.")
        return

    print("")
    print("Divergências:")

    for result in incorrect_results:
        print(f"- {result.case_id}")
        print(
            "  Categoria: "
            f"{result.expected_category.value} -> "
            f"{result.predicted_category.value}"
        )
        print(
            "  Prioridade: "
            f"{result.expected_priority.value} -> "
            f"{result.predicted_priority.value}"
        )


async def main() -> None:
    """Executa a avaliação configurada."""

    arguments = parse_arguments()
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

    cases = load_ticket_evaluation_cases(
        arguments.dataset,
    )

    if arguments.limit is not None:
        if arguments.limit < 1:
            raise ValueError(
                "--limit deve ser maior que zero.",
            )

        cases = cases[: arguments.limit]

    if arguments.all_strategies:
        strategies = list(PromptStrategy)
    else:
        strategies = [
            PromptStrategy(arguments.strategy),
        ]

    reports: list[TicketEvaluationReport] = []

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        for strategy in strategies:
            classifier = TicketClassifierService(
                client=client,
                model=settings.openai_model,
                prompt_strategy=strategy,
            )

            evaluator = TicketEvaluatorService(
                classifier=classifier,
                strategy=strategy.value,
            )

            report = await evaluator.evaluate(cases)

            reports.append(report)
            print_report(report)

    arguments.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized_reports = [report.model_dump(mode="json") for report in reports]

    arguments.output.write_text(
        json.dumps(
            serialized_reports,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print(f"Relatório salvo em: {arguments.output}")


if __name__ == "__main__":
    asyncio.run(main())
