"""Configuration module — loads and validates environment variables."""

import os
from functools import lru_cache

from dotenv import load_dotenv

# Load .env from the backend directory (parent of app/)
_backend_dir = os.path.dirname(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(_backend_dir, ".env"))


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.euri_api_key: str = os.environ.get("EURI_API_KEY", "")
        self.euri_base_url: str = os.environ.get(
            "EURI_BASE_URL", "https://api.euron.one/api/v1/euri"
        )
        self.euri_embedding_model: str = os.environ.get(
            "EURI_EMBEDDING_MODEL", "gemini-embedding-2-preview"
        )
        self.euri_llm_model: str = os.environ.get("EURI_LLM_MODEL", "gpt-4o-mini")
        self.pinecone_api_key: str = os.environ.get("PINECONE_API_KEY", "")
        self.pinecone_index_name: str = os.environ.get("PINECONE_INDEX_NAME", "rag-multimodal")

        # Embedding settings
        self.embedding_dimensions: int = 768
        self.embedding_chunk_size: int = 1024
        self.embedding_chunk_overlap: int = 256

        # Pinecone settings
        self.pinecone_metric: str = "cosine"
        self.pinecone_cloud: str = "aws"
        self.pinecone_region: str = "us-east-1"
        self.pinecone_upsert_batch_size: int = 100
        self.pinecone_default_top_k: int = 5

        # LLM settings
        self.llm_temperature: float = 0.3
        self.llm_max_tokens: int = 2048

        # Processing limits
        self.max_images_per_batch: int = 6
        self.max_pdf_pages_per_batch: int = 6
        self.max_video_seconds: int = 120


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
