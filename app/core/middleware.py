"""SeshOps HTTP middleware.

Provides request-level observability — Prometheus counters/histograms and
per-request structlog context (operator ID, session ID extracted from JWT).
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import bind_context, clear_context
from app.core.metrics import http_request_duration_seconds, http_requests_total


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request counts and latency for Prometheus dashboards."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration = time.time() - start
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=status,
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path,
            ).observe(duration)
        return response


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Inject operator and session identifiers into the structlog context.

    Decodes the JWT (if present) to bind ``session_id`` and ``user_id``
    so every log line emitted during the request is attributable.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            clear_context()

            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    payload = jwt.decode(
                        token,
                        settings.JWT_SECRET_KEY,
                        algorithms=[settings.JWT_ALGORITHM],
                    )
                    subject = payload.get("sub")
                    if subject:
                        bind_context(session_id=subject)
                except JWTError:
                    pass  # Let the auth dependency handle invalid tokens

            response = await call_next(request)

            if hasattr(request.state, "user_id"):
                bind_context(user_id=request.state.user_id)

            return response
        finally:
            clear_context()
