"""SeshOps deterministic triage graph.

Implements the core ``triage → retrieve → summarize`` LangGraph pipeline
that powers the SeshOps incident response workflow.  The graph topology
is strictly deterministic — no conditional routing.

**This is the core IP of the platform.  Do not alter the node semantics
or edge topology without explicit approval.**
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.events import LogEvents
from app.core.langgraph.state import TriageState
from app.core.logging import logger
from app.core.prompts import SUMMARISE_USER, TRIAGE_SYSTEM, TRIAGE_USER
from app.core.protocols import LLMServiceProtocol, RAGServiceProtocol
from app.services.llm import llm_service
from app.services.rag import rag_service as default_rag_service


class TriageGraph:
    """Orchestrates the SeshOps incident triage workflow.

    Nodes:
        1. **triage** — parse the raw alert to extract ``service_name`` and ``symptoms``.
        2. **retrieve** — pull relevant runbook context from the vector store.
        3. **summarize** — generate a diagnostic summary using the runbook context.

    Services are injected via constructor for testability. Defaults to the
    module-level singletons for production use.
    """

    def __init__(
        self,
        llm: LLMServiceProtocol | None = None,
        rag: RAGServiceProtocol | None = None,
    ) -> None:
        self.llm_service = llm or llm_service
        self.rag_service = rag or default_rag_service
        self._graph: CompiledStateGraph | None = None

    # ── Node 1: Triage ───────────────────────────────────────────────────

    async def triage_incident(self, state: TriageState) -> dict:
        """Parse the raw incident alert to extract service and symptoms."""
        logger.info(LogEvents.TRIAGE_STARTED, preview=state["incident_input"][:50])

        prompt = TRIAGE_USER.format(incident_input=state["incident_input"])

        response = await self.llm_service.call([
            SystemMessage(content=TRIAGE_SYSTEM),
            HumanMessage(content=prompt),
        ])

        try:
            parsed = json.loads(response.content)
            service_name = parsed.get("service_name", "unknown")
            symptoms = parsed.get("symptoms", "unknown")
        except (json.JSONDecodeError, TypeError):
            logger.error(
                LogEvents.TRIAGE_PARSE_FAILED,
                raw_content=str(response.content)[:200],
            )
            service_name = "unknown"
            symptoms = "unable to parse symptoms"

        return {"service_name": service_name, "symptoms": symptoms}

    # ── Node 2: Retrieve ─────────────────────────────────────────────────

    async def retrieve_runbook(self, state: TriageState) -> dict:
        """Fetch relevant runbook excerpts from the vector store.

        Falls back to a no-context message if the RAG service is unreachable.
        """
        logger.info(LogEvents.RETRIEVE_STARTED, service=state.get("service_name"))

        query = f"service: {state.get('service_name')} symptoms: {state.get('symptoms')}"
        try:
            context = await self.rag_service.search_runbooks(query, limit=2)
        except Exception as exc:
            logger.error(
                LogEvents.RUNBOOK_SEARCH_FAILED,
                query=query,
                error=str(exc),
            )
            context = "No runbook context available — RAG service unreachable."

        return {"runbook_context": context}

    # ── Node 3: Summarise ────────────────────────────────────────────────

    async def generate_summary(self, state: TriageState) -> dict:
        """Produce the final diagnostic summary for the operator."""
        logger.info(LogEvents.SUMMARISE_STARTED)

        prompt = SUMMARISE_USER.format(
            service_name=state.get("service_name"),
            symptoms=state.get("symptoms"),
            runbook_context=state.get("runbook_context"),
        )

        response = await self.llm_service.call([HumanMessage(content=prompt)])
        return {"diagnostic_summary": response.content}

    # ── Compilation ──────────────────────────────────────────────────────

    def compile(self) -> CompiledStateGraph:
        """Build and cache the deterministic triage graph.

        Topology: ``triage → retrieve → summarize → END``
        """
        if not self._graph:
            workflow = StateGraph(TriageState)

            workflow.add_node("triage", self.triage_incident)
            workflow.add_node("retrieve", self.retrieve_runbook)
            workflow.add_node("summarize", self.generate_summary)

            workflow.set_entry_point("triage")
            workflow.add_edge("triage", "retrieve")
            workflow.add_edge("retrieve", "summarize")
            workflow.add_edge("summarize", END)

            self._graph = workflow.compile()
            logger.info(LogEvents.GRAPH_COMPILED)

        return self._graph
