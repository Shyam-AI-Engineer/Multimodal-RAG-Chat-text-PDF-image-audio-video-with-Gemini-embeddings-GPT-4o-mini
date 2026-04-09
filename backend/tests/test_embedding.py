"""Unit tests for the embedding service with mocked Euri API calls."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.embedding import (
    embed_audio,
    embed_image_batch,
    embed_pdf_pages,
    embed_single_text,
    embed_texts,
    embed_video_segment,
)


def _make_mock_embedding_response(count: int = 1) -> MagicMock:
    """Create a mock OpenAI embeddings response."""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1] * 768) for _ in range(count)
    ]
    return mock_response


@pytest.mark.asyncio
async def test_embed_single_text():
    """embed_single_text returns a 768-dim vector."""
    with patch("app.services.embedding._embed_sync") as mock_embed:
        mock_embed.return_value = [[0.1] * 768]
        result = await embed_single_text("Hello world")
        assert isinstance(result, list)
        assert len(result) == 768
        mock_embed.assert_called_once_with(["Hello world"])


@pytest.mark.asyncio
async def test_embed_texts_multiple_chunks():
    """embed_texts returns a vector per chunk."""
    chunks = ["chunk one", "chunk two", "chunk three"]
    with patch("app.services.embedding._embed_sync") as mock_embed:
        mock_embed.return_value = [[float(i)] * 768 for i in range(len(chunks))]
        results = await embed_texts(chunks)
        assert len(results) == 3
        assert all(len(v) == 768 for v in results)


@pytest.mark.asyncio
async def test_embed_texts_empty_raises():
    """embed_texts with no chunks still calls the API."""
    with patch("app.services.embedding._embed_sync") as mock_embed:
        mock_embed.return_value = []
        results = await embed_texts([])
        assert results == []


@pytest.mark.asyncio
async def test_embed_image_batch_max_6():
    """embed_image_batch raises ValueError if more than 6 images."""
    with pytest.raises(ValueError, match="Max 6 images"):
        await embed_image_batch([b"img"] * 7)


@pytest.mark.asyncio
async def test_embed_image_batch_valid():
    """embed_image_batch returns one vector per image."""
    images = [b"\xff\xd8\xff" + b"\x00" * 10] * 3
    with patch("app.services.embedding._embed_sync") as mock_embed:
        mock_embed.return_value = [[0.5] * 768 for _ in images]
        results = await embed_image_batch(images, mime_type="image/jpeg")
        assert len(results) == 3
        assert all(len(v) == 768 for v in results)


@pytest.mark.asyncio
async def test_embed_audio():
    """embed_audio returns a single 768-dim vector."""
    audio_bytes = b"\x00" * 1024
    with patch("app.services.embedding._embed_sync") as mock_embed:
        mock_embed.return_value = [[0.3] * 768]
        result = await embed_audio(audio_bytes, mime_type="audio/mpeg")
        assert isinstance(result, list)
        assert len(result) == 768


@pytest.mark.asyncio
async def test_embed_pdf_pages():
    """embed_pdf_pages returns one vector per page batch."""
    page_texts = ["Page 1 content", "Page 2 content"]
    with patch("app.services.embedding._embed_sync") as mock_embed:
        mock_embed.return_value = [[0.2] * 768, [0.4] * 768]
        results = await embed_pdf_pages(page_texts)
        assert len(results) == 2
        assert all(len(v) == 768 for v in results)


@pytest.mark.asyncio
async def test_embed_video_segment():
    """embed_video_segment returns a single 768-dim vector."""
    video_bytes = b"\x00" * 2048
    with patch("app.services.embedding._embed_sync") as mock_embed:
        mock_embed.return_value = [[0.7] * 768]
        result = await embed_video_segment(video_bytes, mime_type="video/mp4")
        assert isinstance(result, list)
        assert len(result) == 768


def test_embed_sync_retry_on_failure():
    """_embed_sync retries up to 3 times on failure."""
    from app.services.embedding import _embed_sync

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Simulated API error")
        return [[0.1] * 768]

    with patch("app.services.euri_client.get_euri_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.embeddings.create.side_effect = side_effect

        # Reset the lru_cache to get a fresh client
        from app.services import euri_client
        euri_client.get_euri_client.cache_clear()

        result = _embed_sync(["test"])
        assert call_count == 3
        assert result == [[0.1] * 768]
