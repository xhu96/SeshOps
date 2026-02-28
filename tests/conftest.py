"""Pytest configuration and shared fixtures for the SeshOps test suite."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

# Pin test environment before any app imports
os.environ["APP_ENV"] = "test"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["OPENAI_API_KEY"] = "sk-test"

from app.main import app  # noqa: E402
from app.models.engine import engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create a clean in-memory SQLite database for the test session."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def client():
    """Provide a synchronous TestClient for making API requests."""
    with TestClient(app) as tc:
        yield tc
