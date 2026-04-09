"""Audio processor — validates MP3/WAV audio files for embedding."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp3", ".wav"}
MIME_TYPE_MAP = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

# Maximum file size: 100MB
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


@dataclass
class AudioItem:
    """A validated audio file ready for embedding."""

    audio_bytes: bytes
    mime_type: str
    filename: str
    chunk_index: int = 0


def get_audio_extension(filename: str) -> str:
    """Extract and validate the file extension."""
    lower = filename.lower()
    for ext in SUPPORTED_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    raise ValueError(
        f"Unsupported audio format for file '{filename}'. "
        f"Supported extensions: {SUPPORTED_EXTENSIONS}"
    )


def process_audio(audio_bytes: bytes, filename: str) -> AudioItem:
    """
    Validate an audio file and return an AudioItem ready for embedding.
    Audio is embedded natively — no transcription.
    """
    if len(audio_bytes) == 0:
        raise ValueError(f"Audio file '{filename}' is empty.")

    if len(audio_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Audio file '{filename}' is too large ({len(audio_bytes) / 1024 / 1024:.1f} MB). "
            f"Maximum allowed: {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB."
        )

    ext = get_audio_extension(filename)
    mime_type = MIME_TYPE_MAP[ext]

    logger.info(
        "Validated audio: filename=%s mime_type=%s size=%d bytes",
        filename,
        mime_type,
        len(audio_bytes),
    )

    return AudioItem(
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        filename=filename,
        chunk_index=0,
    )
