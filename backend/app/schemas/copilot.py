"""
Copilot schemas — NL2SQL chat request/response models.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str
    timestamp: datetime | None = None


class ChatRequest(BaseModel):
    """Single turn NL2SQL chat request."""

    question: str = Field(..., min_length=1, max_length=2000)
    session_id: UUID | None = None  # None → create new session


class QueryResult(BaseModel):
    """Result of executing a validated SQL query."""

    sql: str
    columns: list[str]
    rows: list[list]  # raw values
    row_count: int
    chart_type: str | None = None  # bar | line | pie | table


class ChatResponse(BaseModel):
    """Full response for one NL2SQL turn."""

    session_id: UUID
    question: str
    answer: str  # LLM narrative answer
    sql: str | None = None  # generated SQL (may be None for conversational turns)
    result: QueryResult | None = None
    follow_up_suggestions: list[str] = []
    from_cache: bool = False


class SessionOut(BaseModel):
    """Chat session metadata."""

    id: UUID
    title: str | None = None
    created_at: datetime
    message_count: int
