from app.schemas.rag import (
    RagAnswer,
    RagAnswerSource,
    RagContext,
    RagGenerationResult,
    RagSource,
)


class RagAnswerComposer:
    """Compõe a resposta final preservando provenance controlada pela aplicação."""

    def compose(
        self,
        *,
        generation: RagGenerationResult,
        context: RagContext,
    ) -> RagAnswer:
        sources = _answer_sources_from_context(
            context,
        )

        return RagAnswer(
            answer=generation.answer,
            sources=sources,
            source_count=len(sources),
        )


def _answer_sources_from_context(
    context: RagContext,
) -> list[RagAnswerSource]:
    sources: list[RagAnswerSource] = []
    seen_source_ids: set[str] = set()

    for source in context.sources:
        source_id = _source_id(
            source,
        )

        if source_id in seen_source_ids:
            continue

        seen_source_ids.add(
            source_id,
        )
        sources.append(
            RagAnswerSource(
                source_id=source_id,
                article_id=source.article_id,
                chunk_id=source.chunk_id,
                title=source.title,
                category=source.category,
                rank=source.rank,
            ),
        )

    return sources


def _source_id(
    source: RagSource,
) -> str:
    if source.chunk_id is not None:
        return source.chunk_id

    return source.article_id
