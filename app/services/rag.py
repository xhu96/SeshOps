"""RAG service for SeshOps runbook retrieval.

Manages document ingestion, embedding, and vector similarity search against
IT operations runbooks.  In production, the backing store is pgvector; in
local development the service falls back to an in-memory store so that Docker
is not required for basic testing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore, VectorStore
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logging import logger


class RAGService:
    """Embeds and retrieves IT operations runbooks for the SeshOps triage pipeline."""

    def __init__(self) -> None:
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self._vector_store: Optional[VectorStore] = None

    def get_vector_store(self) -> VectorStore:
        """Lazily initialise the vector store (in-memory for local dev)."""
        if self._vector_store is None:
            logger.info(
                "seshops_vectorstore_init",
                backend="in_memory",
                note="Production deployments should use pgvector",
            )
            self._vector_store = InMemoryVectorStore(self.embeddings)
        return self._vector_store

    async def ingest_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Embed and store a batch of runbook documents.

        Args:
            documents: List of dicts with ``content`` and optional ``metadata``.
        """
        store = self.get_vector_store()

        lc_docs = []
        for doc in documents:
            meta = doc.get("metadata", {})
            meta.setdefault("id", "unknown")
            meta.setdefault("title", "Untitled")
            meta.setdefault("source_type", "runbook")
            meta.setdefault("owner", "unknown-team")

            lc_docs.append(
                Document(page_content=doc["content"], metadata=meta)
            )

        await store.aadd_documents(lc_docs)
        logger.info("seshops_runbooks_ingested", count=len(lc_docs))

    async def search_runbooks(self, query: str, limit: int = 3) -> str:
        """Search for runbooks relevant to the given incident query.

        Args:
            query: Free-text combining service name and symptoms.
            limit: Maximum number of chunks to return.

        Returns:
            Concatenated markdown string of matched runbook excerpts.
        """
        store = self.get_vector_store()
        try:
            results = await store.asimilarity_search(query, k=limit)

            if not results:
                logger.warning("seshops_no_runbooks", query=query)
                return "No relevant runbooks found."

            formatted = []
            for i, doc in enumerate(results):
                title = doc.metadata.get("title", f"Runbook {i + 1}")
                owner = doc.metadata.get("owner", "Unknown Team")
                formatted.append(
                    f"### Source: {title} (Owner: {owner})\n{doc.page_content}"
                )

            logger.info("seshops_runbooks_retrieved", query=query, count=len(results))
            return "\n\n".join(formatted)

        except Exception as exc:
            logger.error("seshops_runbook_search_failed", query=query, error=str(exc))
            return "Error retrieving runbooks."


rag_service = RAGService()
