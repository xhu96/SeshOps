"""SeshOps database service.

Encapsulates all persistence operations for operator accounts, triage
sessions, and health checks.  All blocking SQLModel operations are
offloaded to a thread pool via ``anyio.to_thread.run_sync`` so they
never block the uvicorn event loop.
"""

from __future__ import annotations

from typing import List, Optional

import anyio
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlmodel import Session, SQLModel, select
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Environment, settings
from app.core.logging import logger
from app.models.engine import engine, create_tables
from app.models.session import Session as TriageSession
from app.models.user import User


class DatabaseService:
    """Async-safe persistence layer for SeshOps entities.

    Every method offloads blocking SQLModel I/O to a thread pool so that
    the FastAPI event loop remains unblocked under concurrent requests.
    """

    def __init__(self) -> None:
        """Initialise the service and ensure tables exist."""
        try:
            create_tables()
            logger.info(
                "seshops_database_ready",
                environment=settings.ENVIRONMENT.value,
            )
        except SQLAlchemyError as exc:
            logger.error("seshops_database_init_failed", error=str(exc))
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise

    # ── Thread-offload helper with transient retry ──────────────────────

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type((OperationalError, ConnectionError, OSError)),
        reraise=True,
    )
    async def _run_sync(fn, *args, **kwargs):
        """Run a synchronous callable in a background thread.

        Retries up to 3 times on transient connection errors.
        """
        return await anyio.to_thread.run_sync(lambda: fn(*args, **kwargs))

    # ── User operations ──────────────────────────────────────────────────

    async def create_user(self, email: str, password: str) -> User:
        """Persist a new operator account."""
        def _create():
            with Session(engine) as session:
                user = User(email=email, hashed_password=password)
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info("seshops_operator_created", email=email)
                return user
        return await self._run_sync(_create)

    async def get_user(self, user_id: int) -> Optional[User]:
        """Look up an operator by primary key."""
        def _get():
            with Session(engine) as session:
                return session.get(User, user_id)
        return await self._run_sync(_get)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Look up an operator by email address."""
        def _get():
            with Session(engine) as session:
                return session.exec(
                    select(User).where(User.email == email)
                ).first()
        return await self._run_sync(_get)

    async def delete_user_by_email(self, email: str) -> bool:
        """Remove an operator account by email. Returns ``True`` on success."""
        def _delete():
            with Session(engine) as session:
                user = session.exec(
                    select(User).where(User.email == email)
                ).first()
                if not user:
                    return False
                session.delete(user)
                session.commit()
                logger.info("seshops_operator_deleted", email=email)
                return True
        return await self._run_sync(_delete)

    # ── Session operations ───────────────────────────────────────────────

    async def create_session(
        self, session_id: str, user_id: int, name: str = ""
    ) -> TriageSession:
        """Open a new triage session for the given operator."""
        def _create():
            with Session(engine) as session:
                triage = TriageSession(id=session_id, user_id=user_id, name=name)
                session.add(triage)
                session.commit()
                session.refresh(triage)
                logger.info(
                    "seshops_session_persisted",
                    session_id=session_id,
                    user_id=user_id,
                )
                return triage
        return await self._run_sync(_create)

    async def delete_session(self, session_id: str) -> bool:
        """Remove a triage session. Returns ``True`` on success."""
        def _delete():
            with Session(engine) as session:
                triage = session.get(TriageSession, session_id)
                if not triage:
                    return False
                session.delete(triage)
                session.commit()
                logger.info("seshops_session_removed", session_id=session_id)
                return True
        return await self._run_sync(_delete)

    async def get_session(self, session_id: str) -> Optional[TriageSession]:
        """Retrieve a single triage session by ID."""
        def _get():
            with Session(engine) as session:
                return session.get(TriageSession, session_id)
        return await self._run_sync(_get)

    async def get_user_sessions(self, user_id: int) -> List[TriageSession]:
        """Return all triage sessions belonging to an operator."""
        def _get():
            with Session(engine) as session:
                return list(
                    session.exec(
                        select(TriageSession)
                        .where(TriageSession.user_id == user_id)
                        .order_by(TriageSession.created_at)
                    ).all()
                )
        return await self._run_sync(_get)

    async def update_session_name(
        self, session_id: str, name: str
    ) -> TriageSession:
        """Rename a triage session. Raises 404 if not found."""
        def _update():
            with Session(engine) as session:
                triage = session.get(TriageSession, session_id)
                if not triage:
                    return None
                triage.name = name
                session.add(triage)
                session.commit()
                session.refresh(triage)
                logger.info(
                    "seshops_session_renamed",
                    session_id=session_id,
                    name=name,
                )
                return triage
        return await self._run_sync(_update)

    # ── Health ───────────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Return ``True`` if the database is reachable."""
        def _check():
            try:
                with Session(engine) as session:
                    session.exec(select(1)).first()
                    return True
            except (SQLAlchemyError, ConnectionError, OSError) as exc:
                logger.error("seshops_db_health_failed", error=str(exc))
                return False
        return await self._run_sync(_check)


database_service = DatabaseService()
