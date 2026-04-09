"""Test configuration — sets up environment variables for testing."""

import os

import pytest

# Set placeholder env vars so config doesn't fail validation during tests
os.environ.setdefault("EURI_API_KEY", "test_euri_key_for_unit_tests")
os.environ.setdefault("PINECONE_API_KEY", "test_pinecone_key_for_unit_tests")
os.environ.setdefault("PINECONE_INDEX_NAME", "rag-multimodal-test")
os.environ.setdefault("EURI_BASE_URL", "https://api.euron.one/api/v1/euri")
os.environ.setdefault("EURI_EMBEDDING_MODEL", "gemini-embedding-2-preview")
os.environ.setdefault("EURI_LLM_MODEL", "gpt-4o-mini")

# Clear the lru_cache so tests get fresh settings
from app.config import get_settings
from app.services import euri_client

get_settings.cache_clear()
euri_client.get_euri_client.cache_clear()
