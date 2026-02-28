# ADR 004: Memory Model and Authentication MVP

**Date:** 2026-02-27
**Status:** Accepted

## Context

v1 utilized JWT authentication and mem0ai for user personalization ("remembering user preferences"). In an IT Operations context, memory has a different focus: environment facts and professional working context.

## Decision

- **Auth**: We will retain the v1 JWT implementation (`/api/v1/auth`) unmodified to secure the endpoints.
- **Memory**: The `mem0ai` namespace will be strictly segmented by `user_id`. The agent prompts will be directed to only store IT context (e.g. "User is responsible for the billing-service cluster") rather than personal conversational trivia.

## Consequences

- Auth remains robust out of the box.
- The `user_id` context provides a clean boundary for role-based reasoning later on.
- Prompts must actively shape what the long-term memory retains.
