"""Unit tests for SeshOps data models."""

import os
import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from app.models.user import User


class TestUserModel:
    def test_hash_password_returns_string(self):
        hashed = User.hash_password("SecurePass1!")
        assert isinstance(hashed, str)
        assert hashed != "SecurePass1!"

    def test_verify_password_correct(self):
        hashed = User.hash_password("SecurePass1!")
        user = User(email="test@example.com", hashed_password=hashed)
        assert user.verify_password("SecurePass1!") is True

    def test_verify_password_incorrect(self):
        hashed = User.hash_password("SecurePass1!")
        user = User(email="test@example.com", hashed_password=hashed)
        assert user.verify_password("WrongPassword!") is False

    def test_hash_is_unique_per_call(self):
        """Bcrypt salts should produce different hashes for the same input."""
        h1 = User.hash_password("SamePassword1!")
        h2 = User.hash_password("SamePassword1!")
        assert h1 != h2  # Different salts

    def test_user_email_field(self):
        user = User(email="ops@seshops.io", hashed_password="x")
        assert user.email == "ops@seshops.io"
