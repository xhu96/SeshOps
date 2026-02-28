"""LangGraph checkpoint thread model for the SeshOps triage pipeline.

Each triage invocation runs within a LangGraph thread that tracks the
deterministic ``triage → retrieve → summarize`` workflow state.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Thread(SQLModel, table=True):
    """A LangGraph execution thread for a single SeshOps triage run.

    Attributes:
        id: UUID identifying the thread within the LangGraph checkpoint store.
        created_at: UTC timestamp of thread creation.
    """

    id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
