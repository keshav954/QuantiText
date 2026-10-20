"""
Audit logging helper — writes immutable records to the audit_log table.
Called from services and middleware for: logins, queries, approvals, exports.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def log_audit(
    db: AsyncSession,
    *,
    action: str,
    resource: str,
    resource_id: str | None = None,
    user_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Insert an audit log entry. Fire-and-forget — errors are logged but don't
    propagate to the caller.

    Args:
        db: Async database session
        action: What happened (e.g. 'login', 'query', 'approve', 'export')
        resource: What was acted on (e.g. 'user', 'recommendation', 'report')
        resource_id: ID of the resource (optional)
        user_id: Who did it (optional for unauthenticated actions)
        org_id: Which org context (optional)
        details: Additional JSON metadata
        ip_address: Client IP
    """
    import json
    import logging

    log = logging.getLogger(__name__)

    try:
        await db.execute(
            text("""
                INSERT INTO audit_log (id, org_id, user_id, action, resource, resource_id, details, ip_address, created_at)
                VALUES (:id, :org_id, :user_id, :action, :resource, :resource_id, :details, :ip, :created_at)
            """),
            {
                "id": str(uuid.uuid4()),
                "org_id": str(org_id) if org_id else None,
                "user_id": str(user_id) if user_id else None,
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
                "details": json.dumps(details) if details else None,
                "ip": ip_address,
                "created_at": datetime.now(UTC),
            },
        )
        await db.commit()
    except Exception:
        log.exception("Failed to write audit log entry: action=%s resource=%s", action, resource)


def get_client_ip(request) -> str | None:
    """Extract client IP from a FastAPI/Starlette request, handling proxies."""
    if hasattr(request, "headers"):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if hasattr(request, "client") and request.client:
        return request.client.host
    return None
