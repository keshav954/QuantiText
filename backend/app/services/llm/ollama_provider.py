"""
Ollama LLM provider — local, zero-cost inference.

Runs models locally via Ollama (https://ollama.ai). Best for:
- Daily SQL generation (Qwen-2.5-Coder)
- Quick explanations and summaries (Llama-3)
- Privacy-sensitive operations (no data leaves the machine)

Cost: $0 — runs on your own hardware.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings
from app.services.llm.base import LLMProvider, LLMResponse, TaskType

log = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Local Ollama provider for zero-cost, low-latency inference."""

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._sql_model = settings.OLLAMA_SQL_MODEL
        self._text_model = settings.OLLAMA_TEXT_MODEL
        self._timeout = 120.0  # Local models can be slow on first load

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        """Check if Ollama server is reachable (non-blocking best-effort check)."""
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def _pick_model(self, task_type: TaskType) -> str:
        """Select the best local model for the task."""
        if task_type == TaskType.SQL_GENERATION:
            return self._sql_model
        return self._text_model

    def _build_messages(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context: list[dict] | None = None,
    ) -> list[dict]:
        """Build Ollama chat message format."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            for msg in context:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })
        messages.append({"role": "user", "content": prompt})
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
        """Generate a response using a local Ollama model."""
        model = self._pick_model(task_type)
        messages = self._build_messages(prompt, system_prompt, context)

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.monotonic() - start) * 1000

        # Extract token counts from Ollama response
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return LLMResponse(
            text=data.get("message", {}).get("content", ""),
            model=model,
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
        """Generate SQL using the local SQL-optimised model (Qwen-2.5-Coder)."""
        from app.services.llm.prompts import (
            FEW_SHOT_HEADER,
            FEW_SHOT_TEMPLATE,
            NL2SQL_SYSTEM,
            NL2SQL_USER,
        )

        few_shot_section = ""
        if examples:
            few_shot_section = FEW_SHOT_HEADER
            for ex in examples[:5]:
                few_shot_section += FEW_SHOT_TEMPLATE.format(
                    question=ex["question"], sql=ex["sql"]
                )

        user_prompt = NL2SQL_USER.format(
            schema_context=schema_context,
            glossary_context="",
            few_shot_section=few_shot_section,
            question=question,
        )

        return await self.generate(
            user_prompt,
            system_prompt=NL2SQL_SYSTEM,
            temperature=0.0,
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
        """Stream tokens from a local Ollama model."""
        model = self._pick_model(task_type)
        messages = self._build_messages(prompt, system_prompt, context)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                import json

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
