# ADR 002: Provider Abstraction and Azure Migration Path

**Date:** 2026-02-27
**Status:** Accepted

## Context

We are starting local-first, likely utilizing OpenAI APIs directly. However, for a future enterprise deployment, this application will need to run within Azure environments utilizing Azure OpenAI and strict data locality controls.

## Decision

We will implement a **Thin Provider Abstraction** using `langchain-core` capabilities. All LLM instantiations must use an abstraction factory (e.g. `get_llm_model()`) that reads from environment variables (`LLM_PROVIDER`, `AZURE_OPENAI_ENDPOINT`).

## Consequences

- No direct `import openai` in business logic or graph nodes.
- Local MVP development is unblocked using standard OpenAI keys.
- Changing `LLM_PROVIDER=azure` automatically switches the LangChain class instantiated (e.g. `AzureChatOpenAI`) without requiring changes to the LangGraph core logic.
