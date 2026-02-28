"""Unit tests for SeshOps database engine factory."""

import os
import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from app.models.engine import engine


def test_test_env_uses_sqlite():
    """In test environment, engine should use SQLite (in-memory)."""
    url = str(engine.url)
    assert "sqlite" in url


def test_engine_is_not_none():
    """Engine should always be initialised at module level."""
    assert engine is not None
