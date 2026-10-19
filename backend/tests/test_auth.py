"""
Tests for auth endpoints: login, register, and /me.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid
from datetime import datetime, timezone


def _make_fake_user(role="admin"):
    """Create a fake User-like object for mocking."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.org_id = uuid.uuid4()
    user.email = "admin@demo.local"
    user.hashed_password = "hashed"
    user.full_name = "Admin User"
    user.role = role
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.mark.asyncio
async def test_login_missing_body(async_client):
    """Login should return 422 if body is missing."""
    response = await async_client.post("/api/v1/auth/login")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client):
    """Login should return 403 for wrong credentials."""
    with patch("app.api.auth.auth_service") as mock_svc:
        from app.core.exceptions import ForbiddenError

        mock_svc.authenticate_user = AsyncMock(
            side_effect=ForbiddenError("Invalid email or password")
        )

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "bad@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_success(async_client):
    """Successful login returns a JWT token."""
    fake_user = _make_fake_user()

    with patch("app.api.auth.auth_service") as mock_svc:
        mock_svc.authenticate_user = AsyncMock(return_value=fake_user)
        mock_svc.build_token_for_user = MagicMock(
            return_value={
                "access_token": "fake.jwt.token",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        )
        # Patch audit log to avoid DB write
        with patch("app.api.auth.log_audit", new_callable=AsyncMock):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "admin@demo.local", "password": "admin123"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800


@pytest.mark.asyncio
async def test_me_unauthenticated(async_client):
    """GET /me without token should return 401 or 403."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_register_requires_admin(async_client):
    """Register endpoint should reject non-admin users."""
    # Viewer user trying to register
    fake_viewer = _make_fake_user(role="viewer")

    with patch("app.api.deps.get_current_user", return_value=fake_viewer):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@demo.local",
                "password": "newpassword123",
                "full_name": "New User",
                "role": "analyst",
            },
            headers={"Authorization": "Bearer fake.token"},
        )
        # Should be 403 (insufficient role)
        assert response.status_code == 403
