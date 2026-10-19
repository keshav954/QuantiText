"""
Auth router — login, register, and profile endpoints.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.core.audit import get_client_ip, log_audit
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate with email + password, receive a JWT.
    """
    user = await auth_service.authenticate_user(db, body.email, body.password)
    token_data = auth_service.build_token_for_user(user)

    # Audit log
    await log_audit(
        db,
        action="login",
        resource="user",
        resource_id=str(user.id),
        user_id=user.id,
        org_id=user.org_id,
        ip_address=get_client_ip(request),
    )

    return TokenResponse(**token_data)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """
    Register a new user (admin-only).
    The new user is created in the same org as the admin.
    """
    user = await auth_service.create_user(
        db,
        org_id=current_user.org_id,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
    )

    # Audit log
    await log_audit(
        db,
        action="register",
        resource="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        org_id=current_user.org_id,
        details={"new_user_email": body.email, "role": body.role},
        ip_address=get_client_ip(request),
    )

    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """
    Get the currently authenticated user's profile.
    """
    return UserRead.model_validate(current_user)
