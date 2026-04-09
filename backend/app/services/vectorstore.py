"""Pinecone vector store service."""

import logging
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.models.schemas import IngestedFileRecord, SourceReference, SourceType

logger = logging.getLogger(__name__)

NAMESPACE_MAP: dict[str, str] = {
    "text": "ns_text",
    "pdf": "ns_pdf",
    "image": "ns_image",
    "audio": "ns_audio",
    "video": "ns_video",
}


class VectorStore:
    """Manages all Pinecone operations."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._pc: Optional[Pinecone] = None
        self._index = None

    async def initialize(self) -> None:
        """Connect to Pinecone and ensure the index exists."""
        self._pc = Pinecone(api_key=self._settings.pinecone_api_key)

        index_name = self._settings.pinecone_index_name
        existing = [idx.name for idx in self._pc.list_indexes()]

        if index_name not in existing:
            logger.info("Creating Pinecone index '%s'...", index_name)
            self._pc.create_index(
                name=index_name,
                dimension=self._settings.embedding_dimensions,
                metric=self._settings.pinecone_metric,
                spec=ServerlessSpec(
                    cloud=self._settings.pinecone_cloud,
                    region=self._settings.pinecone_region,
                ),
            )
            logger.info("Pinecone index '%s' created.", index_name)
        else:
            logger.info("Pinecone index '%s' already exists.", index_name)

        self._index = self._pc.Index(index_name)

    def _ensure_index(self) -> None:
        if self._index is None:
            raise RuntimeError("VectorStore not initialized. Call initialize() first.")

    async def upsert_vectors(
        self,
        vectors: list[list[float]],
        source_type: SourceType,
        source_file: str,
        content_previews: list[str],
        chunk_indices: list[int],
    ) -> int:
        """
        Upsert vectors to Pinecone in batches of 100.
        Returns the number of vectors upserted.
        """
        self._ensure_index()
        namespace = NAMESPACE_MAP[source_type]
        timestamp = datetime.now(timezone.utc).isoformat()

        records = []
        for i, (vec, preview, chunk_idx) in enumerate(
            zip(vectors, content_previews, chunk_indices)
        ):
            vector_id = f"{source_type}_{source_file}_{chunk_idx}_{uuid.uuid4().hex[:8]}"
            records.append(
                {
                    "id": vector_id,
                    "values": vec,
                    "metadata": {
                        "source_type": source_type,
                        "source_file": source_file,
                        "chunk_index": chunk_idx,
                        "content_preview": preview[:200],
                        "timestamp": timestamp,
                    },
                }
            )

        batch_size = self._settings.pinecone_upsert_batch_size
        total = 0
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            self._index.upsert(vectors=batch, namespace=namespace)
            total += len(batch)
            logger.info(
                "Upserted batch of %d vectors for source_type=%s source_file=%s",
                len(batch),
                source_type,
                source_file,
            )

        return total

    async def query(
        self,
        query_vector: list[float],
        top_k: int = 5,
        source_type: Optional[SourceType] = None,
    ) -> list[SourceReference]:
        """
        Query Pinecone for the most similar vectors.
        Optionally filter by source_type namespace.
        Returns list of SourceReference objects.
        """
        self._ensure_index()

        namespaces_to_query: list[str] = (
            [NAMESPACE_MAP[source_type]]
            if source_type
            else list(NAMESPACE_MAP.values())
        )

        all_matches: list[dict] = []

        for ns in namespaces_to_query:
            result = self._index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=ns,
                include_metadata=True,
            )
            all_matches.extend(result.get("matches", []))

        # Sort by score descending and take top_k
        all_matches.sort(key=lambda m: m.get("score", 0.0), reverse=True)
        top_matches = all_matches[:top_k]

        sources: list[SourceReference] = []
        for match in top_matches:
            meta = match.get("metadata", {})
            sources.append(
                SourceReference(
                    source_type=meta.get("source_type", "text"),
                    source_file=meta.get("source_file", "unknown"),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    content_preview=meta.get("content_preview", ""),
                    score=float(match.get("score", 0.0)),
                    timestamp=meta.get("timestamp", ""),
                )
            )

        return sources

    async def delete_file(self, source_type: SourceType, source_file: str) -> int:
        """Delete all vectors for a given source_file from its namespace."""
        self._ensure_index()
        namespace = NAMESPACE_MAP.get(source_type, "ns_text")
        zero = [0.0] * self._settings.embedding_dimensions

        # Fetch all vector IDs for this file (Pinecone has no direct metadata filter delete)
        result = self._index.query(
            vector=zero,
            top_k=1000,
            namespace=namespace,
            include_metadata=True,
        )
        ids_to_delete = [
            m["id"] for m in result.get("matches", [])
            if m.get("metadata", {}).get("source_file") == source_file
        ]
        if ids_to_delete:
            self._index.delete(ids=ids_to_delete, namespace=namespace)
            logger.info("Deleted %d vectors for source_file='%s' from namespace '%s'",
                        len(ids_to_delete), source_file, namespace)
        return len(ids_to_delete)

    async def list_ingested_files(self) -> list[dict]:
        """List all ingested files by querying each namespace for stats."""
        if self._index is None:
            return []

        files: dict[str, dict] = {}

        for source_type, namespace in NAMESPACE_MAP.items():
            try:
                stats = self._index.describe_index_stats()
                ns_stats = stats.get("namespaces", {}).get(namespace, {})
                vector_count = ns_stats.get("vector_count", 0)
                if vector_count == 0:
                    continue

                # Fetch a sample to get file names (Pinecone doesn't have a direct "list" by metadata)
                # Use a zero vector query to list records
                zero_vec = [0.0] * self._settings.embedding_dimensions
                result = self._index.query(
                    vector=zero_vec,
                    top_k=min(vector_count, 100),
                    namespace=namespace,
                    include_metadata=True,
                )

                for match in result.get("matches", []):
                    meta = match.get("metadata", {})
                    sf = meta.get("source_file", "unknown")
                    key = f"{source_type}::{sf}"
                    if key not in files:
                        files[key] = {
                            "source_type": source_type,
                            "source_file": sf,
                            "chunk_count": 0,
                            "timestamp": meta.get("timestamp", ""),
                        }
                    files[key]["chunk_count"] += 1
            except Exception as exc:
                logger.warning("Could not list files for namespace %s: %s", namespace, exc)

        return list(files.values())


@lru_cache()
def get_vectorstore() -> VectorStore:
    """Return a cached VectorStore instance."""
    return VectorStore()
