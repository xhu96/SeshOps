# ADR-003: Circular Model Fallback for LLM Resilience

## Status

Accepted

## Context

SeshOps depends on external LLM APIs (OpenAI, OpenRouter) for the triage pipeline. Individual providers experience rate limits, timeouts, and outages. Single-provider setups are a single point of failure.

## Decision

Implement a circular fallback strategy: when the current LLM model exhausts its retry budget, automatically rotate to the next model in the `LLMRegistry`. After all models are exhausted, a circuit breaker opens for 60 seconds to prevent retry storms.

## Rationale

- IT operations incidents don't wait for API outages — the triage pipeline must be maximally available.
- Per-model retry (via `tenacity`) handles transient errors; circular fallback handles sustained failures.
- A circuit breaker prevents cascading retry storms when all providers are simultaneously down.
- The circuit auto-resets after a cooldown period, allowing recovery without human intervention.

## Consequences

- Adding a new LLM provider only requires a new entry in `LLMRegistry.LLMS`.
- Response latency increases under fallback (retries + model switch).
- The circuit breaker state is in-process only — not shared across uvicorn workers. Each worker tracks its own circuit state.
- In the worst case (all providers down, circuit open), the triage pipeline returns a 500 within milliseconds instead of timing out after minutes.
