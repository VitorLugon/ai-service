import asyncio

from openai import AsyncOpenAI

from app.core.config import get_settings


async def main() -> None:
    """Executa uma requisição mínima para validar a integração."""

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

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=20.0,
        max_retries=2,
    ) as client:
        response = await client.responses.create(
            model=settings.openai_model,
            instructions=(
                "Você é um teste de conexão. Siga exatamente o formato solicitado."
            ),
            input='Responda somente com a palavra minúscula "ok".',
        )

    print(f"Modelo: {settings.openai_model}")
    print(f"Resposta: {response.output_text.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
