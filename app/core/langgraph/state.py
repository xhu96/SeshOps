"""State definition for the SeshOps triage LangGraph.

``TriageState`` is a TypedDict that flows through every node in the
deterministic ``triage → retrieve → summarize`` pipeline, accumulating
extracted fields at each step.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import BaseMessage


class TriageState(TypedDict):
    """Mutable state carried through the SeshOps triage graph.

    Attributes:
        incident_input: Raw alert text or operator description.
        service_name: Service identified by the triage node.
        symptoms: Symptoms extracted by the triage node.
        runbook_context: Markdown excerpts retrieved by the retrieve node.
        diagnostic_summary: Final summary produced by the summarise node.
        messages: Conversation history accumulated during the run.
    """

    incident_input: str
    service_name: str
    symptoms: str
    runbook_context: str
    diagnostic_summary: str
    messages: list[BaseMessage]
