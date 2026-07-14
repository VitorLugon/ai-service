from fastapi import FastAPI, status

app = FastAPI(
    title="AI Service",
    description="Serviço responsável pelas funcionalidades de inteligência artificial.",
    version="0.1.0",
)


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
)
async def health_check() -> dict[str, str]:
    """Verifica se o processo da aplicação está funcionando."""
    return {"status": "ok"}
