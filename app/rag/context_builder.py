from collections.abc import Sequence

from app.schemas.knowledge import KnowledgeSearchMatch
from app.schemas.rag import RagContext, RagSource, RankedRagChunk

MIN_RAG_CONTEXT_CHARACTERS = 1_000
MAX_RAG_CONTEXT_CHARACTERS = 100_000
TRUNCATION_MARKER = "[conteúdo truncado]"


class RagContextBuilder:
    """Monta contexto textual a partir dos resultados de recuperação."""

    def __init__(
        self,
        *,
        max_characters: int,
    ) -> None:
        if (
            max_characters < MIN_RAG_CONTEXT_CHARACTERS
            or max_characters > MAX_RAG_CONTEXT_CHARACTERS
        ):
            raise ValueError(
                "max_characters deve estar entre 1000 e 100000.",
            )

        self._max_characters = max_characters

    def build(
        self,
        matches: Sequence[KnowledgeSearchMatch],
    ) -> RagContext:
        """Constrói um contexto RAG preservando a ordem da recuperação."""

        if not matches:
            return RagContext(
                text="",
                sources=[],
                source_count=0,
            )

        included_sources: list[RagSource] = []
        text_parts: list[str] = []

        for index, match in enumerate(
            matches,
            start=1,
        ):
            source = _source_from_match(
                match,
                rank=index,
            )
            source_text = _format_source(
                source,
            )
            candidate_text = _join_source_texts(
                [
                    *text_parts,
                    source_text,
                ],
            )

            if len(candidate_text) <= self._max_characters:
                included_sources.append(
                    source,
                )
                text_parts.append(
                    source_text,
                )
                continue

            if not included_sources:
                included_sources.append(
                    source,
                )
                text_parts.append(
                    _truncate_first_source(
                        source,
                        max_characters=self._max_characters,
                    ),
                )

            break

        text = _join_source_texts(
            text_parts,
        )

        return RagContext(
            text=text,
            sources=included_sources,
            source_count=len(included_sources),
        )

    def build_from_chunks(
        self,
        ranked_chunks: Sequence[RankedRagChunk],
    ) -> RagContext:
        """Constrói contexto a partir de chunks já ranqueados."""

        if not ranked_chunks:
            return RagContext(
                text="",
                sources=[],
                source_count=0,
            )

        included_sources: list[RagSource] = []
        text_parts: list[str] = []
        seen_chunk_ids: set[str] = set()

        for ranked_chunk in ranked_chunks:
            chunk_id = ranked_chunk.chunk.chunk_id

            if chunk_id is None:
                raise ValueError(
                    "chunk_id deve estar preenchido no chunk ranqueado.",
                )

            if chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(
                chunk_id,
            )
            source = _source_from_ranked_chunk(
                ranked_chunk,
            )
            source_text = _format_source(
                source,
            )
            candidate_text = _join_source_texts(
                [
                    *text_parts,
                    source_text,
                ],
            )

            if len(candidate_text) <= self._max_characters:
                included_sources.append(
                    source,
                )
                text_parts.append(
                    source_text,
                )
                continue

            if not included_sources:
                included_sources.append(
                    source,
                )
                text_parts.append(
                    _truncate_first_source(
                        source,
                        max_characters=self._max_characters,
                    ),
                )

            break

        text = _join_source_texts(
            text_parts,
        )

        return RagContext(
            text=text,
            sources=included_sources,
            source_count=len(included_sources),
        )


def _source_from_match(
    match: KnowledgeSearchMatch,
    *,
    rank: int,
) -> RagSource:
    article = match.article

    return RagSource(
        article_id=article.id,
        title=article.title,
        category=article.category,
        score=match.score,
        rank=rank,
        content=article.content,
    )


def _source_from_ranked_chunk(
    ranked_chunk: RankedRagChunk,
) -> RagSource:
    chunk = ranked_chunk.chunk

    return RagSource(
        article_id=chunk.article_id,
        title=chunk.title,
        category=chunk.category,
        score=ranked_chunk.score,
        rank=ranked_chunk.rank,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
        chunk_id=chunk.chunk_id,
    )


def _format_source(
    source: RagSource,
) -> str:
    return (
        f"[SOURCE {source.rank}]\n"
        f"{_source_id_label(source)}: {source.article_id}\n"
        f"{_chunk_id_line(source)}"
        f"title: {source.title}\n"
        f"category: {source.category.value}\n"
        "content:\n"
        f"{source.content}"
    )


def _format_source_header(
    source: RagSource,
) -> str:
    return (
        f"[SOURCE {source.rank}]\n"
        f"{_source_id_label(source)}: {source.article_id}\n"
        f"{_chunk_id_line(source)}"
        f"title: {source.title}\n"
        f"category: {source.category.value}\n"
        "content:\n"
    )


def _source_id_label(
    source: RagSource,
) -> str:
    if source.chunk_id is None:
        return "id"

    return "article_id"


def _chunk_id_line(
    source: RagSource,
) -> str:
    if source.chunk_id is None:
        return ""

    return f"chunk_id: {source.chunk_id}\n"


def _truncate_first_source(
    source: RagSource,
    *,
    max_characters: int,
) -> str:
    header = _format_source_header(
        source,
    )
    marker = f"\n{TRUNCATION_MARKER}"
    available_content_length = max_characters - len(header) - len(marker)

    if available_content_length < 0:
        raise ValueError(
            "max_characters não comporta a estrutura mínima de uma fonte.",
        )

    return (header + source.content[:available_content_length].rstrip() + marker)[
        :max_characters
    ]


def _join_source_texts(
    source_texts: Sequence[str],
) -> str:
    return "\n\n".join(
        source_texts,
    )
