"""Unit tests for SeshOps security module (JWT + validation)."""

import os
import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from app.core.security import (
    Token,
    UserCreate,
    create_access_token,
    verify_token,
)


class TestTokenLifecycle:
    """JWT creation and verification round-trip."""

    def test_create_access_token_returns_token(self):
        token = create_access_token(subject="42")
        assert isinstance(token, Token)
        assert token.token_type == "bearer"
        assert token.access_token  # non-empty

    def test_verify_token_round_trip(self):
        token = create_access_token(subject="user-99")
        subject = verify_token(token.access_token)
        assert subject == "user-99"

    def test_verify_token_tampered_returns_none(self):
        token = create_access_token(subject="user-1")
        tampered = token.access_token[:-5] + "XXXXX"
        assert verify_token(tampered) is None

    def test_verify_token_invalid_format_raises(self):
        with pytest.raises(ValueError, match="invalid"):
            verify_token("not-a-jwt")

    def test_verify_token_empty_string_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            verify_token("")


class TestUserCreateValidation:
    """Password strength enforcement on UserCreate."""

    def test_valid_password_accepted(self):
        user = UserCreate(email="ops@example.com", password="SecurePass1!")
        assert user.email == "ops@example.com"

    def test_short_password_rejected(self):
        with pytest.raises(Exception):
            UserCreate(email="ops@example.com", password="Sh1!")

    def test_no_uppercase_rejected(self):
        with pytest.raises(Exception):
            UserCreate(email="ops@example.com", password="alllower1!")

    def test_no_digit_rejected(self):
        with pytest.raises(Exception):
            UserCreate(email="ops@example.com", password="NoDigitsHere!")

    def test_no_special_char_rejected(self):
        with pytest.raises(Exception):
            UserCreate(email="ops@example.com", password="NoSpecial1A")
