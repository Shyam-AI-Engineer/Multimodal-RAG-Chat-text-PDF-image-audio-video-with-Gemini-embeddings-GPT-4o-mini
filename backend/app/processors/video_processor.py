"""Video processor — validates MP4/MOV files and segments into 120-second clips."""

import logging
import math
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp4", ".mov"}
MIME_TYPE_MAP = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}

# Maximum file size: 500MB
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024
MAX_SEGMENT_SECONDS = 120


@dataclass
class VideoSegment:
    """A video segment (up to 120 seconds) ready for embedding."""

    video_bytes: bytes
    mime_type: str
    filename: str
    segment_index: int
    chunk_index: int


def get_video_extension(filename: str) -> str:
    """Extract and validate the file extension."""
    lower = filename.lower()
    for ext in SUPPORTED_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    raise ValueError(
        f"Unsupported video format for file '{filename}'. "
        f"Supported extensions: {SUPPORTED_EXTENSIONS}"
    )


def estimate_segments(file_size_bytes: int, mime_type: str) -> int:
    """
    Estimate the number of 120-second segments based on file size.
    Uses a rough bitrate estimate: ~1 Mbps for standard video.
    This is a fallback when we cannot probe the actual duration.
    """
    # Rough estimate: 1 Mbps average bitrate
    estimated_bitrate_bps = 1_000_000
    estimated_duration_seconds = (file_size_bytes * 8) / estimated_bitrate_bps
    num_segments = max(1, math.ceil(estimated_duration_seconds / MAX_SEGMENT_SECONDS))
    return num_segments


def process_video(video_bytes: bytes, filename: str) -> list[VideoSegment]:
    """
    Validate a video file and split it into segments.

    Since segmenting video without ffmpeg requires a binary dependency,
    we use the following strategy:
    - If the estimated duration is <= 120s, treat the whole file as one segment.
    - If larger, attempt byte-range splitting (rough approximation).

    For production use, install ffmpeg and use subprocess to split precisely.
    Returns a list of VideoSegment objects.
    """
    if len(video_bytes) == 0:
        raise ValueError(f"Video file '{filename}' is empty.")

    if len(video_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Video file '{filename}' is too large "
            f"({len(video_bytes) / 1024 / 1024:.1f} MB). "
            f"Maximum allowed: {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB."
        )

    ext = get_video_extension(filename)
    mime_type = MIME_TYPE_MAP[ext]
    file_size_mb = len(video_bytes) / 1024 / 1024

    logger.info(
        "Processing video: filename=%s mime_type=%s size=%.1fMB",
        filename,
        mime_type,
        file_size_mb,
    )

    # Try to use ffprobe/ffmpeg for accurate segmentation if available
    segments = _try_ffmpeg_segment(video_bytes, filename, mime_type)
    if segments:
        return segments

    # Fallback: treat entire file as one segment (or rough byte-split)
    num_segments = estimate_segments(len(video_bytes), mime_type)

    if num_segments <= 1:
        logger.info("Video '%s' treated as single segment.", filename)
        return [
            VideoSegment(
                video_bytes=video_bytes,
                mime_type=mime_type,
                filename=filename,
                segment_index=0,
                chunk_index=0,
            )
        ]

    # Rough byte splitting — not frame-accurate, but works as approximation
    logger.warning(
        "Video '%s' may be longer than 120s. Splitting into ~%d segments by byte range.",
        filename,
        num_segments,
    )
    segment_size = len(video_bytes) // num_segments
    result: list[VideoSegment] = []
    for i in range(num_segments):
        start = i * segment_size
        end = start + segment_size if i < num_segments - 1 else len(video_bytes)
        result.append(
            VideoSegment(
                video_bytes=video_bytes[start:end],
                mime_type=mime_type,
                filename=filename,
                segment_index=i,
                chunk_index=i,
            )
        )

    return result


def _get_ffmpeg_exe() -> str | None:
    """Return the path to the bundled ffmpeg binary, or None if unavailable."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _delete_file(path: str, retries: int = 5, delay: float = 0.2) -> None:
    """Delete a file, retrying on Windows file-lock errors."""
    import time
    for _ in range(retries):
        try:
            if os.path.exists(path):
                os.unlink(path)
            return
        except OSError:
            time.sleep(delay)


def extract_frames_as_jpeg(video_bytes: bytes, filename: str, max_frames: int = 6) -> list[bytes]:
    """
    Extract evenly-spaced key frames from a video as JPEG bytes.
    Runs the bundled ffmpeg binary directly via subprocess — works on any codec
    that ffmpeg supports (H.264, H.265, VP9, screen recordings, etc.).
    Returns an empty list if extraction fails for any reason.
    """
    import re
    import subprocess
    import tempfile

    ffmpeg_exe = _get_ffmpeg_exe()
    if not ffmpeg_exe:
        logger.warning("ffmpeg binary not found; cannot extract frames from '%s'", filename)
        return []

    tmp_in: str | None = None
    frame_paths: list[str] = []

    try:
        suffix = os.path.splitext(filename)[-1] or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(video_bytes)
            tmp_in = f.name

        # --- Step 1: probe duration from ffmpeg stderr ---
        probe = subprocess.run(
            [ffmpeg_exe, "-i", tmp_in],
            capture_output=True, text=True, timeout=30,
        )
        # ffmpeg prints: "  Duration: HH:MM:SS.ss," to stderr
        duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr)
        if duration_match:
            h, m, s = duration_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)
        else:
            duration = 60.0  # fallback: assume 60 s
            logger.warning("Could not determine duration of '%s'; assuming 60s", filename)

        logger.info("Video '%s' duration=%.1fs, extracting up to %d frames", filename, duration, max_frames)

        # --- Step 2: extract one JPEG per evenly-spaced timestamp ---
        interval = duration / (max_frames + 1)
        frames: list[bytes] = []

        for i in range(1, max_frames + 1):
            timestamp = i * interval
            if timestamp >= duration:
                break

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fout:
                frame_path = fout.name
            frame_paths.append(frame_path)

            result = subprocess.run(
                [
                    ffmpeg_exe, "-y",
                    "-ss", f"{timestamp:.3f}",
                    "-i", tmp_in,
                    "-vframes", "1",
                    "-q:v", "2",
                    "-f", "image2",
                    frame_path,
                ],
                capture_output=True, timeout=30,
            )

            if result.returncode == 0 and os.path.exists(frame_path):
                data = open(frame_path, "rb").read()
                if data:
                    frames.append(data)
                    logger.debug("Extracted frame %d at t=%.1fs (%d bytes)", i, timestamp, len(data))

        logger.info("Extracted %d/%d frame(s) from '%s'", len(frames), max_frames, filename)
        return frames

    except Exception as exc:
        logger.warning("Frame extraction failed for '%s': %s", filename, exc)
        return []

    finally:
        if tmp_in:
            _delete_file(tmp_in)
        for fp in frame_paths:
            _delete_file(fp)


def _try_ffmpeg_segment(
    video_bytes: bytes, filename: str, mime_type: str
) -> list[VideoSegment] | None:
    """
    Attempt to use ffmpeg for accurate video segmentation.
    Returns None if ffmpeg is not available.
    """
    try:
        import subprocess
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
            tmp_in.write(video_bytes)
            tmp_in_path = tmp_in.name

        try:
            # Get duration with ffprobe
            probe_result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    tmp_in_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if probe_result.returncode != 0:
                return None

            duration = float(probe_result.stdout.strip())
            num_segments = max(1, math.ceil(duration / MAX_SEGMENT_SECONDS))
            logger.info(
                "Video '%s' duration=%.1fs, splitting into %d segment(s)",
                filename,
                duration,
                num_segments,
            )

            segments: list[VideoSegment] = []
            for i in range(num_segments):
                start_time = i * MAX_SEGMENT_SECONDS
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_out:
                    tmp_out_path = tmp_out.name

                try:
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-i", tmp_in_path,
                            "-ss", str(start_time),
                            "-t", str(MAX_SEGMENT_SECONDS),
                            "-c", "copy",
                            tmp_out_path,
                        ],
                        capture_output=True,
                        timeout=120,
                        check=True,
                    )
                    with open(tmp_out_path, "rb") as f:
                        seg_bytes = f.read()
                    segments.append(
                        VideoSegment(
                            video_bytes=seg_bytes,
                            mime_type=mime_type,
                            filename=filename,
                            segment_index=i,
                            chunk_index=i,
                        )
                    )
                finally:
                    if os.path.exists(tmp_out_path):
                        os.unlink(tmp_out_path)

            return segments

        finally:
            if os.path.exists(tmp_in_path):
                os.unlink(tmp_in_path)

    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        # ffmpeg not available or failed
        return None
