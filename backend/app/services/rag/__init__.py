"""
RAG — Retrieval-Augmented Generation for Fiscalogix.

Layer 2 of the Intelligence Stack. Grounds every LLM call in real,
tenant-specific data from the database instead of relying on generic
model knowledge.

Public API:
    from app.services.rag import get_retriever
    retriever = get_retriever()
    context = retriever.get_context("EU route risk", tenant_id="default_tenant")
"""

from app.services.rag.retriever import RAGRetriever

_instance: RAGRetriever | None = None


def get_retriever() -> RAGRetriever:
    """Singleton accessor — embedder loads once at startup."""
    global _instance
    if _instance is None:
        _instance = RAGRetriever()
    return _instance
