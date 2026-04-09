"""Embedding service — embeds all modalities via Euri API (gemini-embedding-2-preview)."""

import asyncio
import base64
import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.services.euri_client import get_euri_client

logger = logging.getLogger(__name__)


def _b64(data: bytes) -> str:
    """Encode bytes as base64 string."""
    return base64.b64encode(data).decode("utf-8")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _embed_sync(input_data: Any) -> list[list[float]]:
    """
    Synchronous embedding call with tenacity retry.

    input_data can be:
      - str  → single text chunk
      - list[str] → multiple text chunks (batched)
    """
    settings = get_settings()
    client = get_euri_client()

    response = client.embeddings.create(
        model=settings.euri_embedding_model,
        input=input_data,
        dimensions=settings.embedding_dimensions,
    )
    return [item.embedding for item in response.data]


async def embed_texts(chunks: list[str]) -> list[list[float]]:
    """
    Embed a list of text chunks.
    Each chunk should be within the 8192-token limit.
    Returns a list of 768-dimensional float vectors.
    """
    logger.info("Embedding %d text chunk(s)", len(chunks))
    loop = asyncio.get_event_loop()
    vectors = await loop.run_in_executor(None, _embed_sync, chunks)
    return vectors


async def embed_single_text(text: str) -> list[float]:
    """Embed a single text string and return its vector."""
    vectors = await embed_texts([text])
    return vectors[0]


async def embed_image_batch(image_bytes_list: list[bytes], mime_type: str = "image/jpeg") -> list[list[float]]:
    """
    Embed a batch of images (max 6 per request).
    Converts images to base64 data URIs and passes as text inputs.
    """
    if len(image_bytes_list) > 6:
        raise ValueError(f"Max 6 images per batch, got {len(image_bytes_list)}")

    logger.info("Embedding %d image(s) with mime_type=%s", len(image_bytes_list), mime_type)

    # Pass base64-encoded images as text inputs to the multimodal embedding endpoint
    # The Euri/Gemini embedding model accepts base64 data URIs
    inputs = [f"data:{mime_type};base64,{_b64(img)}" for img in image_bytes_list]

    loop = asyncio.get_event_loop()
    vectors = await loop.run_in_executor(None, _embed_sync, inputs)
    return vectors


async def embed_audio(audio_bytes: bytes, mime_type: str = "audio/mpeg") -> list[float]:
    """
    Embed audio natively (no transcription).
    Passes audio as base64 data URI.
    """
    logger.info("Embedding audio file, size=%d bytes, mime_type=%s", len(audio_bytes), mime_type)
    input_data = f"data:{mime_type};base64,{_b64(audio_bytes)}"

    loop = asyncio.get_event_loop()
    vectors = await loop.run_in_executor(None, _embed_sync, [input_data])
    return vectors[0]


async def embed_pdf_pages(pdf_pages_text: list[str]) -> list[list[float]]:
    """
    Embed PDF pages as text.
    Each batch contains at most 6 pages worth of text.
    """
    logger.info("Embedding %d PDF page chunk(s)", len(pdf_pages_text))
    return await embed_texts(pdf_pages_text)


async def embed_video_segment(video_bytes: bytes, mime_type: str = "video/mp4") -> list[float]:
    """
    Embed a video segment (max 120 seconds).
    Passes video as base64 data URI.
    """
    logger.info("Embedding video segment, size=%d bytes, mime_type=%s", len(video_bytes), mime_type)
    input_data = f"data:{mime_type};base64,{_b64(video_bytes)}"

    loop = asyncio.get_event_loop()
    vectors = await loop.run_in_executor(None, _embed_sync, [input_data])
    return vectors[0]
