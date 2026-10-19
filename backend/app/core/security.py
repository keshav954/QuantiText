"""
Security utilities — JWT token management and password hashing.
Uses argon2 for password hashing per security rules.
Uses python-jose for JWT encode/decode.
"""

from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from jose import JWTError, jwt

from app.core.config import settings

# ── Password Hashing (argon2) ────────────────────────────

_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
)


def hash_password(plain: str) -> str:
    """Hash a plaintext password using argon2id."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an argon2id hash."""
    try:
        return _ph.verify(hashed, plain)
    except VerificationError:
        return False


# ── JWT Tokens ───────────────────────────────────────────


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.
    Payload includes 'sub' (user id), 'org' (org id), 'role', and 'exp'.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.
    Returns the payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
