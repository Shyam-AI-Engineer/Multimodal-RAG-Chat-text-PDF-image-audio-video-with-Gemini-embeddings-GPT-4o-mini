"""LLM generation service via Euri API (gpt-4o-mini)."""

import base64
import json
import logging
from typing import AsyncGenerator

from app.config import get_settings
from app.models.schemas import SourceReference
from app.services.euri_client import get_euri_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based ONLY on the provided context.

Rules:
1. Answer the question using ONLY the information found in the context below.
2. If the context does not contain enough information to answer the question, say so clearly — do NOT make up information.
3. Be concise, accurate, and helpful.
4. When referencing information, you may mention the source file name.
5. Do not hallucinate facts that are not in the context."""


def _build_user_message(question: str, sources: list[SourceReference]) -> str:
    """Build the user message with retrieved context embedded."""
    context_parts: list[str] = []
    for i, src in enumerate(sources, 1):
        context_parts.append(
            f"[Source {i}] File: {src.source_file} (Type: {src.source_type}, "
            f"Chunk: {src.chunk_index})\n{src.content_preview}"
        )

    context_block = "\n\n".join(context_parts) if context_parts else "No relevant context found."
    return f"Context:\n{context_block}\n\nQuestion: {question}"


async def describe_video_frames(frames: list[bytes], filename: str) -> str:
    """
    Use the vision LLM to generate a text description of video content from extracted frames.
    Returns a rich text description suitable for embedding and retrieval.
    """
    settings = get_settings()
    client = get_euri_client()

    if not frames:
        logger.warning("No frames provided for video '%s', returning stub description.", filename)
        return f"Video file: {filename}. No frames could be extracted for analysis."

    content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"These are key frames extracted from the video '{filename}'. "
                "Provide a detailed description covering:\n"
                "1. The main topic and subject matter\n"
                "2. Key concepts, data, or information shown\n"
                "3. Any visible text, labels, charts, diagrams, or equations\n"
                "4. The overall narrative or lesson being conveyed\n\n"
                "Be thorough and specific — your description will be used to answer questions about this video."
            ),
        }
    ]

    for frame_bytes in frames[:6]:  # vision API limit: max 6 images
        b64 = base64.b64encode(frame_bytes).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    logger.info("Describing %d frame(s) from video '%s' via vision LLM", len(frames), filename)

    try:
        response = client.chat.completions.create(
            model=settings.euri_llm_model,
            messages=[{"role": "user", "content": content}],
            max_tokens=1024,
            temperature=0.1,
        )
        description = response.choices[0].message.content or ""
        logger.info("Video description for '%s': %d chars", filename, len(description))
        return description
    except Exception as exc:
        logger.error("Vision LLM description failed for '%s': %s", filename, exc)
        return f"Video file: {filename}. Content description unavailable due to error: {exc}"


async def generate_response(
    question: str,
    sources: list[SourceReference],
) -> str:
    """Generate a non-streaming LLM response based on retrieved context."""
    settings = get_settings()
    client = get_euri_client()
    user_message = _build_user_message(question, sources)

    logger.info("Generating LLM response for question (non-streaming)")

    try:
        response = client.chat.completions.create(
            model=settings.euri_llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        raise


async def stream_response(
    question: str,
    sources: list[SourceReference],
) -> AsyncGenerator[str, None]:
    """
    Generate a streaming LLM response via SSE.
    Yields SSE-formatted strings:
      data: {"content": "<token>"}\n\n
      data: {"sources": [...]}\n\n
      data: [DONE]\n\n
    """
    settings = get_settings()
    client = get_euri_client()
    user_message = _build_user_message(question, sources)

    logger.info("Generating streaming LLM response for question")

    try:
        stream = client.chat.completions.create(
            model=settings.euri_llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield f"data: {json.dumps({'content': delta.content})}\n\n"

        # Send source references after the stream completes
        sources_payload = [src.model_dump() for src in sources]
        yield f"data: {json.dumps({'sources': sources_payload})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as exc:
        logger.error("Streaming LLM generation failed: %s", exc)
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"
