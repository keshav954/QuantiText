"""
LLM provider factory.

Selects the appropriate provider based on LLM_PROVIDER config:
- "gemini"  → always use Gemini (cloud)
- "ollama"  → always use Ollama (local)
- "auto"    → use Ollama for daily ops, fallback to Gemini for complex tasks
              or when Ollama is unavailable
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import settings
from app.services.llm.base import LLMProvider, TaskType

log = logging.getLogger(__name__)


class AutoProvider(LLMProvider):
    """
    Intelligent provider that routes to Ollama (fast, free) by default
    and falls back to Gemini (powerful, paid) when needed.

    Routing logic:
    - SQL_GENERATION     → Ollama (Qwen excels at SQL)
    - TEXT_EXPLANATION    → Ollama first, Gemini fallback
    - ANOMALY_ANALYSIS   → Ollama first, Gemini fallback
    - RECOMMENDATION     → Gemini (needs stronger reasoning)
    - SUMMARIZATION      → Ollama (straightforward task)
    - GENERAL            → Ollama first, Gemini fallback
    """

    def __init__(self) -> None:
        from app.services.llm.gemini_provider import GeminiProvider
        from app.services.llm.ollama_provider import OllamaProvider

        self._ollama = OllamaProvider()
        self._gemini = GeminiProvider()

    @property
    def provider_name(self) -> str:
        return "auto"

    @property
    def is_available(self) -> bool:
        return self._ollama.is_available or self._gemini.is_available

    # Tasks that PREFER Gemini due to complexity
    _PREFER_GEMINI: set[TaskType] = {TaskType.RECOMMENDATION}

    def _pick_provider(self, task_type: TaskType) -> LLMProvider:
        """Pick the best available provider for this task type."""
        if task_type in self._PREFER_GEMINI:
            if self._gemini.is_available:
                log.debug("Auto: routing %s to Gemini (preferred)", task_type)
                return self._gemini
            if self._ollama.is_available:
                log.debug("Auto: Gemini unavailable, routing %s to Ollama", task_type)
                return self._ollama
        else:
            if self._ollama.is_available:
                log.debug("Auto: routing %s to Ollama (local)", task_type)
                return self._ollama
            if self._gemini.is_available:
                log.debug("Auto: Ollama unavailable, routing %s to Gemini", task_type)
                return self._gemini

        raise RuntimeError(
            "No LLM provider available. Ensure either GEMINI_API_KEY is set "
            "or Ollama is running at OLLAMA_BASE_URL."
        )

    async def generate(
        self,
        prompt,
        *,
        system_prompt=None,
        context=None,
        temperature=0.1,
        max_tokens=2048,
        task_type=TaskType.GENERAL,
    ):
        provider = self._pick_provider(task_type)
        try:
            return await provider.generate(
                prompt,
                system_prompt=system_prompt,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
                task_type=task_type,
            )
        except Exception:
            # Fallback to the other provider
            fallback = self._gemini if provider is self._ollama else self._ollama
            if fallback.is_available:
                log.warning(
                    "Primary %s failed, falling back to %s",
                    provider.provider_name,
                    fallback.provider_name,
                )
                return await fallback.generate(
                    prompt,
                    system_prompt=system_prompt,
                    context=context,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    task_type=task_type,
                )
            raise

    async def generate_sql(self, question, *, schema_context, examples=None, dialect="postgresql"):
        provider = self._pick_provider(TaskType.SQL_GENERATION)
        try:
            return await provider.generate_sql(
                question,
                schema_context=schema_context,
                examples=examples,
                dialect=dialect,
            )
        except Exception:
            fallback = self._gemini if provider is self._ollama else self._ollama
            if fallback.is_available:
                log.warning(
                    "SQL gen failed on %s, falling back to %s",
                    provider.provider_name,
                    fallback.provider_name,
                )
                return await fallback.generate_sql(
                    question,
                    schema_context=schema_context,
                    examples=examples,
                    dialect=dialect,
                )
            raise

    async def stream(
        self,
        prompt,
        *,
        system_prompt=None,
        context=None,
        temperature=0.3,
        task_type=TaskType.GENERAL,
    ):
        provider = self._pick_provider(task_type)
        async for chunk in provider.stream(
            prompt,
            system_prompt=system_prompt,
            context=context,
            temperature=temperature,
            task_type=task_type,
        ):
            yield chunk


@lru_cache(maxsize=1)
def get_provider() -> LLMProvider:
    """
    Return the configured LLM provider (singleton).

    Reads LLM_PROVIDER from settings:
    - "gemini" → GeminiProvider
    - "ollama" → OllamaProvider
    - "auto"   → AutoProvider (smart routing with fallback)
    """
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "gemini":
        from app.services.llm.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        log.info("LLM provider: Gemini (cloud) — model=%s", settings.LLM_MODEL)

    elif provider_name == "ollama":
        from app.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        log.info(
            "LLM provider: Ollama (local) — sql=%s, text=%s",
            settings.OLLAMA_SQL_MODEL,
            settings.OLLAMA_TEXT_MODEL,
        )

    elif provider_name == "auto":
        provider = AutoProvider()
        log.info("LLM provider: Auto (Ollama preferred, Gemini fallback)")

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{provider_name}'. Must be one of: gemini, ollama, auto"
        )

    return provider
