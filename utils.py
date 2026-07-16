"""Security, logging, formatting and serialization utilities."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from config import settings


LOGGER_NAME = "career_copilot"


def setup_logging() -> logging.Logger:
    """Configure rotating activity and error logs once."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    activity_handler = RotatingFileHandler(
        settings.logs_dir / "app.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    activity_handler.setLevel(logging.INFO)
    activity_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        settings.logs_dir / "errors.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    logger.addHandler(activity_handler)
    logger.addHandler(error_handler)
    logger.propagate = False
    return logger


logger = setup_logging()


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 digest of byte content."""
    return hashlib.sha256(data).hexdigest()


def sanitize_filename(filename: str) -> str:
    """Return a traversal-safe ASCII-ish filename."""
    base_name = Path(filename).name
    normalized = unicodedata.normalize("NFKD", base_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_name).strip("._")
    return safe_name[:180] or "cv_document"


def safe_json_loads(raw_text: str) -> dict[str, Any]:
    """Parse an AI JSON response, tolerating Markdown code fences."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("AI yanıtında geçerli JSON bulunamadı.") from None
        data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("AI yanıtının kök öğesi bir JSON nesnesi olmalıdır.")
    return data


def compact_text(text: str, max_chars: int = 80_000) -> str:
    """Normalize whitespace and constrain text sent to providers."""
    normalized = text.replace("\x00", " ")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    return normalized[:max_chars]


def format_list(items: list[str]) -> str:
    """Format a list for human-readable display."""
    cleaned = [item.strip() for item in items if item and item.strip()]
    return "\n".join(f"• {item}" for item in cleaned) or "Belirtilmemiş"
