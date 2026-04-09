"""Shared Euri/OpenAI client — used for both embedding and LLM calls."""

import logging
from functools import lru_cache

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_euri_client() -> OpenAI:
    """Return a cached OpenAI client pointed at the Euri base URL."""
    settings = get_settings()
    logger.info("Creating Euri client with base_url=%s", settings.euri_base_url)
    return OpenAI(
        api_key=settings.euri_api_key,
        base_url=settings.euri_base_url,
    )
