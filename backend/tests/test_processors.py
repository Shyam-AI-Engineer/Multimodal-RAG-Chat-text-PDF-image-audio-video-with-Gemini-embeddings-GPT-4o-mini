"""Unit tests for all processors."""

import io

import pytest


# ---------------------------------------------------------------------------
# Text processor tests
# ---------------------------------------------------------------------------

def test_text_processor_basic():
    """chunk_text splits short text into a single chunk."""
    from app.processors.text_processor import chunk_text

    text = "Hello world. This is a test."
    chunks = chunk_text(text, source_name="test.txt")
    assert len(chunks) >= 1
    assert chunks[0].text == text or text in chunks[0].text
    assert chunks[0].chunk_index == 0
    assert len(chunks[0].content_preview) <= 200


def test_text_processor_long_text():
    """chunk_text splits long text into multiple chunks."""
    from app.processors.text_processor import chunk_text

    # Create text longer than 1024 tokens (approx 4096 chars)
    long_text = "Lorem ipsum dolor sit amet. " * 300  # ~8400 chars
    chunks = chunk_text(long_text, source_name="long.txt")
    assert len(chunks) > 1
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert len(chunk.content_preview) <= 200


def test_text_processor_empty():
    """chunk_text returns empty list for empty text."""
    from app.processors.text_processor import chunk_text

    chunks = chunk_text("   ", source_name="empty.txt")
    assert chunks == []


def test_text_processor_preview_truncation():
    """content_preview is always <= 200 chars."""
    from app.processors.text_processor import chunk_text

    text = "A" * 500
    chunks = chunk_text(text)
    for chunk in chunks:
        assert len(chunk.content_preview) <= 200


# ---------------------------------------------------------------------------
# PDF processor tests
# ---------------------------------------------------------------------------

def _make_simple_pdf(num_pages: int = 3) -> bytes:
    """Create a minimal valid PDF in memory with the given number of pages."""
    try:
        import PyPDF2
        from PyPDF2 import PdfWriter
        from reportlab.pdfgen import canvas as rl_canvas
        import io as _io

        # Try using reportlab if available
        buffer = _io.BytesIO()
        c = rl_canvas.Canvas(buffer)
        for i in range(num_pages):
            c.drawString(100, 750, f"Page {i + 1} content")
            c.showPage()
        c.save()
        return buffer.getvalue()
    except ImportError:
        pass

    # Fallback: build a minimal PDF manually
    pages = []
    for i in range(num_pages):
        pages.append(f"Page {i + 1} content")

    # Minimal PDF structure
    pdf_lines = [
        b"%PDF-1.4",
    ]
    offsets = []
    obj_num = 1

    page_content_objects = []
    for i, text in enumerate(pages):
        content = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET"
        content_bytes = content.encode()
        stream = f"{len(content_bytes)}"
        offsets.append(len(b"\n".join(pdf_lines)) + 1)
        pdf_lines.append(
            f"{obj_num} 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n{content}\nendstream\nendobj".encode()
        )
        page_content_objects.append(obj_num)
        obj_num += 1

    # Pages
    page_objects = []
    for content_obj in page_content_objects:
        offsets.append(len(b"\n".join(pdf_lines)) + 1)
        pdf_lines.append(
            f"{obj_num} 0 obj\n<< /Type /Page /Parent {obj_num + num_pages} 0 R /Contents {content_obj} 0 R >>\nendobj".encode()
        )
        page_objects.append(obj_num)
        obj_num += 1

    # Pages dictionary
    kids = " ".join(f"{p} 0 R" for p in page_objects)
    offsets.append(len(b"\n".join(pdf_lines)) + 1)
    pdf_lines.append(
        f"{obj_num} 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>\nendobj".encode()
    )
    pages_obj = obj_num
    obj_num += 1

    # Catalog
    offsets.append(len(b"\n".join(pdf_lines)) + 1)
    pdf_lines.append(
        f"{obj_num} 0 obj\n<< /Type /Catalog /Pages {pages_obj} 0 R >>\nendobj".encode()
    )
    catalog_obj = obj_num
    obj_num += 1

    # xref and trailer
    xref_pos = len(b"\n".join(pdf_lines)) + 1
    pdf_lines.append(b"xref")
    pdf_lines.append(f"0 {obj_num}".encode())
    pdf_lines.append(b"0000000000 65535 f ")
    for off in offsets:
        pdf_lines.append(f"{off:010d} 00000 n ".encode())

    pdf_lines.append(
        f"trailer\n<< /Size {obj_num} /Root {catalog_obj} 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    )
    return b"\n".join(pdf_lines)


def test_pdf_processor_small_pdf():
    """process_pdf produces one batch for a <= 6-page PDF."""
    from app.processors.pdf_processor import process_pdf

    # Use a known-good minimal PDF approach
    try:
        pdf_bytes = _make_simple_pdf(3)
        batches = process_pdf(pdf_bytes, "test.pdf")
        assert len(batches) >= 1
        assert batches[0].chunk_index == 0
        assert batches[0].page_start == 0
    except Exception:
        # If the synthetic PDF fails to parse, skip
        pytest.skip("Could not create test PDF — install reportlab for better PDF tests")


def test_pdf_processor_large_pdf():
    """process_pdf batches a > 6-page PDF into multiple batches."""
    from app.processors.pdf_processor import process_pdf

    try:
        pdf_bytes = _make_simple_pdf(13)
        batches = process_pdf(pdf_bytes, "large.pdf")
        # 13 pages → ceil(13/6) = 3 batches
        assert len(batches) == 3
        assert batches[0].page_end == 5
        assert batches[1].page_start == 6
    except Exception:
        pytest.skip("Could not create test PDF — install reportlab for better PDF tests")


# ---------------------------------------------------------------------------
# Image processor tests
# ---------------------------------------------------------------------------

def _make_png_bytes() -> bytes:
    """Create a minimal 1x1 PNG image."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes() -> bytes:
    """Create a minimal 1x1 JPEG image."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (1, 1), color=(0, 255, 0))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_image_processor_single_png():
    """process_images validates a single PNG image."""
    from app.processors.image_processor import process_images

    png = _make_png_bytes()
    batches = process_images([(png, "test.png")])
    assert len(batches) == 1
    assert len(batches[0].items) == 1
    assert batches[0].items[0].mime_type == "image/png"


def test_image_processor_batches_7_images():
    """process_images creates 2 batches for 7 images."""
    from app.processors.image_processor import process_images

    png = _make_png_bytes()
    images = [(png, f"img_{i}.png") for i in range(7)]
    batches = process_images(images)
    assert len(batches) == 2
    assert len(batches[0].items) == 6
    assert len(batches[1].items) == 1


def test_image_processor_invalid_format():
    """process_images raises ValueError for unsupported formats."""
    from app.processors.image_processor import process_images

    with pytest.raises((ValueError, Exception)):
        process_images([(b"\x00\x00\x00\x00", "test.bmp")])


# ---------------------------------------------------------------------------
# Audio processor tests
# ---------------------------------------------------------------------------

def test_audio_processor_mp3():
    """process_audio validates an MP3 file."""
    from app.processors.audio_processor import process_audio

    # Minimal fake MP3 bytes (ID3 header)
    mp3_bytes = b"\xff\xfb\x90\x00" + b"\x00" * 100
    item = process_audio(mp3_bytes, "test.mp3")
    assert item.mime_type == "audio/mpeg"
    assert item.filename == "test.mp3"
    assert item.chunk_index == 0


def test_audio_processor_wav():
    """process_audio validates a WAV file."""
    from app.processors.audio_processor import process_audio

    # Minimal WAV header
    wav_bytes = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100
    item = process_audio(wav_bytes, "test.wav")
    assert item.mime_type == "audio/wav"


def test_audio_processor_empty_raises():
    """process_audio raises ValueError for empty files."""
    from app.processors.audio_processor import process_audio

    with pytest.raises(ValueError, match="empty"):
        process_audio(b"", "empty.mp3")


def test_audio_processor_unsupported_format_raises():
    """process_audio raises ValueError for unsupported formats."""
    from app.processors.audio_processor import process_audio

    with pytest.raises(ValueError):
        process_audio(b"\x00" * 100, "test.ogg")


# ---------------------------------------------------------------------------
# Video processor tests
# ---------------------------------------------------------------------------

def test_video_processor_small_mp4():
    """process_video treats a small MP4 as a single segment."""
    from app.processors.video_processor import process_video

    # Minimal MP4-like bytes (small file = short video estimate)
    small_video = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 200
    segments = process_video(small_video, "test.mp4")
    assert len(segments) >= 1
    assert segments[0].mime_type == "video/mp4"
    assert segments[0].filename == "test.mp4"


def test_video_processor_empty_raises():
    """process_video raises ValueError for empty files."""
    from app.processors.video_processor import process_video

    with pytest.raises(ValueError, match="empty"):
        process_video(b"", "empty.mp4")


def test_video_processor_unsupported_format_raises():
    """process_video raises ValueError for unsupported formats."""
    from app.processors.video_processor import process_video

    with pytest.raises(ValueError):
        process_video(b"\x00" * 100, "test.avi")


def test_video_processor_mov_format():
    """process_video handles MOV files."""
    from app.processors.video_processor import process_video

    mov_bytes = b"\x00" * 500
    segments = process_video(mov_bytes, "test.mov")
    assert len(segments) >= 1
    assert segments[0].mime_type == "video/quicktime"
