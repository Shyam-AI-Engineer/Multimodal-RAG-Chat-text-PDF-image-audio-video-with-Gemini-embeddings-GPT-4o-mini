"""Image processor — validates PNG/JPEG images and batches them for embedding."""

import io
import logging
from dataclasses import dataclass

from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"PNG", "JPEG"}
SUPPORTED_MIME_TYPES = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "JPG": "image/jpeg",
}
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@dataclass
class ImageItem:
    """A single validated image ready for embedding."""

    image_bytes: bytes
    mime_type: str
    filename: str
    chunk_index: int


@dataclass
class ImageBatch:
    """A batch of up to 6 images."""

    items: list[ImageItem]
    batch_index: int


def validate_image(image_bytes: bytes, filename: str) -> str:
    """
    Validate that the image is PNG or JPEG and return its MIME type.
    Raises ValueError for unsupported formats.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        fmt = img.format
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported image format '{fmt}' for file '{filename}'. "
                f"Supported: {SUPPORTED_FORMATS}"
            )
        return SUPPORTED_MIME_TYPES.get(fmt, "image/jpeg")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Failed to open image '{filename}': {exc}") from exc


def process_images(
    image_files: list[tuple[bytes, str]],
) -> list[ImageBatch]:
    """
    Validate and batch a list of (image_bytes, filename) tuples.
    Returns a list of ImageBatch objects (each batch has max 6 images).
    """
    settings = get_settings()
    max_per_batch = settings.max_images_per_batch

    validated: list[ImageItem] = []
    for chunk_idx, (img_bytes, filename) in enumerate(image_files):
        try:
            mime_type = validate_image(img_bytes, filename)
            validated.append(
                ImageItem(
                    image_bytes=img_bytes,
                    mime_type=mime_type,
                    filename=filename,
                    chunk_index=chunk_idx,
                )
            )
            logger.info("Validated image: filename=%s mime_type=%s", filename, mime_type)
        except ValueError as exc:
            logger.error("Image validation failed: %s", exc)
            raise

    batches: list[ImageBatch] = []
    for batch_idx, start in enumerate(range(0, len(validated), max_per_batch)):
        batch_items = validated[start : start + max_per_batch]
        batches.append(ImageBatch(items=batch_items, batch_index=batch_idx))
        logger.info(
            "Image batch %d: %d image(s)", batch_idx, len(batch_items)
        )

    return batches
