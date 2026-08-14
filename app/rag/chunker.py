from collections.abc import Sequence
from re import sub

from app.schemas.knowledge import KnowledgeArticle
from app.schemas.rag import RagChunk

MIN_RAG_CHUNK_SIZE_CHARACTERS = 500
MAX_RAG_CHUNK_SIZE_CHARACTERS = 10_000


class RagTextChunker:
    """Divide artigos em chunks rastreáveis e determinísticos."""

    def __init__(
        self,
        *,
        chunk_size: int,
        overlap: int,
    ) -> None:
        if (
            chunk_size < MIN_RAG_CHUNK_SIZE_CHARACTERS
            or chunk_size > MAX_RAG_CHUNK_SIZE_CHARACTERS
        ):
            raise ValueError(
                "chunk_size deve estar entre 500 e 10000.",
            )

        if overlap < 0:
            raise ValueError(
                "overlap deve ser maior ou igual a zero.",
            )

        if overlap >= chunk_size:
            raise ValueError(
                "overlap deve ser menor que chunk_size.",
            )

        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk_article(
        self,
        article: KnowledgeArticle,
    ) -> list[RagChunk]:
        """Divide um artigo preservando sua origem."""

        content = normalize_chunk_content(
            article.content,
        )

        if len(content) <= self._chunk_size:
            return [
                _build_chunk(
                    article,
                    chunk_index=0,
                    content=content,
                ),
            ]

        chunks: list[RagChunk] = []
        current_chunk = ""

        for unit in _split_content_units(
            content,
            chunk_size=self._chunk_size,
        ):
            candidate = _append_unit(
                current_chunk,
                unit,
            )

            if len(candidate) <= self._chunk_size:
                current_chunk = candidate
                continue

            if current_chunk:
                chunks.append(
                    _build_chunk(
                        article,
                        chunk_index=len(chunks),
                        content=current_chunk,
                    ),
                )

            carry = _overlap_suffix(
                current_chunk,
                overlap=self._overlap,
            )
            current_chunk = _append_unit(
                carry,
                unit,
            )

            if len(current_chunk) > self._chunk_size:
                current_chunk = unit

        if current_chunk:
            chunks.append(
                _build_chunk(
                    article,
                    chunk_index=len(chunks),
                    content=current_chunk,
                ),
            )

        return chunks

    def chunk_articles(
        self,
        articles: Sequence[KnowledgeArticle],
    ) -> list[RagChunk]:
        """Divide vários artigos preservando a ordem recebida."""

        chunks: list[RagChunk] = []

        for article in articles:
            chunks.extend(
                self.chunk_article(
                    article,
                ),
            )

        return chunks


def normalize_chunk_content(
    content: str,
) -> str:
    """Normaliza quebras sem alterar semanticamente o texto."""

    normalized = content.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    return sub(
        r"\n{3,}",
        "\n\n",
        normalized.strip(),
    )


def _build_chunk(
    article: KnowledgeArticle,
    *,
    chunk_index: int,
    content: str,
) -> RagChunk:
    return RagChunk(
        article_id=article.id,
        title=article.title,
        category=article.category,
        chunk_index=chunk_index,
        content=content,
    )


def _split_content_units(
    content: str,
    *,
    chunk_size: int,
) -> list[str]:
    units: list[str] = []

    for paragraph in content.split(
        "\n\n",
    ):
        normalized_paragraph = paragraph.strip()

        if not normalized_paragraph:
            continue

        units.extend(
            _split_oversized_text(
                normalized_paragraph,
                chunk_size=chunk_size,
            ),
        )

    return units


def _split_oversized_text(
    text: str,
    *,
    chunk_size: int,
) -> list[str]:
    if len(text) <= chunk_size:
        return [
            text,
        ]

    line_units = _split_by_separator(
        text,
        separator="\n",
        chunk_size=chunk_size,
    )

    if all(len(unit) <= chunk_size for unit in line_units):
        return line_units

    word_units: list[str] = []

    for line_unit in line_units:
        word_units.extend(
            _split_by_separator(
                line_unit,
                separator=" ",
                chunk_size=chunk_size,
            ),
        )

    char_units: list[str] = []

    for word_unit in word_units:
        if len(word_unit) <= chunk_size:
            char_units.append(
                word_unit,
            )
            continue

        char_units.extend(
            word_unit[start : start + chunk_size]
            for start in range(
                0,
                len(word_unit),
                chunk_size,
            )
        )

    return char_units


def _split_by_separator(
    text: str,
    *,
    separator: str,
    chunk_size: int,
) -> list[str]:
    pieces = [
        piece.strip()
        for piece in text.split(
            separator,
        )
        if piece.strip()
    ]
    units: list[str] = []
    current = ""

    for piece in pieces:
        candidate = _append_with_separator(
            current,
            piece,
            separator=separator,
        )

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            units.append(
                current,
            )

        current = piece

    if current:
        units.append(
            current,
        )

    return units


def _append_unit(
    current: str,
    unit: str,
) -> str:
    return _append_with_separator(
        current,
        unit,
        separator="\n\n",
    )


def _append_with_separator(
    current: str,
    piece: str,
    *,
    separator: str,
) -> str:
    if not current:
        return piece

    return f"{current}{separator}{piece}"


def _overlap_suffix(
    text: str,
    *,
    overlap: int,
) -> str:
    if overlap == 0 or not text:
        return ""

    if len(text) <= overlap:
        return text

    start = len(text) - overlap
    whitespace_start = _find_next_whitespace_boundary(
        text,
        start,
    )

    return text[whitespace_start:].strip()


def _find_next_whitespace_boundary(
    text: str,
    start: int,
) -> int:
    for index in range(
        start,
        len(text),
    ):
        if text[index].isspace():
            return index + 1

    return start
