"""SeshOps — IT Operations Copilot.

Application entry point.  Configures the FastAPI instance with middleware,
security headers, rate limiting, Prometheus metrics, CORS, and the v1 API
router.  The lifespan context manager handles startup/shutdown logging.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from langfuse import Langfuse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import setup_metrics
from app.core.middleware import LoggingContextMiddleware, MetricsMiddleware
from app.services.database import database_service

load_dotenv()

# ── Langfuse telemetry ───────────────────────────────────────────────────────

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log SeshOps startup and shutdown events; enforce security gates."""
    # ── Startup security gates ───────────────────────────────────────
    from app.core.config import Environment

    if settings.ENVIRONMENT == Environment.PRODUCTION:
        if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY in (
            "change-me-in-production",
            "",
        ):
            logger.critical("seshops_fatal_insecure_jwt_secret")
            raise SystemExit(
                "FATAL: JWT_SECRET_KEY must be set to a strong, unique value "
                "in production. Refusing to start."
            )
        if "*" in settings.ALLOWED_ORIGINS:
            logger.warning(
                "seshops_cors_wildcard_in_production",
                hint="Set ALLOWED_ORIGINS to specific domains",
            )

    logger.info(
        "seshops_starting",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        api_prefix=settings.API_V1_STR,
        environment=settings.ENVIRONMENT.value,
    )
    yield
    logger.info("seshops_stopping")


# ── Application factory ─────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Prometheus
setup_metrics(app)

# Logging context (must precede other middleware)
app.add_middleware(LoggingContextMiddleware)

# Custom Prometheus counters
app.add_middleware(MetricsMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Validation errors
@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
):
    """Return a structured 422 response for invalid request payloads."""
    from app.core.events import LogEvents

    logger.error(
        LogEvents.VALIDATION_ERROR,
        path=request.url.path,
        client_host=request.client.host if request.client else "unknown",
        errors=str(exc.errors()),
    )
    formatted = [
        {
            "field": " -> ".join(
                str(p) for p in err["loc"] if p != "body"
            ),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "code": "VALIDATION_ERROR",
            "errors": formatted,
        },
    )


# Security headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append standard security headers to every SeshOps response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


# ── Root & health endpoints ──────────────────────────────────────────────────

@app.get("/")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["root"][0])
async def root(request: Request):
    """SeshOps root — returns platform identity and swagger links."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT.value,
        "swagger_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/health")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["health"][0])
async def health_check(request: Request) -> Dict[str, Any]:
    """Deep health check including database and LLM connectivity."""
    db_ok = await database_service.health_check()

    # LLM probe: check model is initialised and circuit breaker is closed
    from app.services.llm import llm_service

    llm_ok = llm_service.get_llm() is not None and not llm_service._circuit_open

    all_ok = db_ok and llm_ok
    payload = {
        "status": "healthy" if all_ok else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT.value,
        "components": {
            "api": "healthy",
            "database": "healthy" if db_ok else "unhealthy",
            "llm": "healthy" if llm_ok else "unhealthy",
        },
        "timestamp": datetime.now().isoformat(),
    }

    code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=code)
