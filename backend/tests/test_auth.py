"""
Tests for auth endpoints: login, register, and /me.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
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
    from app.api.deps import get_current_user
    from tests.conftest import _test_app

    # Viewer user trying to register
    fake_viewer = _make_fake_user(role="viewer")

    _test_app.dependency_overrides[get_current_user] = lambda: fake_viewer
    try:
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
    finally:
        _test_app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_change_password_success(async_client):
    """Authenticated user can change their password."""
    from app.api.deps import get_current_user
    from tests.conftest import _test_app

    fake_user = _make_fake_user(role="viewer")
    _test_app.dependency_overrides[get_current_user] = lambda: fake_user

    try:
        with patch("app.api.auth.auth_service") as mock_svc:
            mock_svc.change_password = AsyncMock(return_value=True)
            with patch("app.api.auth.log_audit", new_callable=AsyncMock):
                response = await async_client.post(
                    "/api/v1/auth/change-password",
                    json={
                        "current_password": "old_password",
                        "new_password": "new_password_123",
                    },
                    headers={"Authorization": "Bearer fake.token"},
                )
        assert response.status_code == 200
        assert response.json() == {"status": "password_changed"}
    finally:
        _test_app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_change_password_wrong_current(async_client):
    """Change password fails if current password is wrong."""
    from app.api.deps import get_current_user
    from app.core.exceptions import ForbiddenError
    from tests.conftest import _test_app

    fake_user = _make_fake_user(role="viewer")
    _test_app.dependency_overrides[get_current_user] = lambda: fake_user

    try:
        with patch("app.api.auth.auth_service") as mock_svc:
            mock_svc.change_password = AsyncMock(
                side_effect=ForbiddenError("Incorrect current password")
            )
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "wrong_password",
                    "new_password": "new_password_123",
                },
                headers={"Authorization": "Bearer fake.token"},
            )
        assert response.status_code == 403
    finally:
        _test_app.dependency_overrides.pop(get_current_user, None)


def test_validate_production_settings_rejects_insecure_keys():
    """validate_production_settings must exit if DEBUG=False and key is weak or placeholder."""
    from app.core.config import settings, validate_production_settings

    # 1. Too short
    with (
        patch.object(settings, "DEBUG", False),
        patch.object(settings, "SECRET_KEY", "short-key-123"),
    ):
        with pytest.raises(SystemExit) as exc:
            validate_production_settings()
        assert exc.value.code == 1

    # 2. Contains placeholder word 'generate'
    with (
        patch.object(settings, "DEBUG", False),
        patch.object(settings, "SECRET_KEY", "generate_with_openssl_rand_hex_32_extra_padding"),
    ):
        with pytest.raises(SystemExit) as exc:
            validate_production_settings()
        assert exc.value.code == 1

    # 3. Contains placeholder word 'set_strong'
    with (
        patch.object(settings, "DEBUG", False),
        patch.object(settings, "SECRET_KEY", "set_strong_production_postgres_password_key"),
    ):
        with pytest.raises(SystemExit) as exc:
            validate_production_settings()
        assert exc.value.code == 1

    # 4. In DEBUG=True mode, weak key does not exit
    with patch.object(settings, "DEBUG", True), patch.object(settings, "SECRET_KEY", "short"):
        validate_production_settings()  # should not raise

    # 5. Strong key in DEBUG=False passes cleanly
    strong_key = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    with patch.object(settings, "DEBUG", False), patch.object(settings, "SECRET_KEY", strong_key):
        validate_production_settings()  # should not raise
