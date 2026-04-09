"""Pydantic request/response models for all API endpoints."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / common
# ---------------------------------------------------------------------------

SourceType = Literal["text", "pdf", "image", "audio", "video"]


class SourceReference(BaseModel):
    """A single retrieved source chunk reference."""

    source_type: SourceType
    source_file: str
    chunk_index: int
    content_preview: str
    score: float
    timestamp: str


# ---------------------------------------------------------------------------
# Ingestion request/response models
# ---------------------------------------------------------------------------


class TextIngestRequest(BaseModel):
    """Request body for POST /ingest/text."""

    text: str = Field(..., min_length=1, description="Raw text to ingest")
    source_name: str = Field(default="manual_input", description="Identifier for this text")


class IngestResponse(BaseModel):
    """Generic ingestion response."""

    status: Literal["success", "error"]
    message: str
    source_type: SourceType
    source_file: str
    chunks_stored: int
    timestamp: str


# ---------------------------------------------------------------------------
# Query request/response models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """Request body for POST /query and POST /query/stream."""

    question: str = Field(..., min_length=1, description="User question")
    source_type: Optional[SourceType] = Field(
        default=None, description="Optional filter by source modality"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to retrieve")


class QueryResponse(BaseModel):
    """Response for POST /query (non-streaming)."""

    answer: str
    sources: list[SourceReference]
    question: str


# ---------------------------------------------------------------------------
# Ingested files listing
# ---------------------------------------------------------------------------


class IngestedFileRecord(BaseModel):
    """Metadata record for a previously ingested file."""

    source_type: SourceType
    source_file: str
    chunk_count: int
    timestamp: str


class IngestedFilesResponse(BaseModel):
    """Response for GET /ingested."""

    files: list[IngestedFileRecord]
    total: int
