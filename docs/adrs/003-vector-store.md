# ADR 003: Vector Store and State Checkpointing

**Date:** 2026-02-27
**Status:** Accepted

## Context

The agent requires:

1. Long-term semantic memory (`mem0ai`)
2. Vector storage for knowledge retrieval (SOPs, Runbooks)
3. Checkpoint storage for LangGraph state persistence

## Decision

We will standardize on **PostgreSQL with pgvector** for all three needs, carrying forward the architectural decision from v1.

## Consequences

- Reduces infrastructure sprawl (no need for standalone Redis, Pinecone, or ChromaDB).
- Native support in `LangGraph` (`AsyncPostgresSaver`) and `mem0ai`.
- Easily portable to Azure Database for PostgreSQL in the future.
