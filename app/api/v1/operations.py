"""SeshOps triage endpoint — core API surface.

Exposes the ``POST /triage`` endpoint that accepts an incident description,
runs it through the deterministic LangGraph pipeline, and returns a
structured diagnostic summary to the operator.

**This is 100% original code — not derived from any template.**
"""

from __future__ import annotations

import anyio
from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.events import LogEvents
from app.core.langgraph.graph import TriageGraph
from app.core.logging import logger
from app.models.operations import TriageRequest, TriageResponse
from app.models.user import User

router = APIRouter()

triage_graph_manager = TriageGraph()

# Configurable per-request timeout (seconds)
TRIAGE_TIMEOUT_SECONDS: float = 120.0


@router.post("/triage", response_model=TriageResponse)
async def triage_incident(
    request: TriageRequest,
    current_user: User = Depends(get_current_user),
):
    """Run an incident through the SeshOps triage pipeline.

    Accepts a raw alert or operator description and returns service
    identification, symptom extraction, and a diagnostic summary
    grounded in retrieved runbook context.

    An ``anyio.fail_after`` guard ensures unbounded LLM/RAG latency
    never keeps the request open indefinitely.
    """
    try:
        logger.info(LogEvents.TRIAGE_REQUESTED, user_id=current_user.id)

        compiled = triage_graph_manager.compile()
        initial_state = {"incident_input": request.incident_input, "messages": []}

        with anyio.fail_after(TRIAGE_TIMEOUT_SECONDS):
            final_state = await compiled.ainvoke(initial_state)

        return TriageResponse(
            service_name=final_state.get("service_name", "unknown"),
            symptoms=final_state.get("symptoms", "unknown"),
            diagnostic_summary=final_state.get(
                "diagnostic_summary", "No summary generated."
            ),
        )

    except TimeoutError:
        logger.error(
            LogEvents.TRIAGE_FAILED,
            error="Request timed out",
            timeout_seconds=TRIAGE_TIMEOUT_SECONDS,
        )
        raise HTTPException(
            status_code=504,
            detail=f"Triage pipeline timed out after {TRIAGE_TIMEOUT_SECONDS}s.",
        )

    except Exception as exc:
        logger.error(LogEvents.TRIAGE_FAILED, error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to process incident triage."
        )
