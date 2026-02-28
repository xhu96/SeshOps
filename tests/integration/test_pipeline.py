"""Integration test for the SeshOps triage LangGraph pipeline.

Mocks the LLM service to return fixed JSON, then asserts the full
triage → retrieve → summarize pipeline produces expected output.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeLLMResponse:
    """Minimal LLM response object with a .content attribute."""

    def __init__(self, content: str) -> None:
        self.content = content


@pytest.fixture
def mock_llm():
    """LLM service that returns fixed triage JSON on first call, summary on second."""
    llm = AsyncMock()
    llm.call = AsyncMock(
        side_effect=[
            FakeLLMResponse('{"service_name": "auth-service", "symptoms": "high latency"}'),
            FakeLLMResponse("Diagnostic: auth-service experiencing high latency due to connection pool saturation."),
        ]
    )
    return llm


@pytest.fixture
def mock_rag():
    """RAG service that returns a fixed runbook context."""
    rag = AsyncMock()
    rag.search_runbooks = AsyncMock(
        return_value="### Source: Auth Runbook\nRestart auth pods if latency > 5s."
    )
    return rag


async def test_full_triage_pipeline(mock_llm, mock_rag):
    """Run the full triage → retrieve → summarize pipeline with mocked services."""
    from app.core.langgraph.graph import TriageGraph

    graph = TriageGraph(llm=mock_llm, rag=mock_rag)
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "incident_input": "auth-service is down with 503 errors",
        "messages": [],
    })

    # Node 1 output
    assert result["service_name"] == "auth-service"
    assert result["symptoms"] == "high latency"

    # Node 2 output (from mock RAG)
    assert "Auth Runbook" in result["runbook_context"]

    # Node 3 output (from mock LLM second call)
    assert "connection pool saturation" in result["diagnostic_summary"]

    # Verify both LLM calls were made (triage + summarize)
    assert mock_llm.call.call_count == 2

    # Verify RAG was called once (retrieve)
    mock_rag.search_runbooks.assert_called_once()


async def test_pipeline_with_malformed_llm_json(mock_rag):
    """When LLM returns invalid JSON, triage should gracefully degrade."""
    from app.core.langgraph.graph import TriageGraph

    bad_llm = AsyncMock()
    bad_llm.call = AsyncMock(
        side_effect=[
            FakeLLMResponse("this is not json at all"),
            FakeLLMResponse("Diagnostic: unable to determine root cause."),
        ]
    )

    graph = TriageGraph(llm=bad_llm, rag=mock_rag)
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "incident_input": "something broke",
        "messages": [],
    })

    assert result["service_name"] == "unknown"
    assert "unable to parse" in result["symptoms"]
    assert result["diagnostic_summary"] is not None


async def test_pipeline_with_rag_failure():
    """When RAG is unreachable, pipeline should still complete with fallback."""
    from app.core.langgraph.graph import TriageGraph

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        side_effect=[
            FakeLLMResponse('{"service_name": "db-service", "symptoms": "OOM kills"}'),
            FakeLLMResponse("Diagnostic: investigate memory limits."),
        ]
    )

    broken_rag = AsyncMock()
    broken_rag.search_runbooks = AsyncMock(side_effect=ConnectionError("RAG unreachable"))

    graph = TriageGraph(llm=mock_llm, rag=broken_rag)
    compiled = graph.compile()

    result = await compiled.ainvoke({
        "incident_input": "db-service OOM",
        "messages": [],
    })

    assert result["service_name"] == "db-service"
    assert "runbook context available" in result["runbook_context"].lower() or "unreachable" in result["runbook_context"].lower()
    assert result["diagnostic_summary"] is not None
