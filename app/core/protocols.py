"""Protocol interfaces for SeshOps services.

Defines the contracts that LLM and RAG services must satisfy.  LangGraph
nodes depend on these protocols rather than concrete implementations,
enabling dependency injection and clean test mocking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable

from langchain_core.messages import BaseMessage


@runtime_checkable
class LLMServiceProtocol(Protocol):
    """Contract for an LLM service capable of chat-completion calls."""

    async def call(self, messages: list[BaseMessage]) -> Any:
        """Send messages to an LLM and return the response."""
        ...

    async def call_with_fallback(self, messages: list[BaseMessage]) -> Any:
        """Call with automatic model fallback on failure."""
        ...


@runtime_checkable
class RAGServiceProtocol(Protocol):
    """Contract for a RAG service capable of runbook retrieval."""

    async def search_runbooks(self, query: str, limit: int = 3) -> str:
        """Search for runbooks relevant to the given query."""
        ...

    async def ingest_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Embed and store a batch of documents."""
        ...
