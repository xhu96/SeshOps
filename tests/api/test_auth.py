"""Integration tests for SeshOps operator authentication endpoints."""

import pytest


@pytest.fixture(scope="module")
def test_user_data():
    return {
        "email": "testoperator@example.com",
        "password": "SecurePassword123!",
    }


def test_register_operator_success(client, test_user_data):
    """An operator can register with a valid email and strong password."""
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert "token" in data
    assert "id" in data


def test_register_duplicate_operator(client, test_user_data):
    """Registering the same email twice returns 400."""
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_login_operator_success(client, test_user_data):
    """A registered operator can log in with correct credentials."""
    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"],
        "grant_type": "password",
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_operator_bad_password(client, test_user_data):
    """Login with the wrong password returns 401."""
    login_data = {
        "username": test_user_data["email"],
        "password": "WrongPassword123!",
        "grant_type": "password",
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401
