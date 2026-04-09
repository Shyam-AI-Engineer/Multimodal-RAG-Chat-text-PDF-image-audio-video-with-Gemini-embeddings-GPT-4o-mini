"""Ingestion router — POST endpoints for all modalities."""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.models.schemas import IngestResponse, TextIngestRequest
from app.processors.audio_processor import process_audio
from app.processors.image_processor import SUPPORTED_EXTENSIONS as IMAGE_EXTS
from app.processors.image_processor import process_images
from app.processors.pdf_processor import process_pdf
from app.processors.text_processor import chunk_text
from app.processors.video_processor import SUPPORTED_EXTENSIONS as VIDEO_EXTS
from app.processors.video_processor import extract_frames_as_jpeg, process_video
from app.services.embedding import (
    embed_audio,
    embed_image_batch,
    embed_pdf_pages,
    embed_texts,
)
from app.services.llm import describe_video_frames
from app.services.vectorstore import get_vectorstore

router = APIRouter()
logger = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/text", response_model=IngestResponse)
async def ingest_text(
    request: TextIngestRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestResponse:
    """Ingest raw text by chunking and embedding it."""
    logger.info("Ingesting text: source_name=%s length=%d", request.source_name, len(request.text))

    try:
        chunks = chunk_text(request.text, source_name=request.source_name)
        if not chunks:
            raise HTTPException(status_code=400, detail="Text produced no chunks after processing.")

        texts = [c.text for c in chunks]
        vectors = await embed_texts(texts)

        vs = get_vectorstore()
        if vs._index is None:
            await vs.initialize()

        count = await vs.upsert_vectors(
            vectors=vectors,
            source_type="text",
            source_file=request.source_name,
            content_previews=[c.content_preview for c in chunks],
            chunk_indices=[c.chunk_index for c in chunks],
        )

        return IngestResponse(
            status="success",
            message=f"Successfully ingested {count} text chunk(s).",
            source_type="text",
            source_file=request.source_name,
            chunks_stored=count,
            timestamp=_timestamp(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Text ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Text ingestion failed: {exc}") from exc


@router.post("/pdf", response_model=IngestResponse)
async def ingest_pdf(
    file: Annotated[UploadFile, File(description="PDF file to ingest")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestResponse:
    """Ingest a PDF file by splitting into page batches and embedding."""
    filename = file.filename or "unknown.pdf"
    logger.info("Ingesting PDF: filename=%s", filename)

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="PDF file is empty.")

        batches = process_pdf(pdf_bytes, source_file=filename)
        if not batches:
            raise HTTPException(status_code=400, detail="PDF produced no processable content.")

        texts = [b.text for b in batches]
        vectors = await embed_pdf_pages(texts)

        vs = get_vectorstore()
        if vs._index is None:
            await vs.initialize()

        count = await vs.upsert_vectors(
            vectors=vectors,
            source_type="pdf",
            source_file=filename,
            content_previews=[b.content_preview for b in batches],
            chunk_indices=[b.chunk_index for b in batches],
        )

        return IngestResponse(
            status="success",
            message=f"Successfully ingested PDF with {count} batch(es).",
            source_type="pdf",
            source_file=filename,
            chunks_stored=count,
            timestamp=_timestamp(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("PDF ingestion failed for %s: %s", filename, exc)
        raise HTTPException(status_code=500, detail=f"PDF ingestion failed: {exc}") from exc


@router.post("/image", response_model=IngestResponse)
async def ingest_image(
    files: Annotated[list[UploadFile], File(description="Image file(s) to ingest — PNG or JPEG")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestResponse:
    """Ingest one or more images (PNG/JPEG) by embedding them."""
    if not files:
        raise HTTPException(status_code=400, detail="No image files provided.")

    filenames = [f.filename or f"image_{i}.jpg" for i, f in enumerate(files)]
    logger.info("Ingesting %d image(s): %s", len(files), filenames)

    # Validate extensions
    for fn in filenames:
        ext = "." + fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
        if ext not in IMAGE_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format: {fn}. Supported: {IMAGE_EXTS}",
            )

    try:
        image_data: list[tuple[bytes, str]] = []
        for upload, fn in zip(files, filenames):
            img_bytes = await upload.read()
            image_data.append((img_bytes, fn))

        batches = process_images(image_data)
        total_stored = 0
        vs = get_vectorstore()
        if vs._index is None:
            await vs.initialize()

        for batch in batches:
            batch_bytes = [item.image_bytes for item in batch.items]
            mime_type = batch.items[0].mime_type if batch.items else "image/jpeg"
            vectors = await embed_image_batch(batch_bytes, mime_type=mime_type)

            count = await vs.upsert_vectors(
                vectors=vectors,
                source_type="image",
                source_file=",".join(item.filename for item in batch.items),
                content_previews=["" for _ in batch.items],
                chunk_indices=[item.chunk_index for item in batch.items],
            )
            total_stored += count

        return IngestResponse(
            status="success",
            message=f"Successfully ingested {total_stored} image vector(s).",
            source_type="image",
            source_file=",".join(filenames),
            chunks_stored=total_stored,
            timestamp=_timestamp(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Image ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Image ingestion failed: {exc}") from exc


@router.post("/audio", response_model=IngestResponse)
async def ingest_audio(
    file: Annotated[UploadFile, File(description="Audio file — MP3 or WAV")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestResponse:
    """Ingest an audio file by embedding it natively (no transcription)."""
    filename = file.filename or "audio.mp3"
    logger.info("Ingesting audio: filename=%s", filename)

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {".mp3", ".wav"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {filename}. Supported: .mp3, .wav",
        )

    try:
        audio_bytes = await file.read()
        audio_item = process_audio(audio_bytes, filename)
        vector = await embed_audio(audio_item.audio_bytes, mime_type=audio_item.mime_type)

        vs = get_vectorstore()
        if vs._index is None:
            await vs.initialize()

        count = await vs.upsert_vectors(
            vectors=[vector],
            source_type="audio",
            source_file=filename,
            content_previews=[""],
            chunk_indices=[0],
        )

        return IngestResponse(
            status="success",
            message=f"Successfully ingested audio file.",
            source_type="audio",
            source_file=filename,
            chunks_stored=count,
            timestamp=_timestamp(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Audio ingestion failed for %s: %s", filename, exc)
        raise HTTPException(status_code=500, detail=f"Audio ingestion failed: {exc}") from exc


@router.post("/video", response_model=IngestResponse)
async def ingest_video(
    file: Annotated[UploadFile, File(description="Video file — MP4 or MOV")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestResponse:
    """Ingest a video file by segmenting and embedding each 120s clip."""
    filename = file.filename or "video.mp4"
    logger.info("Ingesting video: filename=%s", filename)

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in VIDEO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format: {filename}. Supported: {VIDEO_EXTS}",
        )

    try:
        video_bytes = await file.read()
        segments = process_video(video_bytes, filename)

        vs = get_vectorstore()
        if vs._index is None:
            await vs.initialize()

        total_stored = 0
        for segment in segments:
            # Extract frames → describe with vision LLM → embed text description
            frames = extract_frames_as_jpeg(segment.video_bytes, filename)
            description = await describe_video_frames(frames, filename)

            # Chunk the description text and embed it as text vectors
            chunks = chunk_text(description, source_name=filename)
            if not chunks:
                logger.warning("Video segment %d of '%s' produced no text chunks.", segment.chunk_index, filename)
                continue

            texts = [c.text for c in chunks]
            vectors = await embed_texts(texts)

            count = await vs.upsert_vectors(
                vectors=vectors,
                source_type="video",
                source_file=filename,
                content_previews=[c.content_preview for c in chunks],
                chunk_indices=[segment.chunk_index * 1000 + c.chunk_index for c in chunks],
            )
            total_stored += count

        return IngestResponse(
            status="success",
            message=f"Successfully ingested video with {total_stored} text chunk(s) from frame descriptions.",
            source_type="video",
            source_file=filename,
            chunks_stored=total_stored,
            timestamp=_timestamp(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Video ingestion failed for %s: %s", filename, exc)
        raise HTTPException(status_code=500, detail=f"Video ingestion failed: {exc}") from exc
