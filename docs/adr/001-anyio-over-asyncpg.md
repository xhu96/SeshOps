# ADR-001: anyio over asyncpg for Database Concurrency

## Status

Accepted

## Context

SeshOps uses SQLModel (built on SQLAlchemy) for ORM operations. The original codebase defined `async def` methods but executed synchronous SQLModel sessions directly, blocking the uvicorn event loop under concurrent load.

Two remediation paths were evaluated:

1. **asyncpg + SQLAlchemy async engine** — Full native async, but requires migrating all session code to `async_session` and per-query `await`.
2. **anyio.to_thread.run_sync** — Offload synchronous sessions to a thread pool, keeping existing SQLModel code intact.

## Decision

Use `anyio.to_thread.run_sync` to offload blocking DB operations.

## Rationale

- SQLModel's API is synchronous by design; rewriting to async sessions would require duplicating or replacing all model interactions.
- `anyio` is already a transitive dependency of FastAPI (via Starlette) — no new dependency.
- Thread-pool offloading is the pattern recommended by the Starlette documentation for sync ORMs.
- This preserves the ability to migrate to asyncpg later without architectural changes.

## Consequences

- Each DB operation runs in a background thread, consuming a thread from the default pool.
- Under extreme concurrency (>100 simultaneous DB calls), the thread pool may need tuning.
- Transient connection errors are now retried via `tenacity` on the `_run_sync` helper.
