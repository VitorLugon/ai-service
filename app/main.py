from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from app.api.exception_handlers import (
    register_exception_handlers,
)
from app.api.router import api_router
from app.core.app_state import ApplicationResources
from app.core.config import Settings, get_settings
from app.knowledge.chroma_runtime import load_persisted_knowledge_backend
from app.knowledge.search_backend import KnowledgeSearchBackend


def create_application(
    *,
    settings: Settings | None = None,
    knowledge_search_backend: KnowledgeSearchBackend | None = None,
) -> FastAPI:
    """Cria e configura a aplicação FastAPI."""

    application_settings = settings or get_settings()

    application = FastAPI(
        title=application_settings.app_name,
        description=(
            "Serviço responsável pelas funcionalidades de inteligência artificial."
        ),
        version=application_settings.app_version,
        lifespan=_build_lifespan(
            settings=application_settings,
            knowledge_search_backend=knowledge_search_backend,
        ),
    )

    application.include_router(api_router)
    register_exception_handlers(application)

    if settings is not None:
        application.dependency_overrides[get_settings] = lambda: application_settings

    return application


def _build_lifespan(
    *,
    settings: Settings,
    knowledge_search_backend: KnowledgeSearchBackend | None,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(
        application: FastAPI,
    ) -> AsyncIterator[None]:
        preconfigured_resources = getattr(
            application.state,
            "resources",
            None,
        )

        if preconfigured_resources is None:
            backend = knowledge_search_backend or load_persisted_knowledge_backend(
                settings,
            )
            application.state.resources = ApplicationResources(
                knowledge_search_backend=backend,
            )

        try:
            yield
        finally:
            if preconfigured_resources is None:
                application.state._state.pop(
                    "resources",
                    None,
                )

    return lifespan


app = create_application()
