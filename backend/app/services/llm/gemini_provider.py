"""
Gemini LLM provider — cloud-based, high-quality reasoning.

Uses langchain-google-genai under the hood. Best for:
- Complex multi-step reasoning
- Grounding checks
- When local models produce low-quality output

Cost: per-token billing via Google AI API.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator

from app.core.config import settings
from app.services.llm.base import LLMProvider, LLMResponse, TaskType

log = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini provider via LangChain."""

    def __init__(self) -> None:
        self._model_name = settings.LLM_MODEL
        self._api_key = settings.GEMINI_API_KEY
        self._llm = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_llm(self, temperature: float = 0.1, max_tokens: int = 2048):
        """Lazy-init the LangChain Gemini LLM."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=self._model_name,
            google_api_key=self._api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    def _build_messages(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: list[dict] | None = None,
    ) -> list:
        """Build LangChain message list from our standard format."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        if context:
            for msg in context:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
                elif role == "system":
                    messages.append(SystemMessage(content=content))
        messages.append(HumanMessage(content=prompt))
        return messages

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
        """Generate a response using Gemini."""
        llm = self._get_llm(temperature=temperature, max_tokens=max_tokens)
        messages = self._build_messages(prompt, system_prompt, context)

        start = time.monotonic()
        response = await llm.ainvoke(messages)
        latency = (time.monotonic() - start) * 1000

        # Extract token usage if available
        usage = getattr(response, "usage_metadata", {}) or {}
        prompt_tokens = usage.get("input_tokens", 0) if isinstance(usage, dict) else 0
        completion_tokens = usage.get("output_tokens", 0) if isinstance(usage, dict) else 0

        return LLMResponse(
            text=response.content,
            model=self._model_name,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=round(latency, 2),
        )

    async def generate_sql(
        self,
        question: str,
        *,
        schema_context: str,
        examples: list[dict] | None = None,
        dialect: str = "postgresql",
    ) -> LLMResponse:
        """Generate SQL from natural language using Gemini."""
        from app.services.llm.prompts import (
            FEW_SHOT_HEADER,
            FEW_SHOT_TEMPLATE,
            NL2SQL_SYSTEM,
            NL2SQL_USER,
        )

        # Build few-shot section
        few_shot_section = ""
        if examples:
            few_shot_section = FEW_SHOT_HEADER
            for ex in examples[:5]:  # Cap at 5 examples
                few_shot_section += FEW_SHOT_TEMPLATE.format(question=ex["question"], sql=ex["sql"])

        user_prompt = NL2SQL_USER.format(
            schema_context=schema_context,
            glossary_context="",  # Filled by copilot agent
            few_shot_section=few_shot_section,
            question=question,
        )

        return await self.generate(
            user_prompt,
            system_prompt=NL2SQL_SYSTEM,
            temperature=0.0,  # Deterministic SQL generation
            max_tokens=1024,
            task_type=TaskType.SQL_GENERATION,
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
        """Stream tokens from Gemini."""
        llm = self._get_llm(temperature=temperature)
        messages = self._build_messages(prompt, system_prompt, context)

        async for chunk in llm.astream(messages):
            if chunk.content:
                yield chunk.content
