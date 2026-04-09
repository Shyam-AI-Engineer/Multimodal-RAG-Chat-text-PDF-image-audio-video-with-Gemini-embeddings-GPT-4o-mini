"""RAG pipeline — orchestrates embed → retrieve → generate."""

import logging
from typing import AsyncGenerator, Optional

from app.models.schemas import QueryResponse, SourceReference, SourceType
from app.services.embedding import embed_single_text
from app.services.llm import generate_response, stream_response
from app.services.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


async def run_query(
    question: str,
    source_type: Optional[SourceType] = None,
    top_k: int = 5,
) -> QueryResponse:
    """
    Full RAG pipeline (non-streaming):
    1. Embed the question
    2. Search Pinecone
    3. Build prompt with context
    4. Call LLM
    5. Return answer + sources
    """
    logger.info("RAG query (non-streaming): question=%r source_type=%s top_k=%d", question, source_type, top_k)

    # Step 1: Embed the question
    query_vector = await embed_single_text(question)

    # Step 2: Retrieve relevant chunks from Pinecone
    vs = get_vectorstore()
    sources: list[SourceReference] = await vs.query(
        query_vector=query_vector,
        top_k=top_k,
        source_type=source_type,
    )
    logger.info("Retrieved %d source chunks", len(sources))

    # Step 3-4: Generate answer
    answer = await generate_response(question=question, sources=sources)

    return QueryResponse(answer=answer, sources=sources, question=question)


async def run_query_stream(
    question: str,
    source_type: Optional[SourceType] = None,
    top_k: int = 5,
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline (streaming SSE):
    1. Embed the question
    2. Search Pinecone
    3. Build prompt with context
    4. Stream LLM tokens via SSE
    """
    logger.info("RAG query (streaming): question=%r source_type=%s top_k=%d", question, source_type, top_k)

    # Step 1: Embed the question
    query_vector = await embed_single_text(question)

    # Step 2: Retrieve relevant chunks
    vs = get_vectorstore()
    sources: list[SourceReference] = await vs.query(
        query_vector=query_vector,
        top_k=top_k,
        source_type=source_type,
    )
    logger.info("Retrieved %d source chunks for streaming response", len(sources))

    # Step 3-4: Stream the LLM response
    async for sse_chunk in stream_response(question=question, sources=sources):
        yield sse_chunk
