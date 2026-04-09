"""End-to-end RAG pipeline tests with mocked dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import QueryResponse, SourceReference


def _make_source(score: float = 0.9) -> SourceReference:
    return SourceReference(
        source_type="text",
        source_file="test.txt",
        chunk_index=0,
        content_preview="Sample content for testing",
        score=score,
        timestamp="2024-01-01T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_run_query_success():
    """run_query returns QueryResponse with answer and sources."""
    from app.services.rag_pipeline import run_query

    mock_sources = [_make_source(0.9), _make_source(0.8)]

    with (
        patch("app.services.rag_pipeline.embed_single_text", new_callable=AsyncMock) as mock_embed,
        patch("app.services.rag_pipeline.get_vectorstore") as mock_vs_factory,
        patch("app.services.rag_pipeline.generate_response", new_callable=AsyncMock) as mock_gen,
    ):
        mock_embed.return_value = [0.1] * 768
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(return_value=mock_sources)
        mock_vs_factory.return_value = mock_vs
        mock_gen.return_value = "This is the answer based on the context."

        result = await run_query(question="What is RAG?", top_k=5)

        assert isinstance(result, QueryResponse)
        assert result.answer == "This is the answer based on the context."
        assert len(result.sources) == 2
        assert result.question == "What is RAG?"
        mock_embed.assert_called_once_with("What is RAG?")
        mock_vs.query.assert_called_once_with(
            query_vector=[0.1] * 768,
            top_k=5,
            source_type=None,
        )


@pytest.mark.asyncio
async def test_run_query_with_source_type_filter():
    """run_query passes source_type filter to vectorstore."""
    from app.services.rag_pipeline import run_query

    with (
        patch("app.services.rag_pipeline.embed_single_text", new_callable=AsyncMock) as mock_embed,
        patch("app.services.rag_pipeline.get_vectorstore") as mock_vs_factory,
        patch("app.services.rag_pipeline.generate_response", new_callable=AsyncMock) as mock_gen,
    ):
        mock_embed.return_value = [0.1] * 768
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(return_value=[_make_source()])
        mock_vs_factory.return_value = mock_vs
        mock_gen.return_value = "Answer from PDF sources."

        result = await run_query(question="Summarize", source_type="pdf", top_k=3)

        mock_vs.query.assert_called_once_with(
            query_vector=[0.1] * 768,
            top_k=3,
            source_type="pdf",
        )
        assert result.answer == "Answer from PDF sources."


@pytest.mark.asyncio
async def test_run_query_no_results():
    """run_query still calls LLM even when no context is found."""
    from app.services.rag_pipeline import run_query

    with (
        patch("app.services.rag_pipeline.embed_single_text", new_callable=AsyncMock) as mock_embed,
        patch("app.services.rag_pipeline.get_vectorstore") as mock_vs_factory,
        patch("app.services.rag_pipeline.generate_response", new_callable=AsyncMock) as mock_gen,
    ):
        mock_embed.return_value = [0.0] * 768
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(return_value=[])  # No results
        mock_vs_factory.return_value = mock_vs
        mock_gen.return_value = "I don't have enough context to answer that question."

        result = await run_query(question="Unknown topic?")

        assert len(result.sources) == 0
        assert "context" in result.answer.lower() or "don't" in result.answer.lower()


@pytest.mark.asyncio
async def test_run_query_stream_yields_sse_events():
    """run_query_stream yields SSE-formatted data chunks."""
    from app.services.rag_pipeline import run_query_stream

    async def mock_stream(*args, **kwargs):
        yield 'data: {"content": "Hello"}\n\n'
        yield 'data: {"content": " world"}\n\n'
        yield 'data: {"sources": []}\n\n'
        yield "data: [DONE]\n\n"

    with (
        patch("app.services.rag_pipeline.embed_single_text", new_callable=AsyncMock) as mock_embed,
        patch("app.services.rag_pipeline.get_vectorstore") as mock_vs_factory,
        patch("app.services.rag_pipeline.stream_response") as mock_stream_response,
    ):
        mock_embed.return_value = [0.1] * 768
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(return_value=[])
        mock_vs_factory.return_value = mock_vs
        mock_stream_response.return_value = mock_stream()

        chunks = []
        async for chunk in run_query_stream(question="Test query"):
            chunks.append(chunk)

        assert len(chunks) == 4
        assert chunks[0] == 'data: {"content": "Hello"}\n\n'
        assert chunks[-1] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_embed_query_error_propagates():
    """Embedding errors propagate up from the pipeline."""
    from app.services.rag_pipeline import run_query

    with patch(
        "app.services.rag_pipeline.embed_single_text",
        new_callable=AsyncMock,
        side_effect=Exception("Euri API unreachable"),
    ):
        with pytest.raises(Exception, match="Euri API unreachable"):
            await run_query(question="Will this fail?")
