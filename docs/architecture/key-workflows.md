# Key Workflows

## 1. Incident Triage Workflow

The primary workflow triggered by an incoming alert payload or user description.

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI Router
    participant Orchestrator as LangGraph StateMachine
    participant LLM as LLM Provider
    participant DB as pgvector

    User->>API: POST /api/v1/operations/triage {alert_text}
    API->>Orchestrator: Initialize Triage State

    Orchestrator->>LLM: Parse service and symptoms
    LLM-->>Orchestrator: {service: "auth", issue: "502s"}

    Orchestrator->>DB: Search Runbooks (Vector Search)
    DB-->>Orchestrator: Return Runbook Context

    Orchestrator->>LLM: Generate Diagnostic Summary
    LLM-->>Orchestrator: Formatted Markdown Draft

    Orchestrator-->>API: Stream tokens to client
    API-->>User: Display summary and next step recommendations
```

## 2. Ingestion & Retrieval (RAG)

Runbook markdown files are parsed into documents, chunked, embedded using `text-embedding-3-small` (or standard provider embedder), and upserted into `pgvector` collections.
