from collections.abc import Sequence
from typing import Protocol

from app.schemas.knowledge import KnowledgeSearchMatch


class KnowledgeSearchBackend(Protocol):
    """Contrato de leitura para mecanismos de busca semântica."""

    @property
    def size(self) -> int:
        """Retorna a quantidade de artigos disponíveis."""

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        """Recupera os artigos semanticamente mais próximos."""
