from fastapi import FastAPI

from app.api.exception_handlers import (
    register_exception_handlers,
)
from app.api.router import api_router
from app.core.config import get_settings


def create_application() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""

    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        description=(
            "Serviço responsável pelas funcionalidades de inteligência artificial."
        ),
        version=settings.app_version,
    )

    application.include_router(api_router)
    register_exception_handlers(application)

    return application


app = create_application()
