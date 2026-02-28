"""Consistent API error response model for SeshOps.

All error responses — validation, authentication, server errors — use
this schema so that API consumers can always rely on a predictable
JSON structure.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Single field-level validation error."""

    field: str = ""
    message: str = ""


class ErrorResponse(BaseModel):
    """Standard error payload returned by all SeshOps API endpoints.

    Attributes:
        detail: Human-readable error summary.
        code: Machine-readable error code (e.g. ``VALIDATION_ERROR``).
        errors: Optional list of field-level errors for 422 responses.
    """

    detail: str
    code: str = "UNKNOWN_ERROR"
    errors: list[ErrorDetail] = []
