"""Unit tests for SeshOps DatabaseService (async CRUD)."""

import os
import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from sqlmodel import SQLModel

from app.models.engine import engine
from app.models.user import User
from app.services.database import DatabaseService

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def db_service():
    """Provide a fresh DatabaseService with clean tables."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    return DatabaseService()


async def test_create_and_get_user(db_service):
    """Create a user and retrieve it by ID."""
    hashed = User.hash_password("TestPass1!")
    user = await db_service.create_user("crud@example.com", hashed)
    assert user.id is not None
    assert user.email == "crud@example.com"

    fetched = await db_service.get_user(user.id)
    assert fetched is not None
    assert fetched.email == "crud@example.com"


async def test_get_user_by_email(db_service):
    """Look up a user by email."""
    user = await db_service.get_user_by_email("crud@example.com")
    assert user is not None
    assert user.email == "crud@example.com"


async def test_get_user_not_found(db_service):
    """Non-existent user returns None."""
    user = await db_service.get_user(99999)
    assert user is None


async def test_health_check(db_service):
    """Health check returns True when DB is available."""
    result = await db_service.health_check()
    assert result is True


async def test_create_and_delete_session(db_service):
    """Create and delete a triage session."""
    user = await db_service.get_user_by_email("crud@example.com")
    session = await db_service.create_session("test-sess-1", user.id, "Test Session")
    assert session.id == "test-sess-1"
    assert session.name == "Test Session"

    deleted = await db_service.delete_session("test-sess-1")
    assert deleted is True

    deleted_again = await db_service.delete_session("test-sess-1")
    assert deleted_again is False
