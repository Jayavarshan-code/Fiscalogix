"""
RAG Ingestion Pipeline — populates the knowledge_chunks table.

Reads from your existing operational tables (CarrierPerformance,
DWShipmentFact, DecisionLog, etc.) and converts each row into a
plain-English text chunk that gets embedded and stored for retrieval.

Run manually:     python -m app.services.rag.ingestion
Run via Celery:   task name "refresh_rag_knowledge_base"

Design:
- Each source type has its own _ingest_* method that knows how to
  turn a DB row into a human-readable sentence the LLM can use.
- Existing chunks are replaced (delete-then-insert per source_id)
  so re-running is always idempotent.
- Batch embedding: all texts for a source type are embedded in one
  forward pass (much faster than per-row embedding).
"""

import logging
import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RAGIngestionPipeline:
    """
    Converts operational DB rows into embedded knowledge chunks.

    Typical call sequence (Celery task):
        pipeline = RAGIngestionPipeline()
        result = pipeline.run_full(tenant_id="default_tenant")
    """

    def __init__(self):
        from app.services.rag.embedder import get_embedder
        self._embedder = get_embedder()

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    def run_full(self, tenant_id: str = "default_tenant") -> Dict[str, int]:
        """
        Full refresh of the knowledge base for a tenant.
        Returns dict of {source_type: rows_ingested}.
        """
        logger.info(f"RAG ingestion: starting full refresh for tenant={tenant_id}")
        results = {}

        results["carrier_performance"] = self._ingest_carrier_performance(tenant_id)
        results["shipment_history"]    = self._ingest_shipment_history(tenant_id)
        results["decision_outcomes"]   = self._ingest_decision_outcomes(tenant_id)
        results["route_performance"]   = self._ingest_route_performance(tenant_id)
        results["supplier_profiles"]   = self._ingest_supplier_profiles(tenant_id)

        total = sum(results.values())
        logger.info(f"RAG ingestion: complete — {total} chunks embedded for tenant={tenant_id}")
        return results

    def ingest_document(
        self,
        extracted_data: Dict[str, Any],
        tenant_id: str,
        source_type: str = "sla_contract",
        source_id: str = None,
    ) -> bool:
        """
        Called by DocumentIntelligenceService after extracting a contract/permit.
        Embeds the extracted fields as a knowledge chunk immediately.
        """
        text = self._format_document_chunk(extracted_data, source_type)
        if not text:
            return False
        return self._upsert_chunk(
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id or f"doc_{datetime.datetime.utcnow().timestamp():.0f}",
            content=text,
        )

    def ingest_sla_contract(
        self,
        raw_text: str,
        tenant_id: str,
        contract_id: str,
        supplier_id: str = "unknown",
    ) -> int:
        """
        Parse a raw contract PDF text with SLAContractExtractor and embed each
        extracted clause as its own knowledge chunk.

        Embedding individual clauses (not the full contract blob) means the RAG
        retriever returns precise clause-level context — e.g. the exact OTIF
        penalty rate — rather than a 50-page wall of text.

        Returns: number of clause chunks embedded.
        """
        from app.ml.sla_extractor import SLAContractExtractor

        extraction = SLAContractExtractor.extract(raw_text)
        clauses    = extraction.get("clauses", [])

        if not clauses:
            # Embed a summary chunk so the contract is at least findable by keyword
            summary = (
                f"Contract {contract_id} (supplier: {supplier_id}): "
                f"no structured penalty clauses detected by regex engine. "
                f"Preview: {raw_text[:300]}"
            )
            self._upsert_chunk(tenant_id, "sla_contract", f"contract_{contract_id}_summary", summary)
            return 0

        texts, ids = [], []
        for idx, clause in enumerate(clauses):
            severity = clause.get("bottleneck_severity", "NONE")
            value    = clause.get("value")
            unit     = clause.get("unit", "")
            val_str  = f" (value: {value} {unit})" if value is not None else ""

            text = (
                f"Contract {contract_id} — {supplier_id} | "
                f"Clause type: {clause['clause_type']}{val_str}. "
                f"Severity: {severity}. "
                f"Context: {clause.get('section_context', 'N/A')}. "
                f"Text: {clause.get('raw_text', '')[:200]}. "
                f"Risk: {clause.get('bottleneck_reason', '')}."
            )
            texts.append(text)
            ids.append(f"contract_{contract_id}_clause_{idx}")

        embedded = self._batch_upsert(tenant_id, "sla_contract", texts, ids)
        logger.info(
            f"RAG: ingested {embedded}/{len(clauses)} clauses for contract={contract_id} "
            f"supplier={supplier_id} tenant={tenant_id} "
            f"(critical={extraction['critical_count']}, high={extraction['high_risk_count']})"
        )
        return embedded

    # ─────────────────────────────────────────────────────────────────────────
    # SOURCE-SPECIFIC INGESTION METHODS
    # ─────────────────────────────────────────────────────────────────────────

    def _ingest_carrier_performance(self, tenant_id: str) -> int:
        """
        Converts CarrierPerformance rows into sentences like:
        "DHL Express on route CN-EU achieved 97.2% on-time rate over
         the 90-day window ending 2026-03-01. Average delay: 0.8 days."
        """
        try:
            from app.Db.connections import SessionLocal
            from setup_db import CarrierPerformance

            db = SessionLocal()
            try:
                rows = db.query(CarrierPerformance).filter(
                    CarrierPerformance.measured_to >= (
                        datetime.datetime.utcnow() - datetime.timedelta(days=180)
                    )
                ).all()

                texts, ids = [], []
                for r in rows:
                    text = (
                        f"{r.carrier_name} on route {r.route or 'all routes'} achieved "
                        f"{r.on_time_rate * 100:.1f}% on-time delivery rate over the "
                        f"measurement window ending {r.measured_to.strftime('%Y-%m-%d') if r.measured_to else 'recently'}. "
                    )
                    if hasattr(r, 'avg_delay_days') and r.avg_delay_days is not None:
                        text += f"Average delay when late: {r.avg_delay_days:.1f} days."
                    texts.append(text)
                    ids.append(f"carrier_{r.id}")

                return self._batch_upsert(tenant_id, "carrier_performance", texts, ids)

            finally:
                db.close()

        except Exception as e:
            logger.warning(f"RAG: carrier_performance ingestion failed — {e}")
            return 0

    def _ingest_shipment_history(self, tenant_id: str) -> int:
        """
        Summarizes recent DWShipmentFact rows into route-level performance chunks.
        Groups by route and computes averages — avoids embedding 50k individual rows.
        """
        try:
            from app.Db.connections import engine
            import pandas as pd

            query = """
                SELECT
                    origin_node,
                    destination_node,
                    COUNT(*)                      AS shipment_count,
                    AVG(delay_days_calculated)    AS avg_delay,
                    AVG(margin_usd)               AS avg_margin,
                    AVG(ml_confidence_score)      AS avg_risk,
                    SUM(CASE WHEN ml_risk_detected THEN 1 ELSE 0 END) AS risk_events
                FROM dw_shipment_facts
                WHERE tenant_id = :tenant_id
                  AND created_at >= NOW() - INTERVAL '90 days'
                GROUP BY origin_node, destination_node
                HAVING COUNT(*) >= 3
                LIMIT 200
            """
            df = pd.read_sql(query, engine, params={"tenant_id": tenant_id})

            texts, ids = [], []
            for _, row in df.iterrows():
                origin = row["origin_node"] or "UNKNOWN"
                dest   = row["destination_node"] or "UNKNOWN"
                text = (
                    f"Route {origin} → {dest}: {int(row['shipment_count'])} shipments in last 90 days. "
                    f"Average delay: {row['avg_delay']:.1f} days. "
                    f"Average margin: ${row['avg_margin']:,.0f}. "
                    f"Average risk score: {row['avg_risk']:.2f}. "
                    f"Risk events detected: {int(row['risk_events'])}."
                )
                texts.append(text)
                ids.append(f"route_{origin}_{dest}".replace(" ", "_").lower())

            return self._batch_upsert(tenant_id, "shipment_history", texts, ids)

        except Exception as e:
            logger.warning(f"RAG: shipment_history ingestion failed — {e}")
            return 0

    def _ingest_decision_outcomes(self, tenant_id: str) -> int:
        """
        Converts DecisionLog rows into outcome sentences:
        "Reroute decision for shipment SH-1203 (route EU→US, confidence 0.87)
         selected action: reroute_via_cape. Predicted EFI: $42,300."
        """
        try:
            from app.Db.connections import SessionLocal
            from setup_db import DecisionLog

            db = SessionLocal()
            try:
                # Most recent 500 decisions — enough context, not too large
                rows = (
                    db.query(DecisionLog)
                    .filter(DecisionLog.tenant_id == tenant_id)
                    .order_by(DecisionLog.id.desc())
                    .limit(500)
                    .all()
                )

                texts, ids = [], []
                for r in rows:
                    text = (
                        f"Decision for shipment {r.shipment_id or 'N/A'}: "
                        f"action selected was '{r.route_selected or 'unknown'}' "
                        f"with confidence {r.confidence_score:.2f if r.confidence_score else 'N/A'}. "
                        f"Risk posture: {r.risk_posture or 'N/A'}. "
                        f"Predicted financial impact: ${r.predicted_efi:,.0f}."
                        if r.predicted_efi else
                        f"Decision for shipment {r.shipment_id or 'N/A'}: "
                        f"action '{r.route_selected or 'unknown'}' selected."
                    )
                    texts.append(text)
                    ids.append(f"decision_{r.decision_id}")

                return self._batch_upsert(tenant_id, "decision_outcomes", texts, ids)

            finally:
                db.close()

        except Exception as e:
            logger.warning(f"RAG: decision_outcomes ingestion failed — {e}")
            return 0

    def _ingest_route_performance(self, tenant_id: str) -> int:
        """
        Creates route-level performance summaries from ReVM snapshot data
        if the revm_snapshots table exists.
        """
        try:
            from app.Db.connections import engine
            import pandas as pd

            query = """
                SELECT
                    origin_node,
                    destination_node,
                    AVG(revm)          AS avg_revm,
                    STDDEV(revm)       AS revm_stddev,
                    AVG(risk_score)    AS avg_risk,
                    COUNT(*)           AS sample_count
                FROM revm_snapshots
                WHERE tenant_id = :tenant_id
                  AND snapshotted_at >= NOW() - INTERVAL '90 days'
                GROUP BY origin_node, destination_node
                HAVING COUNT(*) >= 5
                LIMIT 100
            """
            df = pd.read_sql(query, engine, params={"tenant_id": tenant_id})

            texts, ids = [], []
            for _, row in df.iterrows():
                origin = row.get("origin_node") or "N/A"
                dest   = row.get("destination_node") or "N/A"
                text = (
                    f"ReVM performance for route {origin} → {dest} "
                    f"(last 90 days, {int(row['sample_count'])} records): "
                    f"average ReVM ${row['avg_revm']:,.0f}, "
                    f"standard deviation ${row['revm_stddev']:,.0f}, "
                    f"average risk score {row['avg_risk']:.3f}."
                )
                texts.append(text)
                ids.append(f"revm_{origin}_{dest}".replace(" ", "_").lower())

            return self._batch_upsert(tenant_id, "route_performance", texts, ids)

        except Exception as e:
            logger.warning(f"RAG: route_performance ingestion failed — {e}")
            return 0

    def _ingest_supplier_profiles(self, tenant_id: str) -> int:
        """
        Converts Supplier rows into readable profiles.
        """
        try:
            from app.Db.connections import SessionLocal
            from setup_db import Supplier

            db = SessionLocal()
            try:
                rows = db.query(Supplier).filter(Supplier.tenant_id == tenant_id).all()

                texts, ids = [], []
                for r in rows:
                    text = (
                        f"Supplier '{r.supplier_name}' (country: {r.country_code or 'N/A'}): "
                        f"financial health score {r.financial_health_score:.2f}, "
                        f"on-time delivery rate {r.on_time_delivery_rate * 100:.1f}%, "
                        f"geopolitical risk index {r.geopolitical_risk_index:.2f}. "
                    )
                    if r.contract_expiry_date:
                        text += f"Contract expires {r.contract_expiry_date.strftime('%Y-%m-%d')}."
                    texts.append(text)
                    ids.append(f"supplier_{r.supplier_id}")

                return self._batch_upsert(tenant_id, "supplier_profiles", texts, ids)

            finally:
                db.close()

        except Exception as e:
            logger.warning(f"RAG: supplier_profiles ingestion failed — {e}")
            return 0

    # ─────────────────────────────────────────────────────────────────────────
    # SHARED UTILITIES
    # ─────────────────────────────────────────────────────────────────────────

    def _batch_upsert(
        self,
        tenant_id: str,
        source_type: str,
        texts: List[str],
        source_ids: List[str],
    ) -> int:
        """
        Embeds texts in one batch, then upserts into knowledge_chunks.
        Returns count of successfully stored chunks.
        """
        if not texts:
            return 0

        embeddings = self._embedder.embed_batch(texts)

        count = 0
        for text, source_id, embedding in zip(texts, source_ids, embeddings):
            ok = self._upsert_chunk(
                tenant_id=tenant_id,
                source_type=source_type,
                source_id=source_id,
                content=text,
                embedding=embedding,
            )
            if ok:
                count += 1

        logger.info(f"RAG: upserted {count}/{len(texts)} chunks for source_type={source_type}")
        return count

    def _upsert_chunk(
        self,
        tenant_id: str,
        source_type: str,
        source_id: str,
        content: str,
        embedding: List[float] = None,
    ) -> bool:
        """
        Delete-then-insert for a single chunk (idempotent on source_id).
        """
        try:
            from app.Db.connections import SessionLocal
            from setup_db import KnowledgeChunk

            embedding_json = (
                self._embedder.to_json(embedding) if embedding else None
            )

            db = SessionLocal()
            try:
                # Delete stale version if it exists
                db.query(KnowledgeChunk).filter(
                    KnowledgeChunk.tenant_id == tenant_id,
                    KnowledgeChunk.source_id == source_id,
                    KnowledgeChunk.source_type == source_type,
                ).delete()

                db.add(KnowledgeChunk(
                    tenant_id=tenant_id,
                    source_type=source_type,
                    source_id=source_id,
                    content=content,
                    embedding_json=embedding_json,
                ))
                db.commit()
                return True

            except Exception as e:
                db.rollback()
                logger.error(f"RAG._upsert_chunk: DB write failed — {e}")
                return False
            finally:
                db.close()

        except Exception as e:
            logger.error(f"RAG._upsert_chunk: {e}")
            return False

    def _format_document_chunk(
        self, extracted: Dict[str, Any], source_type: str
    ) -> str:
        """Formats extracted document fields into a readable sentence."""
        if source_type == "sla_contract":
            parts = []
            if extracted.get("penalty_rate_per_day_pct"):
                parts.append(
                    f"SLA penalty rate: {extracted['penalty_rate_per_day_pct'] * 100:.1f}%/day"
                )
            if extracted.get("penalty_cap_pct"):
                parts.append(f"capped at {extracted['penalty_cap_pct'] * 100:.0f}% of order value")
            if extracted.get("payment_terms_days"):
                parts.append(f"payment terms: Net-{extracted['payment_terms_days']}")
            if extracted.get("incoterms"):
                parts.append(f"Incoterms: {extracted['incoterms']}")
            if extracted.get("force_majeure_clause") is not None:
                parts.append(
                    f"force majeure clause: {'present' if extracted['force_majeure_clause'] else 'absent'}"
                )
            return "Contract terms — " + "; ".join(parts) + "." if parts else ""

        if source_type == "permit":
            return (
                f"Permit {extracted.get('permit_number', 'N/A')} issued by "
                f"{extracted.get('issuing_authority', 'N/A')}, "
                f"expires {extracted.get('expiry_date', 'N/A')}. "
                f"Scope: {', '.join(extracted.get('permit_scope', []))}."
            )

        # Generic: dump key-value pairs
        return " | ".join(f"{k}: {v}" for k, v in extracted.items() if v is not None)


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    tenant = sys.argv[1] if len(sys.argv) > 1 else "default_tenant"
    pipeline = RAGIngestionPipeline()
    result = pipeline.run_full(tenant_id=tenant)
    for source, count in result.items():
        print(f"  {source}: {count} chunks")
