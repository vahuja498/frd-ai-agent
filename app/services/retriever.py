"""
app/services/retriever.py
Retrieves relevant past FRD chunks from the vector store
given the current project's input documents.
"""
from typing import List

from app.services.vector_store import VectorStoreService
from app.models.schemas import RetrievedFRD


class RetrieverService:
    """
    Builds a search query from the project inputs and
    fetches the most relevant historical FRD passages.
    """

    def __init__(self, vector_store: VectorStoreService) -> None:
        self._store = vector_store

    def retrieve(
        self,
        transcript: str,
        mom: str,
        sow: str,
        top_k: int = 3,
    ) -> List[RetrievedFRD]:
        """
        Build a composite search query from all three inputs
        and return the top-K matching FRD chunks.
        """
        if self._store.total_chunks == 0:
            print("[Retriever] Vector store is empty — no RAG context available")
            return []

        query = self._build_query(transcript, mom, sow)
        raw_hits = self._store.search(query, top_k=top_k)

        return [
            RetrievedFRD(
                text=hit["text"],
                source=hit["source"],
                similarity_score=hit["similarity_score"],
            )
            for hit in raw_hits
        ]

    def format_context(self, retrieved: List[RetrievedFRD]) -> str:
        """
        Format retrieved FRD chunks into a single context string
        suitable for inclusion in an LLM prompt.
        """
        if not retrieved:
            return "No historical FRDs available for reference."

        parts = ["=== RETRIEVED HISTORICAL FRD CONTEXT ==="]
        for i, item in enumerate(retrieved, 1):
            parts.append(
                f"\n[Reference {i} — from: {item.source} "
                f"(similarity: {item.similarity_score:.2f})]\n{item.text}"
            )
        return "\n".join(parts)

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_query(self, transcript: str, mom: str, sow: str) -> str:
        """
        Combine the most informative parts of all inputs into a
        single compact search query (max ~600 chars).
        """
        parts = [
            transcript[:200].strip(),
            mom[:200].strip(),
            sow[:200].strip(),
        ]
        return " ".join(p for p in parts if p)[:600]
