# ADR 005: Observability and Tracing Stack

**Date:** 2026-02-27
**Status:** Accepted

## Context

A production AI agent requires deep observability to understand token usage, latency bottlenecks, and hallucination rates, as well as standard API metrics.

## Decision

We will retain the v1 observability stack in its entirety:

1. **Langfuse**: All LLM calls and `StateGraph` nodes will be instrumented using the Langfuse callback handler.
2. **Prometheus / Grafana**: Fast API metrics and system usage.
3. **Structlog**: Structured JSON logging.

## Consequences

- Requires Langfuse credentials in all environments.
- Ensures immediate visibility into how well the Copilot retrieves runbooks during triage.
