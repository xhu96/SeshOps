"""Integration tests for the SeshOps triage endpoint."""

import pytest
from unittest.mock import patch

from langchain_core.messages import AIMessage


async def mock_llm_call(messages, *args, **kwargs):
    """Deterministic LLM stub for the triage pipeline tests."""
    prompt_text = str(messages[-1].content)
    if "extract the affected `service_name` and the `symptoms`" in prompt_text:
        return AIMessage(
            content='{"service_name": "database", "symptoms": "High latency and connection drops"}'
        )
    elif "Generate a concise diagnostic summary" in prompt_text:
        return AIMessage(
            content=(
                "**Diagnostic Summary:** Database latency is high due to "
                "connection scaling limits. Action: Increase max-connections "
                "and reboot."
            )
        )
    return AIMessage(content="mocked response")


async def mock_rag_search(query, limit=3):
    """Deterministic RAG stub returning a runbook excerpt."""
    return "### Source: Database Scale Guide\nIncrease max-connections parameter in postmaster.conf."


@pytest.fixture
def auth_header(client):
    """Register and log in a test operator, returning a Bearer header."""
    email = "ops_admin@example.com"
    password = "OpsPassword123!"

    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_triage_incident_endpoint(client, auth_header):
    """POST /triage triggers the LangGraph pipeline and returns a diagnostic."""
    payload = {
        "incident_input": (
            "We have very high latency in the primary Postgres database "
            "and clients are dropping connections."
        )
    }

    with (
        patch(
            "app.core.langgraph.graph.llm_service.call",
            side_effect=mock_llm_call,
        ),
        patch(
            "app.services.rag.rag_service.search_runbooks",
            side_effect=mock_rag_search,
        ),
    ):
        response = client.post(
            "/api/v1/operations/triage",
            json=payload,
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "database"
        assert "latency" in data["symptoms"].lower()
        assert "Summary" in data["diagnostic_summary"]


def test_triage_unauthorized(client):
    """Triage endpoint rejects unauthenticated requests."""
    response = client.post(
        "/api/v1/operations/triage",
        json={"incident_input": "The world is on fire"},
    )
    assert response.status_code == 403
    assert "Not authenticated" in response.json()["detail"]
