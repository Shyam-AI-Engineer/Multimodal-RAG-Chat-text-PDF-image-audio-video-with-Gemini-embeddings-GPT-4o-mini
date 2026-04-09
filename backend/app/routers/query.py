"""Query router — JSON and SSE streaming query endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.models.schemas import QueryRequest, QueryResponse
from app.services.rag_pipeline import run_query, run_query_stream
from app.services.vectorstore import get_vectorstore

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> QueryResponse:
    """Ask a question and receive a JSON response (non-streaming)."""
    logger.info(
        "Query request: question=%r source_type=%s top_k=%d",
        request.question,
        request.source_type,
        request.top_k,
    )

    vs = get_vectorstore()
    if vs._index is None:
        try:
            await vs.initialize()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Vectorstore unavailable: {exc}") from exc

    try:
        result = await run_query(
            question=request.question,
            source_type=request.source_type,
            top_k=request.top_k,
        )
        return result
    except Exception as exc:
        logger.error("Query failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


@router.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    """Ask a question and receive a streaming SSE response."""
    logger.info(
        "Streaming query request: question=%r source_type=%s top_k=%d",
        request.question,
        request.source_type,
        request.top_k,
    )

    vs = get_vectorstore()
    if vs._index is None:
        try:
            await vs.initialize()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Vectorstore unavailable: {exc}") from exc

    async def event_generator():
        try:
            async for chunk in run_query_stream(
                question=request.question,
                source_type=request.source_type,
                top_k=request.top_k,
            ):
                yield chunk
        except Exception as exc:
            import json
            logger.error("Streaming query failed: %s", exc)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
