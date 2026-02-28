"""SeshOps API v1 router configuration.

Aggregates the authentication and operations sub-routers under the
``/api/v1`` prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.operations import router as operations_router
from app.core.logging import logger

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(
    operations_router, prefix="/operations", tags=["operations"]
)


@api_router.get("/health")
async def health_check():
    """Lightweight liveness probe for the SeshOps API layer."""
    logger.info("seshops_api_health_checked")
    return {"status": "healthy", "version": "1.0.0"}
