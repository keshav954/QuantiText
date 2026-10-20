"""
Auth schemas — login, registration, and token response models.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Credentials for login."""

    email: str = Field(..., min_length=3, max_length=320, examples=["admin@demo.local"])
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    """New user registration (admin-only)."""

    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="viewer", pattern="^(admin|manager|analyst|viewer)$")


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserRead(BaseModel):
    """User profile (no password exposed)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    """Internal user creation model (used by auth service)."""

    org_id: UUID
    email: str
    password: str
    full_name: str
    role: str = "viewer"
