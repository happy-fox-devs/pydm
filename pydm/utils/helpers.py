"""Utility helpers for PyDM."""

import math
from datetime import timedelta


def format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string (e.g., 1.5 GB)."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    i = min(i, len(units) - 1)
    size = size_bytes / (1024 ** i)
    return f"{size:.1f} {units[i]}" if i > 0 else f"{int(size)} {units[i]}"


def format_speed(speed_bytes: float) -> str:
    """Format download speed into a human-readable string (e.g., 2.3 MB/s)."""
    if speed_bytes <= 0:
        return "0 B/s"
    return f"{format_size(int(speed_bytes))}/s"


def format_eta(seconds: float) -> str:
    """Format ETA seconds into HH:MM:SS or a readable string."""
    if seconds <= 0 or seconds == float("inf"):
        return "∞"
    td = timedelta(seconds=int(seconds))
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_progress(progress: float) -> str:
    """Format progress as percentage string."""
    return f"{progress:.1f}%"


def truncate_filename(name: str, max_length: int = 45) -> str:
    """Truncate a filename for display, keeping the extension visible."""
    if len(name) <= max_length:
        return name
    ext_pos = name.rfind(".")
    if ext_pos > 0:
        ext = name[ext_pos:]
        base = name[: max_length - len(ext) - 3]
        return f"{base}...{ext}"
    return name[: max_length - 3] + "..."
