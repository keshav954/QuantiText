"""
Role-Based Access Control (RBAC) — shared FastAPI dependency.
Enforced as a dependency, NOT ad-hoc in each route (per security rules).

Usage in a router:
    @router.get("/protected", dependencies=[Depends(require_role(Role.ANALYST))])
    async def protected_route(user: User = Depends(get_current_user)):
        ...
"""

from enum import StrEnum

from fastapi import Depends, HTTPException, status


class Role(StrEnum):
    """User roles in ascending privilege order."""

    VIEWER = "viewer"
    ANALYST = "analyst"
    MANAGER = "manager"
    ADMIN = "admin"


# Numeric hierarchy for comparison
ROLE_HIERARCHY: dict[str, int] = {
    Role.VIEWER: 1,
    Role.ANALYST: 2,
    Role.MANAGER: 3,
    Role.ADMIN: 4,
}


def require_role(minimum: Role):
    """
    FastAPI dependency factory — returns a dependency that checks the
    current user's role against the minimum required role.

    Raises 403 if the user's role is below the minimum.
    """

    async def _check_role(current_user=Depends(_get_current_user)):
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' insufficient. Requires '{minimum}' or higher.",
            )
        return current_user

    return _check_role


async def _get_current_user():
    """
    Placeholder — replaced by the real get_current_user via wire_rbac().
    This avoids circular imports between rbac.py and deps.py.
    """
    raise NotImplementedError("Wire up get_current_user via wire_rbac()")


def wire_rbac(get_current_user_func):
    """
    Called once at startup to inject the real get_current_user dependency.
    Avoids circular imports between rbac.py and deps.py.
    """
    global _get_current_user
    _get_current_user = get_current_user_func
