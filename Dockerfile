# ── SeshOps — IT Operations Copilot ──────────────────────────────────────────
# Multi-stage build: slim Python base with uv for fast dependency resolution.

FROM python:3.13.2-slim

WORKDIR /app

ARG APP_ENV=production

ENV APP_ENV=${APP_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# System deps required by psycopg and bcrypt
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && pip install --upgrade pip \
    && pip install uv \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (layer cached unless pyproject.toml changes)
COPY pyproject.toml .
RUN uv venv && . .venv/bin/activate && uv pip install -e . && uv cache clean

# Copy application source
COPY . .

# Make entrypoint executable before switching to non-root user
RUN chmod +x /app/scripts/docker-entrypoint.sh

# Run as non-root
RUN useradd -m seshops && chown -R seshops:seshops /app
USER seshops

RUN mkdir -p /app/logs

EXPOSE 8000

RUN echo "SeshOps starting in ${APP_ENV} environment"

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]