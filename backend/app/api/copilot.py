"""
Copilot router — /api/v1/copilot NL2SQL chat endpoints.

POST /copilot/chat              — single-turn NL2SQL question
GET  /copilot/sessions          — list user's sessions
GET  /copilot/sessions/{id}     — load session message history
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_readonly_db, require_role
from app.models.user import User
from app.schemas.copilot import ChatMessage, ChatRequest, ChatResponse, SessionOut
from app.services import copilot_service

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_role("viewer"))],
)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    readonly_db: AsyncSession = Depends(get_readonly_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    NL2SQL chat — converts a natural-language question to SQL,
    executes it on the read-only connection, and returns a grounded answer.

    ⚠️ Only aggregated data is sent to the LLM. Customer PII is never included.
    Generated SQL is validated before execution.
    """
    result = await copilot_service.chat(
        db,
        readonly_db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        question=body.question,
        session_id=body.session_id,
    )
    return ChatResponse(**result)


@router.get(
    "/sessions",
    response_model=list[SessionOut],
    dependencies=[Depends(require_role("viewer"))],
)
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionOut]:
    """Return recent chat sessions for the current user."""
    sessions = await copilot_service.list_sessions(
        db, org_id=current_user.org_id, user_id=current_user.id, limit=limit
    )
    return [SessionOut(**s) for s in sessions]


@router.get(
    "/sessions/{session_id}",
    response_model=list[ChatMessage],
    dependencies=[Depends(require_role("viewer"))],
)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessage]:
    """Load the message history for a specific session."""
    messages = await copilot_service.get_session_messages(
        db, org_id=current_user.org_id, session_id=session_id
    )
    return [ChatMessage(**m) for m in messages]
