"""Prometheus metrics for SeshOps observability.

Exposes counters, histograms, and gauges that track HTTP traffic,
LLM inference latency, and SeshOps-specific business metrics.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram
from starlette_prometheus import PrometheusMiddleware, metrics

# ── HTTP metrics ─────────────────────────────────────────────────────────────

http_requests_total = Counter(
    "seshops_http_requests_total",
    "Total HTTP requests handled by SeshOps",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "seshops_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# ── Database metrics ─────────────────────────────────────────────────────────

db_connections = Gauge(
    "seshops_db_connections",
    "Active database connections",
)

# ── Triage pipeline metrics ──────────────────────────────────────────────────

triage_requests_total = Counter(
    "seshops_triage_requests_total",
    "Total incident triage requests processed",
)

llm_inference_duration_seconds = Histogram(
    "seshops_llm_inference_duration_seconds",
    "Time spent on a single SeshOps LLM call",
    ["model"],
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 5.0],
)

llm_stream_duration_seconds = Histogram(
    "seshops_llm_stream_duration_seconds",
    "Time spent on streamed SeshOps LLM inference",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)


def setup_metrics(app) -> None:
    """Attach Prometheus middleware and ``/metrics`` route to the FastAPI app."""
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", metrics)
