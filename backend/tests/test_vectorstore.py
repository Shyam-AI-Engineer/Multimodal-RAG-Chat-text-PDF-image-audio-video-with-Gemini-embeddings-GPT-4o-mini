"""Unit tests for the vectorstore service with mocked Pinecone."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.vectorstore import VectorStore


def _make_vectorstore() -> VectorStore:
    """Create a VectorStore with a mocked index."""
    vs = VectorStore()
    vs._index = MagicMock()
    return vs


@pytest.mark.asyncio
async def test_upsert_vectors_single_batch():
    """upsert_vectors upserts all vectors in a single batch when <= 100."""
    vs = _make_vectorstore()
    vs._index.upsert = MagicMock()

    vectors = [[0.1] * 768 for _ in range(5)]
    count = await vs.upsert_vectors(
        vectors=vectors,
        source_type="text",
        source_file="test.txt",
        content_previews=["preview"] * 5,
        chunk_indices=list(range(5)),
    )

    assert count == 5
    vs._index.upsert.assert_called_once()
    call_args = vs._index.upsert.call_args
    assert len(call_args.kwargs["vectors"]) == 5
    assert call_args.kwargs["namespace"] == "ns_text"


@pytest.mark.asyncio
async def test_upsert_vectors_multiple_batches():
    """upsert_vectors splits large uploads into batches of 100."""
    vs = _make_vectorstore()
    vs._index.upsert = MagicMock()

    vectors = [[0.1] * 768 for _ in range(250)]
    count = await vs.upsert_vectors(
        vectors=vectors,
        source_type="pdf",
        source_file="large.pdf",
        content_previews=["p"] * 250,
        chunk_indices=list(range(250)),
    )

    assert count == 250
    assert vs._index.upsert.call_count == 3  # 100 + 100 + 50


@pytest.mark.asyncio
async def test_query_single_namespace():
    """query returns SourceReference objects from a single namespace."""
    vs = _make_vectorstore()
    vs._index.query = MagicMock(
        return_value={
            "matches": [
                {
                    "id": "text_file_0_abc",
                    "score": 0.95,
                    "metadata": {
                        "source_type": "text",
                        "source_file": "test.txt",
                        "chunk_index": 0,
                        "content_preview": "Hello world",
                        "timestamp": "2024-01-01T00:00:00+00:00",
                    },
                }
            ]
        }
    )

    results = await vs.query(query_vector=[0.1] * 768, top_k=5, source_type="text")

    assert len(results) == 1
    assert results[0].source_type == "text"
    assert results[0].score == 0.95
    assert results[0].source_file == "test.txt"
    # Should only query the text namespace
    assert vs._index.query.call_count == 1


@pytest.mark.asyncio
async def test_query_all_namespaces_when_no_filter():
    """query searches all 5 namespaces when source_type is None."""
    vs = _make_vectorstore()
    vs._index.query = MagicMock(return_value={"matches": []})

    results = await vs.query(query_vector=[0.1] * 768, top_k=5, source_type=None)

    assert vs._index.query.call_count == 5  # all 5 namespaces


@pytest.mark.asyncio
async def test_query_sorts_by_score():
    """query returns results sorted by score descending."""
    vs = _make_vectorstore()

    def make_match(score: float, st: str) -> dict:
        return {
            "id": f"{st}_0",
            "score": score,
            "metadata": {
                "source_type": st,
                "source_file": f"{st}_file",
                "chunk_index": 0,
                "content_preview": "",
                "timestamp": "2024-01-01T00:00:00+00:00",
            },
        }

    vs._index.query = MagicMock(
        side_effect=[
            {"matches": [make_match(0.7, "text"), make_match(0.3, "text")]},
            {"matches": [make_match(0.9, "pdf")]},
            {"matches": []},
            {"matches": []},
            {"matches": []},
        ]
    )

    results = await vs.query(query_vector=[0.1] * 768, top_k=3, source_type=None)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 0.9


@pytest.mark.asyncio
async def test_initialize_creates_index_if_missing():
    """initialize creates the Pinecone index if it doesn't exist."""
    vs = VectorStore()

    mock_pc = MagicMock()
    mock_pc.list_indexes.return_value = []  # No existing indexes
    mock_pc.create_index = MagicMock()
    mock_pc.Index = MagicMock(return_value=MagicMock())

    with patch("app.services.vectorstore.Pinecone", return_value=mock_pc):
        await vs.initialize()

    mock_pc.create_index.assert_called_once()
    assert vs._index is not None


@pytest.mark.asyncio
async def test_initialize_skips_creation_if_index_exists():
    """initialize does not create index if it already exists."""
    vs = VectorStore()

    existing_index = MagicMock()
    existing_index.name = "rag-multimodal"

    mock_pc = MagicMock()
    mock_pc.list_indexes.return_value = [existing_index]
    mock_pc.create_index = MagicMock()
    mock_pc.Index = MagicMock(return_value=MagicMock())

    with patch("app.services.vectorstore.Pinecone", return_value=mock_pc):
        await vs.initialize()

    mock_pc.create_index.assert_not_called()
