# Contributing to SeshOps

## Getting Started

```bash
# Clone the repo
git clone https://github.com/your-org/seshops.git
cd seshops

# Install uv (if not installed)
pip install uv

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env  # edit with your values
```

## Development Workflow

### Run the Development Server

```bash
make dev
```

### Run Tests

```bash
make test                     # All tests
make test ARGS="-k test_auth" # Filter by pattern
```

### Lint & Format

```bash
make lint     # ruff check
make format   # ruff format
```

### Pre-commit Hooks

```bash
# Install hooks (one-time)
pre-commit install

# Run against all files
pre-commit run --all-files
```

## Branch Strategy

- `main` — Protected. Requires PR + CI green.
- `feature/<name>` — Short-lived feature branches.
- `fix/<name>` — Bug fix branches.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add streaming triage response
fix: narrow health check exception
docs: add ADR for anyio choice
```

## Architecture Overview

```
Client Request
    │
    ▼
┌──────────┐
│  FastAPI  │──▶ Auth (JWT)
│  Router   │──▶ Rate Limiter
└──────────┘
    │
    ▼
┌──────────────────────────────────┐
│       LangGraph Pipeline         │
│                                  │
│  triage ──▶ retrieve ──▶ summarize │
│    │           │            │      │
│    ▼           ▼            ▼      │
│  LLMService  RAGService  LLMService│
└──────────────────────────────────┘
    │
    ▼
┌──────────┐     ┌──────────┐
│ Postgres │     │ pgvector │
│ (users)  │     │ (runbooks│
└──────────┘     └──────────┘
```

## Adding a New LangGraph Node

1. Define the node function in `app/core/langgraph/graph.py`
2. Add any prompts to `app/core/prompts.py`
3. Register the node in `TriageGraph.compile()`
4. Add edges to connect it to the existing topology
5. Write a test in `tests/integration/test_pipeline.py`

## Key Files

| File                          | Purpose                          |
| ----------------------------- | -------------------------------- |
| `app/core/config.py`          | All settings (pydantic-settings) |
| `app/core/security.py`        | JWT + auth schemas               |
| `app/core/prompts.py`         | LLM prompt templates             |
| `app/core/protocols.py`       | Service interfaces (Protocol)    |
| `app/core/events.py`          | Log event constants              |
| `app/services/llm.py`         | LLM with circular fallback       |
| `app/services/rag.py`         | Runbook retrieval                |
| `app/core/langgraph/graph.py` | Triage pipeline (core IP)        |
