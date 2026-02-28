"""SeshOps prompt templates.

Centralises all prompts used by the LangGraph triage pipeline.  Extracting
them from graph node code enables versioning, A/B testing, and prompt
engineering without modifying the orchestration logic.
"""

from __future__ import annotations


# ── Node 1: Triage ───────────────────────────────────────────────────────────

TRIAGE_SYSTEM = "You always output valid JSON."

TRIAGE_USER = """\
You are an instance of SeshOps. Read the following incident alert or user report
and extract the affected `service_name` and the `symptoms`.
Respond strictly in JSON format: {{"service_name": "...", "symptoms": "..."}}

Incident: {incident_input}
"""

# ── Node 3: Summarise ────────────────────────────────────────────────────────

SUMMARISE_USER = """\
You are an L3 Platform Engineer. Generate a concise diagnostic summary
for the following incident based on the provided runbook context.

Service: {service_name}
Symptoms: {symptoms}

Runbook Context:
{runbook_context}
"""
