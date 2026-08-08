from dataclasses import dataclass

from app.knowledge.search_backend import KnowledgeSearchBackend


@dataclass(frozen=True)
class ApplicationResources:
    """Recursos inicializados no ciclo de vida da aplicação."""

    knowledge_search_backend: KnowledgeSearchBackend
