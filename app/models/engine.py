"""Database engine and session factory for SeshOps.

Provides a synchronous SQLModel engine with environment-aware connection
strategy: SQLite (in-memory for tests, file-backed for local dev) or
PostgreSQL with connection pooling for staging/production.
"""

from __future__ import annotations

from sqlalchemy.pool import QueuePool, StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import Environment, settings
from app.core.logging import logger


def _build_engine():
    """Construct the SQLAlchemy engine based on the current environment."""
    if settings.ENVIRONMENT in (
        Environment.DEVELOPMENT,
        Environment.TEST,
    ) and settings.POSTGRES_HOST == "localhost":
        if settings.ENVIRONMENT == Environment.TEST:
            return create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        return create_engine(
            "sqlite:///./seshops.db",
            connect_args={"check_same_thread": False},
        )

    connection_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    return create_engine(
        connection_url,
        pool_pre_ping=True,
        poolclass=QueuePool,
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        pool_timeout=30,
        pool_recycle=1800,
    )


engine = _build_engine()

logger.info(
    "seshops_engine_ready",
    environment=settings.ENVIRONMENT.value,
    pool_size=settings.POSTGRES_POOL_SIZE,
)


def get_session() -> Session:
    """Open a new SQLModel session bound to the platform engine."""
    return Session(engine)


def create_tables() -> None:
    """Create all registered SQLModel tables if they do not already exist."""
    SQLModel.metadata.create_all(engine)
