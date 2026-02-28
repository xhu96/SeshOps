"""Base model mixin for all SeshOps database entities.

Provides a ``created_at`` timestamp that is automatically set on insert.
All table models in the platform inherit from ``SeshOpsBase``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class SeshOpsBase(SQLModel):
    """Common fields shared by every SeshOps table model."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp recorded when the row was first persisted.",
    )
