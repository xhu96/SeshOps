# ADR 001: Rewrite vs Selective Carry-Forward from v1

**Date:** 2026-02-27
**Status:** Accepted

## Context

The v2 rebuild starts with `reference-v1`, which is a generic, production-ready "FastAPI LangGraph Chatbot". Our goal is to build an internal SeshOps. We must decide whether to fork v1 entirely or selectively cherry-pick its patterns.

## Decision

We will **Selectively Carry-Forward and Adapt** rather than copy-pasting the v1 project en masse.

1. We **KEEP** infrastructural layers as-is: FastAPI layout, structlog configs, Langfuse bindings, JWT setup, Makefile/uv tooling.
2. We **REWRITE** the LangGraph state machine (`app/core/langgraph/graph.py`), removing generic multi-agent conversational patterns in favor of a strict `Triage -> Retrieve -> Summarize` deterministic graph.
3. We **DISCARD** generic API endpoints that expose open-ended chat, instead creating strict workflow endpoints.

## Consequences

- The v2 repo remains clean without leftover boilerplate (e.g., "whatsapp-food-order" references).
- The transition from chatbot to operational copilot is structurally enforced at the API and Graph layer.
