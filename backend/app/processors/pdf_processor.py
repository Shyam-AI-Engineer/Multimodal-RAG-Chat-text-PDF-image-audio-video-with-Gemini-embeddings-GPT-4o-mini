"""PDF processor — splits PDF into page batches and extracts text."""

import io
import logging
from dataclasses import dataclass

import PyPDF2

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PDFPageBatch:
    """A batch of up to 6 PDF pages with combined text."""

    text: str
    page_start: int
    page_end: int
    chunk_index: int
    content_preview: str


def process_pdf(pdf_bytes: bytes, source_file: str) -> list[PDFPageBatch]:
    """
    Extract text from a PDF and split into batches of max 6 pages.
    Returns a list of PDFPageBatch objects.
    """
    settings = get_settings()
    max_pages = settings.max_pdf_pages_per_batch

    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)
    logger.info("Processing PDF source=%s total_pages=%d", source_file, total_pages)

    batches: list[PDFPageBatch] = []
    chunk_index = 0

    for batch_start in range(0, total_pages, max_pages):
        batch_end = min(batch_start + max_pages, total_pages)
        page_texts: list[str] = []

        for page_num in range(batch_start, batch_end):
            page = reader.pages[page_num]
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                logger.warning(
                    "Failed to extract text from page %d of %s: %s",
                    page_num,
                    source_file,
                    exc,
                )
                text = ""
            page_texts.append(text)

        combined_text = "\n\n".join(page_texts).strip()
        if not combined_text:
            logger.warning(
                "No text extracted from pages %d-%d of %s (may be image-based PDF)",
                batch_start,
                batch_end - 1,
                source_file,
            )

        batches.append(
            PDFPageBatch(
                text=combined_text or f"[PDF pages {batch_start + 1}–{batch_end} — no extractable text]",
                page_start=batch_start,
                page_end=batch_end - 1,
                chunk_index=chunk_index,
                content_preview=(combined_text or "")[:200],
            )
        )
        chunk_index += 1

    logger.info(
        "PDF source=%s produced %d batch(es) of up to %d pages",
        source_file,
        len(batches),
        max_pages,
    )
    return batches
