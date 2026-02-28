"""Rate-limiting configuration for the SeshOps API.

Uses slowapi to enforce per-IP request quotas.  Default limits are pulled
from ``Settings.RATE_LIMIT_DEFAULT`` and can be overridden per-endpoint
via the ``@limiter.limit(...)`` decorator.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=settings.RATE_LIMIT_DEFAULT,
)
