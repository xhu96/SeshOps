# Definition of Done

A backlog slice is not marked complete until:

1. The code executes locally without syntax or runtime crashes.
2. The specific slice validation gate (e.g. `make test`, `curl` command) succeeds.
3. Errors and failures are recorded in `docs/status/verification-log.md`.
4. If the slice involves LLMs, it uses the provider abstraction and Langfuse tracing.

# Validation Gates

- **Slice 1 (Backend Skeleton):** `make dev` succeeds. `curl http://localhost:8000/health` returns `200 OK`.
- **Slice 3 (Triage LangGraph):** A mocked execution of the graph from start to end node completes without throwing state errors.
- **Slice 4 (RAG):** Manual database query reveals embedded vectors; test script retrieves top-K correctly.
- **Slice 7 (Evals):** `make eval` runs the dataset against Langfuse and reports a specific >90% score format.
