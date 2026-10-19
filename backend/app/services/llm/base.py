"""
LLM Provider abstract base class.

All LLM providers (Gemini, Ollama, future models) implement this interface.
This decouples business logic from the specific model vendor, allowing
zero-cost local inference with cloud fallback.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum


class TaskType(str, Enum):
    """Task categories — used by the 'auto' provider to pick the best backend."""

    SQL_GENERATION = "sql_generation"
    TEXT_EXPLANATION = "text_explanation"
    ANOMALY_ANALYSIS = "anomaly_analysis"
    RECOMMENDATION = "recommendation"
    SUMMARIZATION = "summarization"
    GENERAL = "general"


@dataclass(frozen=True)
class LLMResponse:
    """Standardised response envelope from any LLM provider."""

    text: str
    model: str
    provider: str  # "gemini" | "ollama"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


class LLMProvider(abc.ABC):
    """
    Abstract LLM provider.

    Every provider MUST implement at minimum `generate` and `generate_sql`.
    Streaming is optional — the default falls back to non-streaming generate.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g. 'gemini', 'ollama')."""

    @property
    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is currently reachable / configured."""

    # ── Core generation ──────────────────────────────────

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        context: list[dict] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        task_type: TaskType = TaskType.GENERAL,
    ) -> LLMResponse:
        """
        Generate a completion.

        Args:
            prompt: The user message / question.
            system_prompt: Optional system-level instruction.
            context: Prior conversation messages [{"role": "user"|"assistant", "content": "..."}].
            temperature: Sampling temperature (lower = more deterministic).
            max_tokens: Maximum tokens in the response.
            task_type: Hint for provider selection in 'auto' mode.
        """

    @abc.abstractmethod
    async def generate_sql(
        self,
        question: str,
        *,
        schema_context: str,
        examples: list[dict] | None = None,
        dialect: str = "postgresql",
    ) -> LLMResponse:
        """
        Generate a SQL query from a natural-language question.

        Args:
            question: The user's NL question.
            schema_context: Relevant table/view definitions and column descriptions.
            examples: Few-shot examples [{"question": "...", "sql": "..."}].
            dialect: SQL dialect hint.
        """

    # ── Specialised methods (with sensible defaults) ─────

    async def explain_anomaly(
        self,
        anomaly_data: dict,
        *,
        context_data: dict | None = None,
    ) -> LLMResponse:
        """
        Generate a 2-3 line plain-English explanation of an anomaly.
        Only uses numbers from anomaly_data — never invents figures.
        """
        prompt = self._build_anomaly_prompt(anomaly_data, context_data)
        return await self.generate(
            prompt,
            system_prompt=(
                "You are a concise business analyst. Explain the anomaly in 2-3 sentences "
                "using ONLY the numbers provided. Never invent figures. "
                "End with a brief suggested action."
            ),
            temperature=0.1,
            task_type=TaskType.ANOMALY_ANALYSIS,
        )

    async def generate_recommendation(
        self,
        context: dict,
    ) -> LLMResponse:
        """Generate an actionable recommendation from anomaly + inventory + feedback context."""
        prompt = self._build_recommendation_prompt(context)
        return await self.generate(
            prompt,
            system_prompt=(
                "You are a supply-chain advisor. Given the data below, produce a specific, "
                "actionable recommendation. Include: what action, why, expected impact, "
                "and urgency level (high/medium/low). Use ONLY the provided numbers."
            ),
            temperature=0.2,
            task_type=TaskType.RECOMMENDATION,
        )

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        context: list[dict] | None = None,
        temperature: float = 0.3,
        task_type: TaskType = TaskType.GENERAL,
    ) -> AsyncIterator[str]:
        """
        Stream tokens. Default implementation yields the full response at once.
        Providers should override for true streaming.
        """
        response = await self.generate(
            prompt,
            system_prompt=system_prompt,
            context=context,
            temperature=temperature,
            task_type=task_type,
        )
        yield response.text

    # ── Prompt builders (shared across providers) ────────

    @staticmethod
    def _build_anomaly_prompt(anomaly_data: dict, context_data: dict | None = None) -> str:
        lines = ["Anomaly detected with the following data:"]
        for k, v in anomaly_data.items():
            lines.append(f"  - {k}: {v}")
        if context_data:
            lines.append("\nAdditional context:")
            for k, v in context_data.items():
                lines.append(f"  - {k}: {v}")
        lines.append("\nExplain this anomaly and suggest what to do.")
        return "\n".join(lines)

    @staticmethod
    def _build_recommendation_prompt(context: dict) -> str:
        lines = ["Generate an actionable recommendation based on:"]
        for section, data in context.items():
            lines.append(f"\n## {section}")
            if isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"  - {k}: {v}")
            elif isinstance(data, list):
                for item in data[:10]:  # Cap to avoid context overflow
                    lines.append(f"  - {item}")
            else:
                lines.append(f"  {data}")
        return "\n".join(lines)
