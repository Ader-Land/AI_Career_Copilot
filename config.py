"""Application configuration and platform-independent paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _secret_or_env(name: str, default: str = "") -> str:
    """Read a setting from environment, then Streamlit secrets when available."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        return str(st.secrets.get(name, default))
    except (ImportError, FileNotFoundError, KeyError, RuntimeError):
        return default


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable runtime settings."""

    app_name: str = "AI Career Copilot"
    app_version: str = "1.0.0"
    gemini_api_key: str = _secret_or_env("GEMINI_API_KEY")
    groq_api_key: str = _secret_or_env("GROQ_API_KEY")
    gemini_model: str = _secret_or_env("GEMINI_MODEL", "gemini-2.5-flash")
    groq_model: str = _secret_or_env("GROQ_MODEL", "llama-3.3-70b-versatile")
    default_ai_provider: str = _secret_or_env("DEFAULT_AI_PROVIDER", "gemini")
    database_url: str = _secret_or_env(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'career_copilot.db').as_posix()}"
    )
    max_upload_mb: int = int(_secret_or_env("MAX_UPLOAD_MB", "10"))
    log_level: str = _secret_or_env("LOG_LEVEL", "INFO")

    @property
    def uploads_dir(self) -> Path:
        """Return the upload directory."""
        return BASE_DIR / "uploads"

    @property
    def reports_dir(self) -> Path:
        """Return the generated-report directory."""
        return BASE_DIR / "reports"

    @property
    def logs_dir(self) -> Path:
        """Return the log directory."""
        return BASE_DIR / "logs"

    def ensure_directories(self) -> None:
        """Create runtime directories if they do not exist."""
        for directory in (self.uploads_dir, self.reports_dir, self.logs_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def has_provider_key(self, provider: str) -> bool:
        """Return whether the selected provider has an API key."""
        keys: dict[str, Any] = {
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_key,
        }
        return bool(keys.get(provider.lower()))


settings = Settings()
settings.ensure_directories()
