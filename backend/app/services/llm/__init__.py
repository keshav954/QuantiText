"""
LLM provider package — pluggable AI backend supporting Gemini (cloud) and Ollama (local).
Use the factory to get the right provider based on configuration.
"""

from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_provider

__all__ = ["LLMProvider", "get_provider"]
