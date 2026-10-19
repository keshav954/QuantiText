"""
Auth service — login, registration, and user lookup.
Business logic only — no HTTP concerns.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.models.user import User


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User:
    """
    Verify credentials and return the user.
    Raises ForbiddenError if credentials are invalid or account is inactive.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise ForbiddenError("Invalid email or password")

    if not user.is_active:
        raise ForbiddenError("Account is deactivated")

    return user


async def create_user(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    email: str,
    password: str,
    full_name: str,
    role: str = "viewer",
) -> User:
    """
    Register a new user. Raises ConflictError if email already taken.
    """
    # Check for existing email
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError(f"Email '{email}' is already registered")

    user = User(
        id=uuid.uuid4(),
        org_id=org_id,
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
    """Fetch a user by ID. Raises NotFoundError if not found."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User", str(user_id))
    return user


def build_token_for_user(user: User) -> dict:
    """Create a JWT token payload for the given user."""
    token = create_access_token(
        data={
            "sub": str(user.id),
            "org": str(user.org_id),
            "role": user.role,
            "email": user.email,
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
