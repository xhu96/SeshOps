"""Integration test for the SeshOps auth flow: register → login → session → list.

Uses the FastAPI TestClient against real in-memory SQLite.
"""

import os
import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.main import app
from app.models.engine import engine


@pytest.fixture(scope="module")
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as tc:
        yield tc


def test_full_auth_flow(client):
    """Run the complete auth lifecycle: register → login → create session → list sessions."""

    # ── Step 1: Register ────────────────────────────────────────────
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "flow@seshops.io", "password": "FlowTest1!"},
    )
    assert reg.status_code == 200, reg.json()
    data = reg.json()
    assert data["email"] == "flow@seshops.io"
    assert "token" in data
    token = data["token"]["access_token"]

    # ── Step 2: Login ───────────────────────────────────────────────
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "flow@seshops.io", "password": "FlowTest1!", "grant_type": "password"},
    )
    assert login.status_code == 200, login.json()
    login_token = login.json()["access_token"]
    assert login_token  # non-empty

    # ── Step 3: Create Session ──────────────────────────────────────
    session = client.post(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert session.status_code == 200, session.json()
    sess_data = session.json()
    assert "session_id" in sess_data
    session_id = sess_data["session_id"]

    # ── Step 4: List Sessions ───────────────────────────────────────
    sessions = client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert sessions.status_code == 200
    sess_list = sessions.json()
    assert any(s["session_id"] == session_id for s in sess_list)

    # ── Step 5: Delete Session ──────────────────────────────────────
    sess_token = sess_data["token"]["access_token"]
    delete = client.delete(
        f"/api/v1/auth/session/{session_id}",
        headers={"Authorization": f"Bearer {sess_token}"},
    )
    assert delete.status_code == 200


def test_register_duplicate_returns_400(client):
    """Registering the same email twice should fail."""
    # First registration (may already exist from previous test)
    client.post(
        "/api/v1/auth/register",
        json={"email": "dupeflow@seshops.io", "password": "DupeTest1!"},
    )
    # Second registration — should fail
    dupe = client.post(
        "/api/v1/auth/register",
        json={"email": "dupeflow@seshops.io", "password": "DupeTest1!"},
    )
    assert dupe.status_code == 400


def test_login_wrong_password_returns_401(client):
    """Login with wrong password should fail."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "flow@seshops.io", "password": "WrongPassword1!", "grant_type": "password"},
    )
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client):
    """Accessing a protected endpoint without a token should return 403."""
    resp = client.get("/api/v1/auth/sessions")
    assert resp.status_code == 403
