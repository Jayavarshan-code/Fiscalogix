"""
RAG Retriever — query interface for the knowledge base.

Given a natural-language query and a tenant_id, returns the top-K
most relevant text chunks from the knowledge_chunks table.

Two retrieval strategies:
  1. Vector similarity (pgvector) — used when embedder is available
  2. Keyword fallback (ILIKE) — used when sentence-transformers not installed

The context string returned is ready to be injected directly into an
LLM prompt as grounding evidence.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    Retrieves relevant knowledge chunks for a query.
    Injected into LLM calls to ground responses in real tenant data.

    Usage:
        retriever = RAGRetriever()
        context = retriever.get_context(
            query="EU route risk after Suez congestion",
            tenant_id="default_tenant",
            top_k=5,
            source_types=["carrier_performance", "route_performance"]
        )
        # context is a formatted string ready for LLM prompt injection
    """

    def __init__(self):
        from app.services.rag.embedder import get_embedder
        self._embedder = get_embedder()

    def get_context(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        source_types: Optional[List[str]] = None,
    ) -> str:
        """
        Main retrieval method. Returns a formatted context string.
        Returns empty string (not an error) if no relevant chunks found.
        """
        chunks = self._retrieve(query, tenant_id, top_k, source_types)
        if not chunks:
            return ""

        lines = ["[RETRIEVED CONTEXT — use these facts to ground your response]"]
        for i, (content, source_type, score) in enumerate(chunks, 1):
            lines.append(f"\n[{i}] Source: {source_type} (relevance: {score:.2f})")
            lines.append(content)
        lines.append("\n[END CONTEXT]")
        return "\n".join(lines)

    def _retrieve(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
        source_types: Optional[List[str]],
    ) -> List[tuple]:
        """
        Returns list of (content, source_type, similarity_score) tuples.
        Tries vector search first, falls back to keyword search.
        """
        if self._embedder.ready:
            results = self._vector_search(query, tenant_id, top_k, source_types)
            if results:
                return results
        # Fallback: keyword match
        return self._keyword_search(query, tenant_id, top_k, source_types)

    def _vector_search(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
        source_types: Optional[List[str]],
    ) -> List[tuple]:
        """
        Cosine similarity search over stored embeddings.
        Uses Python-side cosine calculation (works without pgvector extension).
        If the table is small enough (<10k rows per tenant) this is fast enough.
        For larger corpora, migrate to pgvector native SQL (see comment below).
        """
        try:
            from app.Db.connections import SessionLocal
            from setup_db import KnowledgeChunk

            query_vec = self._embedder.embed(query)
            if query_vec is None:
                return []

            db = SessionLocal()
            try:
                q = db.query(KnowledgeChunk).filter(
                    KnowledgeChunk.tenant_id == tenant_id,
                    KnowledgeChunk.embedding_json.isnot(None),
                )
                if source_types:
                    q = q.filter(KnowledgeChunk.source_type.in_(source_types))

                chunks = q.all()
                if not chunks:
                    return []

                scored = []
                for chunk in chunks:
                    try:
                        stored_vec = self._embedder.from_json(chunk.embedding_json)
                        sim = self._embedder.cosine_similarity(query_vec, stored_vec)
                        scored.append((chunk.content, chunk.source_type, sim))
                    except Exception:
                        continue

                scored.sort(key=lambda x: x[2], reverse=True)
                return scored[:top_k]

            finally:
                db.close()

        except Exception as e:
            logger.warning(f"RAGRetriever._vector_search: {e}")
            return []

    def _keyword_search(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
        source_types: Optional[List[str]],
    ) -> List[tuple]:
        """
        Simple ILIKE keyword fallback for when embedder is unavailable.
        Scores by count of query words found in the chunk.
        """
        try:
            from app.Db.connections import SessionLocal
            from setup_db import KnowledgeChunk
            from sqlalchemy import or_

            words = [w for w in query.lower().split() if len(w) > 3]
            if not words:
                return []

            db = SessionLocal()
            try:
                q = db.query(KnowledgeChunk).filter(
                    KnowledgeChunk.tenant_id == tenant_id,
                    or_(*[
                        KnowledgeChunk.content.ilike(f"%{word}%")
                        for word in words[:5]  # cap at 5 words for performance
                    ]),
                )
                if source_types:
                    q = q.filter(KnowledgeChunk.source_type.in_(source_types))

                chunks = q.limit(top_k * 3).all()

                # Score by word hit count
                scored = []
                for chunk in chunks:
                    content_lower = chunk.content.lower()
                    hits = sum(1 for w in words if w in content_lower)
                    score = hits / max(len(words), 1)
                    scored.append((chunk.content, chunk.source_type, score))

                scored.sort(key=lambda x: x[2], reverse=True)
                return scored[:top_k]

            finally:
                db.close()

        except Exception as e:
            logger.warning(f"RAGRetriever._keyword_search: {e}")
            return []
