# ADR-002: SQLModel over Raw SQLAlchemy

## Status

Accepted

## Context

SeshOps needs an ORM for user accounts, triage sessions, and future triage history. Two options were considered:

1. **Raw SQLAlchemy** — Maximum flexibility, wider community, async engine support.
2. **SQLModel** — Pydantic-SQLAlchemy hybrid by the FastAPI creator, type-safe, less boilerplate.

## Decision

Use SQLModel for all data models.

## Rationale

- SQLModel models are simultaneously Pydantic BaseModels and SQLAlchemy mapped classes — one definition serves both validation and persistence.
- Reduces boilerplate: no separate `schemas/` directory needed.
- First-class compatibility with FastAPI's response model system.
- Created and maintained by the same author as FastAPI (tiangolo).

## Consequences

- SQLModel is less mature than raw SQLAlchemy; some advanced ORM patterns require falling back to `sqlalchemy.orm`.
- Async session support is still evolving in SQLModel — we use `anyio.to_thread.run_sync` as a bridge (see ADR-001).
- Migrations are handled by Alembic, which works identically with SQLModel as with SQLAlchemy.
