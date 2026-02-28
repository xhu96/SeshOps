"""SeshOps application configuration.

Centralises all runtime settings for the SeshOps incident-triage platform.
Values are loaded from environment variables (with .env file support) via
pydantic-settings — no manual ``os.getenv`` calls elsewhere in the codebase.

Per-environment defaults are applied via ``model_post_init`` so that
development, staging, production, and test environments each get sensible
DEBUG, LOG_LEVEL, LOG_FORMAT, and rate-limit values — unless the operator
has explicitly overridden them via environment variables.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment for SeshOps."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# ── Per-environment defaults ─────────────────────────────────────────────────

_ENV_OVERRIDES: dict[Environment, dict] = {
    Environment.DEVELOPMENT: {
        "DEBUG": True,
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "console",
        "RATE_LIMIT_DEFAULT": ["1000 per day", "200 per hour"],
    },
    Environment.STAGING: {
        "DEBUG": False,
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "json",
        "RATE_LIMIT_DEFAULT": ["500 per day", "100 per hour"],
    },
    Environment.PRODUCTION: {
        "DEBUG": False,
        "LOG_LEVEL": "WARNING",
        "LOG_FORMAT": "json",
        "RATE_LIMIT_DEFAULT": ["200 per day", "50 per hour"],
    },
    Environment.TEST: {
        "DEBUG": True,
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "console",
        "RATE_LIMIT_DEFAULT": ["1000 per day", "1000 per hour"],
    },
}


class Settings(BaseSettings):
    """Typed, validated configuration for the SeshOps platform.

    Every setting defaults to a sensible development value and can be
    overridden by an environment variable of the same name (case-sensitive).
    After construction, ``model_post_init`` applies per-environment defaults
    for any field the operator has not explicitly set.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Deployment ────────────────────────────────────────────────────
    APP_ENV: str = "development"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False

    # ── Application identity ──────────────────────────────────────────
    PROJECT_NAME: str = "SeshOps"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "IT Operations Copilot — deterministic incident triage "
        "powered by a LangGraph pipeline with RAG-augmented runbook retrieval"
    )
    API_V1_STR: str = "/api/v1"

    # ── CORS & Security ──────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*", "localhost", "127.0.0.1"]

    # ── Langfuse observability ────────────────────────────────────────
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── LLM configuration ────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gpt-5-mini"
    DEFAULT_LLM_TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 2000
    MAX_LLM_CALL_RETRIES: int = 3

    # ── JWT authentication ────────────────────────────────────────────
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # ── Logging ───────────────────────────────────────────────────────
    LOG_DIR: Path = Path("logs")
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "console"

    # ── Postgres ──────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "seshops_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 10

    # ── Rate limiting ─────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: List[str] = ["200 per day", "50 per hour"]
    RATE_LIMIT_TRIAGE: List[str] = ["30 per minute"]
    RATE_LIMIT_REGISTER: List[str] = ["10 per hour"]
    RATE_LIMIT_LOGIN: List[str] = ["20 per minute"]
    RATE_LIMIT_ROOT: List[str] = ["10 per minute"]
    RATE_LIMIT_HEALTH: List[str] = ["20 per minute"]

    # ── Evaluation ────────────────────────────────────────────────────
    EVALUATION_LLM: str = "gpt-5"
    EVALUATION_BASE_URL: str = "https://api.openai.com/v1"
    EVALUATION_API_KEY: str = ""
    EVALUATION_SLEEP_TIME: int = 10

    # ── Derived helpers ───────────────────────────────────────────────

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _resolve_environment(cls, v: str) -> Environment:
        """Map common aliases (prod, stage) to canonical Environment values."""
        mapping = {
            "production": Environment.PRODUCTION,
            "prod": Environment.PRODUCTION,
            "staging": Environment.STAGING,
            "stage": Environment.STAGING,
            "test": Environment.TEST,
        }
        if isinstance(v, Environment):
            return v
        return mapping.get(str(v).lower(), Environment.DEVELOPMENT)

    def model_post_init(self, __context) -> None:
        """Apply per-environment defaults for fields not explicitly set.

        This re-implements the old repo's ``apply_environment_settings()``
        within pydantic-settings: for each environment, override DEBUG,
        LOG_LEVEL, LOG_FORMAT, and RATE_LIMIT_DEFAULT **only if** the
        operator has not set the corresponding environment variable.
        """
        overrides = _ENV_OVERRIDES.get(self.ENVIRONMENT, {})
        for key, value in overrides.items():
            env_var = key.upper()
            if env_var not in os.environ:
                object.__setattr__(self, key, value)

    @property
    def RATE_LIMIT_ENDPOINTS(self) -> dict[str, list[str]]:
        """Convenience accessor matching the old dict-of-lists interface."""
        return {
            "triage": self.RATE_LIMIT_TRIAGE,
            "register": self.RATE_LIMIT_REGISTER,
            "login": self.RATE_LIMIT_LOGIN,
            "root": self.RATE_LIMIT_ROOT,
            "health": self.RATE_LIMIT_HEALTH,
        }


settings = Settings()
