"""Triage message model for SeshOps.

Stores individual LLM-generated or user-submitted messages produced during
an incident triage session, providing a persistent audit trail.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    """A single message within a SeshOps triage interaction.

    Attributes:
        id: Auto-incremented primary key.
        session_id: Foreign key to the owning session.
        role: Message author — ``"user"``, ``"assistant"``, or ``"system"``.
        content: The message body (plain text or markdown).
        created_at: UTC timestamp of message creation.
    """

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    role: str = Field(description="One of: user, assistant, system")
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
