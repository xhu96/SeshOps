"""SeshOps log event constants.

Centralises all structured log event names to prevent typos, enable
grep-ability, and make bulk-renaming safe.  Import from this module
rather than using raw strings.
"""

from __future__ import annotations


class LogEvents:
    """Namespaced log event identifiers for the SeshOps platform."""

    # ── Lifecycle ────────────────────────────────────────────────────
    STARTING = "seshops_starting"
    STOPPING = "seshops_stopping"

    # ── Auth ─────────────────────────────────────────────────────────
    OPERATOR_CREATED = "seshops_operator_created"
    OPERATOR_DELETED = "seshops_operator_deleted"
    TOKEN_MINTED = "seshops_token_minted"
    LOGIN_SUCCEEDED = "seshops_login_succeeded"
    LOGIN_FAILED = "seshops_login_failed"
    AUTH_FAILED = "seshops_auth_failed"

    # ── Sessions ─────────────────────────────────────────────────────
    SESSION_PERSISTED = "seshops_session_persisted"
    SESSION_RENAMED = "seshops_session_renamed"
    SESSION_REMOVED = "seshops_session_removed"
    SESSION_DELETED = "seshops_session_deleted"

    # ── Triage pipeline ──────────────────────────────────────────────
    TRIAGE_REQUESTED = "seshops_triage_requested"
    TRIAGE_STARTED = "seshops_triage_started"
    TRIAGE_PARSE_FAILED = "seshops_triage_parse_failed"
    TRIAGE_FAILED = "seshops_triage_failed"
    RETRIEVE_STARTED = "seshops_retrieve_started"
    SUMMARISE_STARTED = "seshops_summarise_started"
    GRAPH_COMPILED = "seshops_triage_graph_compiled"

    # ── LLM ──────────────────────────────────────────────────────────
    LLM_SERVICE_READY = "seshops_llm_service_ready"
    LLM_CALL_SUCCESSFUL = "seshops_llm_call_successful"
    LLM_CALL_FAILED = "seshops_llm_call_failed"
    LLM_FALLBACK = "seshops_llm_default_fallback"
    LLM_CIRCUIT_OPEN = "seshops_llm_circuit_open"
    LLM_ALL_MODELS_EXHAUSTED = "seshops_llm_all_models_exhausted"

    # ── RAG ──────────────────────────────────────────────────────────
    VECTORSTORE_INIT = "seshops_vectorstore_init"
    RUNBOOKS_INGESTED = "seshops_runbooks_ingested"
    RUNBOOKS_RETRIEVED = "seshops_runbooks_retrieved"
    RUNBOOK_SEARCH_FAILED = "seshops_runbook_search_failed"
    NO_RUNBOOKS = "seshops_no_runbooks"

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_READY = "seshops_database_ready"
    DATABASE_INIT_FAILED = "seshops_database_init_failed"
    DB_HEALTH_FAILED = "seshops_db_health_failed"

    # ── Infrastructure ───────────────────────────────────────────────
    LOGGING_READY = "seshops_logging_ready"
    ENGINE_READY = "seshops_engine_ready"
    VALIDATION_ERROR = "seshops_validation_error"
    FATAL_INSECURE_JWT = "seshops_fatal_insecure_jwt_secret"
    CORS_WILDCARD = "seshops_cors_wildcard_in_production"
