"""SeshOps operator account model.

Represents a human operator who authenticates against the platform to
submit incident triage requests.  Passwords are hashed with bcrypt.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import List, Optional

import bcrypt
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    """An authenticated SeshOps operator.

    Attributes:
        id: Auto-incremented primary key.
        email: Unique login identifier for the operator.
        hashed_password: Bcrypt digest — never stored in plaintext.
        created_at: UTC timestamp of account creation.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def verify_password(self, plaintext: str) -> bool:
        """Compare *plaintext* against the stored bcrypt hash."""
        return bcrypt.checkpw(
            plaintext.encode("utf-8"),
            self.hashed_password.encode("utf-8"),
        )

    @staticmethod
    def hash_password(plaintext: str) -> str:
        """Return a bcrypt hash suitable for storage."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plaintext.encode("utf-8"), salt).decode("utf-8")
