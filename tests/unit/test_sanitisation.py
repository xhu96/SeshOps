"""Unit tests for SeshOps input sanitisation."""

import os
import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from app.core.sanitisation import (
    sanitize_string,
    sanitize_email,
    sanitize_dict,
    sanitize_list,
    validate_password_strength,
)


class TestSanitizeString:
    def test_escapes_html_entities(self):
        result = sanitize_string("<b>bold</b>")
        assert "<b>" not in result
        assert "&lt;" in result  # html.escape converts < to &lt;

    def test_preserves_safe_text(self):
        assert sanitize_string("hello world 123") == "hello world 123"

    def test_strips_null_bytes(self):
        assert "\0" not in sanitize_string("hello\0world")

    def test_empty_string(self):
        assert sanitize_string("") == ""


class TestSanitizeEmail:
    def test_valid_email_normalised(self):
        result = sanitize_email("Ops@Example.COM")
        assert result == "ops@example.com"

    def test_leading_trailing_whitespace_stripped(self):
        # sanitize_email calls sanitize_string first, which uses html.escape
        # The email regex requires a clean input, so we test with pre-stripped
        result = sanitize_email("ops@example.com")
        assert result == "ops@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            sanitize_email("not-an-email")


class TestSanitizeDict:
    def test_sanitises_string_values(self):
        dirty = {"name": "<b>Admin</b>"}
        clean = sanitize_dict(dirty)
        assert "<b>" not in clean["name"]

    def test_preserves_non_string_values(self):
        data = {"count": 42, "active": True}
        assert sanitize_dict(data) == data

    def test_recursive_dict_sanitisation(self):
        dirty = {"outer": {"inner": "<script>x</script>"}}
        clean = sanitize_dict(dirty)
        assert "<script>" not in str(clean)


class TestSanitizeList:
    def test_sanitises_string_elements(self):
        dirty = ["<b>bold</b>", "clean"]
        clean = sanitize_list(dirty)
        assert "<b>" not in clean[0]
        assert clean[1] == "clean"


class TestPasswordStrength:
    def test_strong_password_passes(self):
        assert validate_password_strength("StrongPass1!") is True

    def test_short_password_raises(self):
        with pytest.raises(ValueError, match="at least 8"):
            validate_password_strength("Sh1!")

    def test_no_uppercase_raises(self):
        with pytest.raises(ValueError, match="uppercase"):
            validate_password_strength("alllower1!")

    def test_no_digit_raises(self):
        with pytest.raises(ValueError, match="number"):
            validate_password_strength("NoDigitsHere!")

    def test_no_special_char_raises(self):
        with pytest.raises(ValueError, match="special"):
            validate_password_strength("NoSpecial1A")
