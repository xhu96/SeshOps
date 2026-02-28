"""Input sanitisation utilities for SeshOps.

Provides defence-in-depth helpers for escaping user-supplied strings,
validating emails, and enforcing password-strength rules before data
reaches the persistence or LLM layers.
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List


def sanitize_string(value: str) -> str:
    """Escape HTML entities and strip injection vectors from *value*."""
    if not isinstance(value, str):
        value = str(value)

    value = html.escape(value)
    value = re.sub(
        r"&lt;script.*?&gt;.*?&lt;/script&gt;", "", value, flags=re.DOTALL
    )
    value = value.replace("\0", "")
    return value


def sanitize_email(email: str) -> str:
    """Normalise and validate an email address for SeshOps operator accounts."""
    email = sanitize_string(email)

    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email format")

    return email.lower()


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitise all string values in a nested dictionary."""
    result: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_string(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = sanitize_list(value)
        else:
            result[key] = value
    return result


def sanitize_list(data: List[Any]) -> List[Any]:
    """Recursively sanitise all string values in a nested list."""
    result: List[Any] = []
    for item in data:
        if isinstance(item, str):
            result.append(sanitize_string(item))
        elif isinstance(item, dict):
            result.append(sanitize_dict(item))
        elif isinstance(item, list):
            result.append(sanitize_list(item))
        else:
            result.append(item)
    return result


def validate_password_strength(password: str) -> bool:
    """Raise ``ValueError`` if *password* does not meet SeshOps policy.

    Policy: ≥ 8 chars, mixed case, at least one digit and one special char.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")
    return True
