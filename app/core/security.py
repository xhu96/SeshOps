"""Authentication and token management for SeshOps.

Consolidates JWT creation, verification, and request/response schemas
that were previously split across ``utils/auth.py`` and ``schemas/auth.py``.
All auth-related data types live here so the rest of the codebase imports
from a single location.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

from app.core.config import settings
from app.core.logging import logger


# ── API contract types ───────────────────────────────────────────────────────

class Token(BaseModel):
    """JWT access token returned after successful authentication.

    Attributes:
        access_token: The encoded JWT string.
        token_type: Always ``"bearer"``.
        expires_at: UTC expiry timestamp.
    """

    access_token: str = Field(..., description="The encoded JWT string")
    token_type: str = Field(default="bearer")
    expires_at: datetime = Field(..., description="UTC expiry timestamp")


class TokenResponse(BaseModel):
    """Response payload for the login endpoint."""

    access_token: str = Field(..., description="The encoded JWT string")
    token_type: str = Field(default="bearer")
    expires_at: datetime = Field(..., description="UTC expiry timestamp")


class UserCreate(BaseModel):
    """Operator registration payload.

    Attributes:
        email: Operator's email address (validated).
        password: Plaintext password — validated for strength, never stored.
    """

    email: EmailStr = Field(..., description="Operator's email address")
    password: SecretStr = Field(
        ..., description="Operator's password", min_length=8, max_length=64
    )

    @field_validator("password")
    @classmethod
    def _enforce_strength(cls, v: SecretStr) -> SecretStr:
        """Require mixed case, digits, and special characters."""
        pw = v.get_secret_value()
        if len(pw) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", pw):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", pw):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", pw):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', pw):
            raise ValueError("Password must contain at least one special character")
        return v


class UserResponse(BaseModel):
    """Response payload for operator registration."""

    id: int = Field(..., description="Operator's ID")
    email: str = Field(..., description="Operator's email address")
    token: Token = Field(..., description="Authentication token")


class SessionResponse(BaseModel):
    """Response payload for session creation/update endpoints."""

    session_id: str = Field(
        ..., description="UUID identifying the triage session"
    )
    name: str = Field(
        default="", description="Human-readable session label", max_length=100
    )
    token: Token = Field(..., description="JWT for subsequent API calls")

    @field_validator("name")
    @classmethod
    def _sanitise_name(cls, v: str) -> str:
        """Strip potentially harmful characters from the session name."""
        return re.sub(r'[<>{}[\]()\'\"`]', "", v)


# ── Token helpers ────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> Token:
    """Mint a signed JWT for the given *subject* (user ID or session ID).

    Args:
        subject: The value to embed in the ``sub`` claim.
        expires_delta: Custom TTL; defaults to ``JWT_ACCESS_TOKEN_EXPIRE_DAYS``.

    Returns:
        A ``Token`` containing the encoded JWT and its expiry.
    """
    expire = datetime.now(UTC) + (
        expires_delta
        or timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
    )

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": f"{subject}-{datetime.now(UTC).timestamp()}",
    }

    encoded = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    logger.info("seshops_token_minted", subject=subject, expires_at=expire.isoformat())

    return Token(access_token=encoded, expires_at=expire)


def verify_token(token: str) -> Optional[str]:
    """Decode and validate a JWT, returning the ``sub`` claim on success.

    Args:
        token: The raw JWT string.

    Returns:
        The subject string if valid, ``None`` if the signature check fails.

    Raises:
        ValueError: If the token is not a well-formed JWT string.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Token must be a non-empty string")

    if not re.match(r"^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$", token):
        raise ValueError("Token format is invalid — expected JWT format")

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        subject: Optional[str] = payload.get("sub")
        if subject is None:
            logger.warning("seshops_token_missing_subject")
            return None

        logger.info("seshops_token_verified", subject=subject)
        return subject

    except JWTError as exc:
        logger.error("seshops_token_verification_failed", error=str(exc))
        return None
