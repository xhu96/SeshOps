# Data Model Outline

## Core Relational Models (PostgreSQL via SQLModel)

1. **User / Session**: Based on V1 auth.
2. **Conversation / Thread**: Tracks the triage incident context.
3. **Audit Log**: Explicit ledger of actions taken by the copilot for security review.

## Vector / Memory Models

1. **Memories (`mem0ai`)**: Fragmented facts about the user's operational role and system preferences (e.g. `User is authorized to view billing-service logs`).
2. **Runbooks (Vector)**: Embedded chunks of markdown standard operating procedures, indexed by service name and symptom description.
