import asyncio

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas.tickets import TicketClassificationInput
from app.services.ticket_classifier import TicketClassifierService


async def main() -> None:
    """Executa uma classificação real para validar o serviço."""

    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY não foi configurada no arquivo .env.",
        )

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY está vazia no arquivo .env.",
        )

    ticket = TicketClassificationInput(
        title="Não consigo acessar minha conta",
        description=(
            "Após redefinir minha senha, o sistema continua informando "
            "que minhas credenciais são inválidas. Preciso acessar o "
            "sistema para trabalhar hoje."
        ),
    )

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        classifier = TicketClassifierService(
            client=client,
            model=settings.openai_model,
        )

        result = await classifier.classify(ticket)

    print(f"Modelo: {result.model}")
    print("")
    print(result.raw_output)


if __name__ == "__main__":
    asyncio.run(main())
