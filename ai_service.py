"""Provider-neutral, validated AI generation service."""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from config import settings
from utils import logger, safe_json_loads


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class AIServiceError(RuntimeError):
    """Raised when an AI provider cannot produce a valid response."""


class AIProvider(ABC):
    """Interface implemented by supported language-model providers."""

    model_name: str

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, json_schema: dict) -> str:
        """Generate a JSON response matching the supplied schema."""


class GeminiProvider(AIProvider):
    """Google Gemini implementation using the current google-genai SDK."""

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise AIServiceError("GEMINI_API_KEY tanımlı değil.")
        from google import genai

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model

    def generate(self, system_prompt: str, user_prompt: str, json_schema: dict) -> str:
        """Request schema-constrained JSON from Gemini."""
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
                response_mime_type="application/json",
                response_json_schema=json_schema,
            ),
        )
        if not response.text:
            raise AIServiceError("Gemini boş yanıt döndürdü.")
        return response.text


class GroqProvider(AIProvider):
    """Groq implementation using Llama 3 JSON object mode."""

    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise AIServiceError("GROQ_API_KEY tanımlı değil.")
        from groq import Groq

        self._client = Groq(api_key=settings.groq_api_key)
        self.model_name = settings.groq_model

    def generate(self, system_prompt: str, user_prompt: str, json_schema: dict) -> str:
        """Request a JSON object from Groq and Llama 3."""
        schema_instruction = "\nYanıtın şu JSON şemasına uymalıdır:\n" + str(
            json_schema
        )
        completion = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt + schema_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content
        if not content:
            raise AIServiceError("Groq boş yanıt döndürdü.")
        return content


class AIService:
    """Validate provider output with Pydantic and retry transient failures."""

    def __init__(self, provider_name: str | None = None, max_retries: int = 2) -> None:
        self.provider_name = (provider_name or settings.default_ai_provider).lower()
        provider_types: dict[str, type[AIProvider]] = {
            "gemini": GeminiProvider,
            "groq": GroqProvider,
        }
        provider_type = provider_types.get(self.provider_name)
        if provider_type is None:
            raise AIServiceError(f"Desteklenmeyen AI sağlayıcısı: {self.provider_name}")
        self.provider = provider_type()
        self.max_retries = max_retries

    @property
    def model_name(self) -> str:
        """Return the configured provider model identifier."""
        return self.provider.model_name

    def generate_structured(
        self,
        operation: str,
        system_prompt: str,
        user_prompt: str,
        schema: type[SchemaT],
    ) -> SchemaT:
        """Generate, parse and validate a structured response."""
        prompt_hash = hashlib.sha256(user_prompt.encode("utf-8")).hexdigest()[:12]
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            started = time.perf_counter()
            logger.info(
                "ai_start operation=%s provider=%s model=%s attempt=%s "
                "prompt_chars=%s prompt_hash=%s",
                operation,
                self.provider_name,
                self.model_name,
                attempt,
                len(user_prompt),
                prompt_hash,
            )
            try:
                raw_response = self.provider.generate(
                    system_prompt,
                    user_prompt,
                    schema.model_json_schema(),
                )
                parsed = safe_json_loads(raw_response)
                result = schema.model_validate(parsed)
                logger.info(
                    "ai_success operation=%s duration_ms=%s response_chars=%s",
                    operation,
                    round((time.perf_counter() - started) * 1000),
                    len(raw_response),
                )
                return result
            except Exception as exc:
                last_error = exc
                logger.error(
                    "ai_failure operation=%s provider=%s attempt=%s error_type=%s "
                    "error=%s",
                    operation,
                    self.provider_name,
                    attempt,
                    type(exc).__name__,
                    str(exc)[:500],
                    exc_info=True,
                )
                if attempt <= self.max_retries:
                    time.sleep(min(2 ** (attempt - 1), 4))
        raise AIServiceError(
            f"{self.provider_name.title()} geçerli bir yanıt üretemedi: {last_error}"
        ) from last_error
