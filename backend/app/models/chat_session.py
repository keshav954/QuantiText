"""
Chat session and message models for multi-turn conversation memory.

ChatSession tracks a conversation thread. ChatMessage stores individual
messages with role (user/assistant/system) and rich metadata for
SQL queries, charts, and feedback.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class ChatSession(UUIDPrimaryKeyMixin, Base):
    """A conversation session between a user and the AI copilot."""

    __tablename__ = "chat_sessions"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="New Chat")
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Auto-generated summary of older messages for context compression",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    messages = relationship(
        "ChatMessage", back_populates="session",
        cascade="all, delete-orphan", order_by="ChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatSession {self.title[:40]}>"


class ChatMessage(UUIDPrimaryKeyMixin, Base):
    """Individual message in a chat session."""

    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Denormalised for efficient multi-tenant filtering (matches migration 0002)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="user | assistant | system",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True,
        comment="Rich metadata: sql_generated, chart_config, error, tokens_used, etc.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        preview = self.content[:50] if self.content else ""
        return f"<ChatMessage {self.role}: {preview}>"

    def to_context_dict(self) -> dict:
        """Convert to the format expected by LLM providers."""
        return {"role": self.role, "content": self.content}
