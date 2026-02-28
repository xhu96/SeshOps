"""Unit tests for SeshOps configuration (pydantic-settings)."""

import os
import pytest


def test_default_project_name():
    """Default PROJECT_NAME is SeshOps, not template name."""
    from app.core.config import Settings
    s = Settings(OPENAI_API_KEY="sk-test", JWT_SECRET_KEY="test")
    assert s.PROJECT_NAME == "SeshOps"


def test_default_postgres_db():
    """Default database name is seshops_db, not food_order_db."""
    from app.core.config import Settings
    s = Settings(OPENAI_API_KEY="sk-test", JWT_SECRET_KEY="test")
    assert s.POSTGRES_DB == "seshops_db"


def test_environment_validator_prod_alias():
    """'prod' alias resolves to PRODUCTION."""
    from app.core.config import Environment, Settings
    s = Settings(
        ENVIRONMENT="prod",
        OPENAI_API_KEY="sk-test",
        JWT_SECRET_KEY="test",
    )
    assert s.ENVIRONMENT == Environment.PRODUCTION


def test_environment_validator_test():
    """'test' resolves to TEST."""
    from app.core.config import Environment, Settings
    s = Settings(
        ENVIRONMENT="test",
        OPENAI_API_KEY="sk-test",
        JWT_SECRET_KEY="test",
    )
    assert s.ENVIRONMENT == Environment.TEST


def test_environment_validator_unknown_defaults_to_dev():
    """Unknown environment string defaults to DEVELOPMENT."""
    from app.core.config import Environment, Settings
    s = Settings(
        ENVIRONMENT="mystery",
        OPENAI_API_KEY="sk-test",
        JWT_SECRET_KEY="test",
    )
    assert s.ENVIRONMENT == Environment.DEVELOPMENT


def test_per_env_override_development():
    """Development environment gets DEBUG=True and console logging by default."""
    from app.core.config import Settings

    # Ensure these are not explicitly set in the test env
    for key in ("DEBUG", "LOG_LEVEL", "LOG_FORMAT"):
        os.environ.pop(key, None)

    s = Settings(
        ENVIRONMENT="development",
        OPENAI_API_KEY="sk-test",
        JWT_SECRET_KEY="test",
    )
    assert s.DEBUG is True
    assert s.LOG_LEVEL == "DEBUG"
    assert s.LOG_FORMAT == "console"


def test_per_env_override_production():
    """Production environment gets DEBUG=False and WARNING log level."""
    from app.core.config import Settings

    for key in ("DEBUG", "LOG_LEVEL", "LOG_FORMAT"):
        os.environ.pop(key, None)

    s = Settings(
        ENVIRONMENT="production",
        OPENAI_API_KEY="sk-test",
        JWT_SECRET_KEY="test",
    )
    assert s.DEBUG is False
    assert s.LOG_LEVEL == "WARNING"
    assert s.LOG_FORMAT == "json"


def test_explicit_env_var_not_overridden(monkeypatch):
    """An explicitly set env var is NOT overridden by per-env defaults."""
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    from app.core.config import Settings

    s = Settings(
        ENVIRONMENT="development",
        OPENAI_API_KEY="sk-test",
        JWT_SECRET_KEY="test",
    )
    # Development default is DEBUG, but env var says ERROR
    assert s.LOG_LEVEL == "ERROR"


def test_rate_limit_endpoints_property():
    """RATE_LIMIT_ENDPOINTS property returns the correct dict shape."""
    from app.core.config import Settings
    s = Settings(OPENAI_API_KEY="sk-test", JWT_SECRET_KEY="test")
    endpoints = s.RATE_LIMIT_ENDPOINTS
    assert "triage" in endpoints
    assert "register" in endpoints
    assert "login" in endpoints
    assert isinstance(endpoints["triage"], list)


def test_no_long_term_memory_settings():
    """LONG_TERM_MEMORY_* settings have been removed (orphaned config)."""
    from app.core.config import Settings
    s = Settings(OPENAI_API_KEY="sk-test", JWT_SECRET_KEY="test")
    assert not hasattr(s, "LONG_TERM_MEMORY_MODEL")
    assert not hasattr(s, "LONG_TERM_MEMORY_EMBEDDER_MODEL")
    assert not hasattr(s, "LONG_TERM_MEMORY_COLLECTION_NAME")
