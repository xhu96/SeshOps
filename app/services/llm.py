"""LLM service for the SeshOps incident triage pipeline.

Manages all LLM interactions with per-model retry, exponential back-off,
and circular fallback through every registered model.  When one provider
hits a rate limit or timeout, the service automatically rotates to the
next model in the ``LLMRegistry`` until all have been exhausted.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from openai import APIError, APITimeoutError, OpenAIError, RateLimitError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Environment, settings
from app.core.logging import logger


# ── Provider helper ──────────────────────────────────────────────────────────

def _get_chat_model(model_name: str, **kwargs: Any) -> BaseChatModel:
    """Instantiate a ChatOpenAI for either OpenAI or OpenRouter."""
    if settings.OPENROUTER_API_KEY:
        return ChatOpenAI(
            model=model_name,
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            **kwargs,
        )
    return ChatOpenAI(
        model=model_name,
        api_key=settings.OPENAI_API_KEY,
        **kwargs,
    )


# ── Model registry ──────────────────────────────────────────────────────────

class LLMRegistry:
    """Catalogue of pre-initialised LLM instances available to SeshOps.

    Models are ordered by preference; the triage pipeline defaults to
    ``settings.DEFAULT_LLM_MODEL`` and falls back circularly through the
    remainder if calls fail.
    """

    LLMS: List[Dict[str, Any]] = [
        {
            "name": "gpt-5-mini",
            "llm": _get_chat_model(
                "gpt-5-mini",
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "low"},
            ),
        },
        {
            "name": "gpt-5",
            "llm": _get_chat_model(
                "gpt-5",
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "medium"},
            ),
        },
        {
            "name": "gpt-5-nano",
            "llm": _get_chat_model(
                "gpt-5-nano",
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "minimal"},
            ),
        },
        {
            "name": "gpt-4o",
            "llm": _get_chat_model(
                "gpt-4o",
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
                top_p=0.95 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.8,
                presence_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
                frequency_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
            ),
        },
        {
            "name": "gpt-4o-mini",
            "llm": _get_chat_model(
                "gpt-4o-mini",
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
                top_p=0.9 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.8,
            ),
        },
    ]

    @classmethod
    def get(cls, model_name: str, **kwargs: Any) -> BaseChatModel:
        """Retrieve a model by name, optionally overriding its defaults."""
        entry = next((e for e in cls.LLMS if e["name"] == model_name), None)

        if not entry:
            logger.info("seshops_llm_dynamic_create", model_name=model_name)
            return _get_chat_model(model_name, **kwargs)

        if kwargs:
            logger.debug("seshops_llm_custom_args", model_name=model_name, keys=list(kwargs))
            return _get_chat_model(model_name, **kwargs)

        return entry["llm"]

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Return registered model names in preference order."""
        return [e["name"] for e in cls.LLMS]

    @classmethod
    def get_model_at_index(cls, index: int) -> Dict[str, Any]:
        """Return the registry entry at *index* (wraps to first on overflow)."""
        if 0 <= index < len(cls.LLMS):
            return cls.LLMS[index]
        return cls.LLMS[0]


# ── Service with circular fallback ───────────────────────────────────────────

class LLMService:
    """Manages LLM calls for the SeshOps incident triage pipeline.

    Provides per-model retry with exponential back-off and automatic
    circular fallback through every model in the ``LLMRegistry``.
    """

    # ── Circuit breaker state ────────────────────────────────────────

    CIRCUIT_OPEN_DURATION: float = 60.0  # seconds before auto-reset

    def __init__(self) -> None:
        """Initialize the LLM service with circuit breaker and fallback state."""
        self._llm: Optional[BaseChatModel] = None
        self._current_model_index: int = 0
        self._circuit_open: bool = False
        self._circuit_opened_at: float = 0.0
        self._consecutive_full_failures: int = 0

        all_names = LLMRegistry.get_all_names()
        try:
            self._current_model_index = all_names.index(settings.DEFAULT_LLM_MODEL)
            self._llm = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
            logger.info(
                "seshops_llm_service_ready",
                default_model=settings.DEFAULT_LLM_MODEL,
                model_index=self._current_model_index,
                total_models=len(all_names),
            )
        except (ValueError, Exception) as exc:
            self._current_model_index = 0
            self._llm = LLMRegistry.LLMS[0]["llm"]
            logger.warning(
                "seshops_llm_default_fallback",
                requested=settings.DEFAULT_LLM_MODEL,
                using=all_names[0] if all_names else "none",
                error=str(exc),
            )

    def _check_circuit(self) -> None:
        """Fail-fast if the circuit breaker is open.

        Auto-resets after ``CIRCUIT_OPEN_DURATION`` seconds.
        """
        if not self._circuit_open:
            return
        elapsed = time.monotonic() - self._circuit_opened_at
        if elapsed >= self.CIRCUIT_OPEN_DURATION:
            logger.info(
                "seshops_llm_circuit_reset",
                open_seconds=round(elapsed, 1),
            )
            self._circuit_open = False
            self._consecutive_full_failures = 0
            return
        raise RuntimeError(
            f"SeshOps LLM circuit breaker is open (open for "
            f"{elapsed:.0f}s / {self.CIRCUIT_OPEN_DURATION:.0f}s). "
            f"Failing fast to protect upstream."
        )

    def _get_next_model_index(self) -> int:
        """Advance the index circularly through the registry."""
        return (self._current_model_index + 1) % len(LLMRegistry.LLMS)

    def _switch_to_next_model(self) -> bool:
        """Rotate to the next model. Returns ``True`` on success."""
        try:
            idx = self._get_next_model_index()
            entry = LLMRegistry.get_model_at_index(idx)
            logger.warning(
                "seshops_llm_switching",
                from_index=self._current_model_index,
                to_model=entry["name"],
            )
            self._current_model_index = idx
            self._llm = entry["llm"]
            return True
        except Exception as exc:
            logger.error("seshops_llm_switch_failed", error=str(exc))
            return False

    @retry(
        stop=stop_after_attempt(settings.MAX_LLM_CALL_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _call_llm_with_retry(self, messages: List[BaseMessage]) -> BaseMessage:
        """Invoke the active model with automatic retry on transient errors."""
        if not self._llm:
            raise RuntimeError("SeshOps LLM service is not initialised")

        try:
            response = await self._llm.ainvoke(messages)
            logger.debug("seshops_llm_call_ok", message_count=len(messages))
            return response
        except (RateLimitError, APITimeoutError, APIError):
            raise
        except OpenAIError as exc:
            logger.error("seshops_llm_call_failed", error_type=type(exc).__name__, error=str(exc))
            raise

    async def call(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
        **model_kwargs: Any,
    ) -> BaseMessage:
        """Execute an LLM call with circular fallback across all registered models.

        Args:
            messages: The prompt messages to send.
            model_name: Pin a specific model instead of using the current default.
            **model_kwargs: Override model construction parameters.

        Returns:
            The assistant response message.

        Raises:
            RuntimeError: If every model in the registry fails after retries.
        """
        # ── Circuit breaker check ──────────────────────────────────
        self._check_circuit()

        if model_name:
            try:
                self._llm = LLMRegistry.get(model_name, **model_kwargs)
                all_names = LLMRegistry.get_all_names()
                try:
                    self._current_model_index = all_names.index(model_name)
                except ValueError:
                    pass
                logger.info("seshops_llm_model_pinned", model_name=model_name)
            except ValueError as exc:
                logger.error("seshops_llm_model_not_found", model_name=model_name, error=str(exc))
                raise

        total = len(LLMRegistry.LLMS)
        tried = 0
        last_error: Optional[Exception] = None

        while tried < total:
            try:
                result = await self._call_llm_with_retry(messages)
                # Success — reset circuit state
                self._consecutive_full_failures = 0
                return result
            except OpenAIError as exc:
                last_error = exc
                tried += 1
                current_name = LLMRegistry.LLMS[self._current_model_index]["name"]
                logger.error(
                    "seshops_llm_exhausted_retries",
                    model=current_name,
                    tried=tried,
                    total=total,
                    error=str(exc),
                )
                if tried >= total:
                    break
                if not self._switch_to_next_model():
                    break

        # All models exhausted — trip or increment circuit breaker
        self._consecutive_full_failures += 1
        if self._consecutive_full_failures >= 2:
            self._circuit_open = True
            self._circuit_opened_at = time.monotonic()
            logger.critical(
                "seshops_llm_circuit_opened",
                consecutive_failures=self._consecutive_full_failures,
                cooldown_seconds=self.CIRCUIT_OPEN_DURATION,
            )

        raise RuntimeError(
            f"SeshOps triage failed: exhausted {tried} models. "
            f"Last error: {last_error}"
        )

    def get_llm(self) -> Optional[BaseChatModel]:
        """Return the currently active model instance."""
        return self._llm

    def bind_tools(self, tools: List[Any]) -> "LLMService":
        """Bind tool schemas to the active model for structured output."""
        if self._llm:
            self._llm = self._llm.bind_tools(tools)
            logger.debug("seshops_tools_bound", tool_count=len(tools))
        return self


llm_service = LLMService()
