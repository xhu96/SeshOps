"""SeshOps operator session model.

A session groups a sequence of triage interactions for a single
authenticated operator.  Sessions are created via the ``/auth/session``
endpoint and carry their own JWT for subsequent API calls.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    """A triage session owned by a SeshOps operator.

    Attributes:
        id: UUID primary key assigned at creation.
        user_id: Foreign key linking the session to its operator.
        name: Optional human-readable label for the session.
        created_at: UTC timestamp of session creation.
    """

    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
