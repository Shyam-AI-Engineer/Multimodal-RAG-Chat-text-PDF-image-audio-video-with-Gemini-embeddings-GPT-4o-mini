"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ingest, query
from app.services.vectorstore import get_vectorstore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize services on startup."""
    logger.info("Starting Multimodal RAG API...")
    try:
        vs = get_vectorstore()
        await vs.initialize()
        logger.info("Vectorstore initialized successfully.")
    except Exception as exc:
        logger.warning(f"Vectorstore initialization failed (will retry on first request): {exc}")
    yield
    logger.info("Shutting down Multimodal RAG API.")


app = FastAPI(
    title="Multimodal RAG API",
    description="RAG system supporting text, PDF, image, audio, and video",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server and any production origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, tags=["query"])


@app.get("/health", tags=["utility"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "multimodal-rag-api"}


@app.get("/ingested", tags=["utility"])
async def list_ingested() -> dict:
    """List all ingested files with metadata."""
    vs = get_vectorstore()
    files = await vs.list_ingested_files()
    return {"files": files, "total": len(files)}


@app.delete("/ingested", tags=["utility"])
async def delete_ingested(source_type: str, source_file: str) -> dict:
    """Delete all vectors for a specific file from Pinecone."""
    vs = get_vectorstore()
    if vs._index is None:
        await vs.initialize()
    deleted = await vs.delete_file(source_type=source_type, source_file=source_file)
    return {"deleted": deleted, "source_type": source_type, "source_file": source_file}
