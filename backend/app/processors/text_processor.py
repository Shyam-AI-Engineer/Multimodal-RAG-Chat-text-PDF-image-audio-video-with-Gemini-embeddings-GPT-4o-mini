"""Text processor — chunks text for embedding."""

import logging
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A processed text chunk ready for embedding."""

    text: str
    chunk_index: int
    content_preview: str


def chunk_text(text: str, source_name: str = "text") -> list[TextChunk]:
    """
    Split text into chunks using RecursiveCharacterTextSplitter.
    chunk_size=1024 tokens (approximated as characters * 0.75),
    chunk_overlap=256 tokens.
    Returns a list of TextChunk objects.
    """
    settings = get_settings()

    if not text.strip():
        logger.warning("Empty text provided for chunking: source=%s", source_name)
        return []

    # langchain splitter uses character counts — approximate tokens by chars
    # 1 token ≈ 4 characters (conservative estimate)
    chars_per_token = 4
    chunk_size_chars = settings.embedding_chunk_size * chars_per_token
    chunk_overlap_chars = settings.embedding_chunk_overlap * chars_per_token

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_chars,
        chunk_overlap=chunk_overlap_chars,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    raw_chunks = splitter.split_text(text)
    logger.info(
        "Chunked source=%s into %d chunks (chunk_size=%d chars, overlap=%d chars)",
        source_name,
        len(raw_chunks),
        chunk_size_chars,
        chunk_overlap_chars,
    )

    return [
        TextChunk(
            text=chunk,
            chunk_index=i,
            content_preview=chunk[:200],
        )
        for i, chunk in enumerate(raw_chunks)
    ]
