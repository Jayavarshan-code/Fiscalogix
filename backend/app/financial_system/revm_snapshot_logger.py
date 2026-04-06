import logging
import datetime
from setup_db import RevmSnapshot

logger = logging.getLogger(__name__)


class RevmSnapshotLogger:
    """
    Persists ReVM engine output after every orchestrator run.

    WHY THIS EXISTS:
    The orchestrator computed ReVM on every request but never stored the results.
    This made it impossible to:
    1. Show historical ReVM trend charts (the #1 investor demo feature).
    2. Detect financial performance degradation over time.
    3. Audit which AI decision point led to a margin change.

    HOW IT WORKS:
    Called from orchestrator.py after Phase 2 (synthesis loop).
    Uses bulk_save_objects for performance — does NOT commit one row at a time.
    """

    def save_batch(self, enriched_records: list, tenant_id: str = "default_tenant"):
        """
        Bulk-writes ReVM snapshots for every processed shipment row.
        Creates its own DB session — orchestrator does not need to pass one.

        Args:
            enriched_records: The list of enriched row dicts from orchestrator Phase 2.
            tenant_id:        The tenant namespace for all written records.
        """
        from app.Db.connections import SessionLocal

        if not enriched_records:
            return

        db = SessionLocal()
        try:
            snapshots = []
            for record in enriched_records:
                decision = record.get("decision", {})
                snapshots.append(RevmSnapshot(
                    tenant_id        = record.get("tenant_id", tenant_id),
                    shipment_id      = record.get("shipment_id"),
                    run_timestamp    = datetime.datetime.utcnow(),
                    # Core ReVM components
                    revm             = record.get("revm"),
                    contribution_profit = record.get("contribution_profit"),
                    risk_penalty     = record.get("risk_penalty"),
                    time_cost        = record.get("time_cost"),
                    future_cost      = record.get("future_cost"),
                    fx_cost          = record.get("fx_cost"),
                    sla_penalty      = record.get("sla_penalty"),
                    # Intelligence outputs
                    risk_score       = record.get("risk_score"),
                    confidence_score = record.get("risk_confidence"),
                    predicted_delay  = record.get("predicted_delay"),
                    decision_action  = decision.get("action"),
                    decision_tier    = decision.get("tier"),
                ))

            db.bulk_save_objects(snapshots)
            db.commit()
            logger.info(
                f"RevmSnapshotLogger: saved {len(snapshots)} snapshots "
                f"for tenant={tenant_id}"
            )
        except Exception as e:
            db.rollback()
            logger.error(
                f"RevmSnapshotLogger.save_batch failed — {type(e).__name__}: {e}",
                exc_info=True
            )
        finally:
            db.close()

    def get_trend(self, tenant_id: str, shipment_id: int = None, days: int = 30):
        """
        Retrieves historical ReVM trend for dashboard charting.
        Returns list of {run_timestamp, revm, decision_action} dicts.

        Args:
            tenant_id:   Filter by tenant.
            shipment_id: Optional — filter to one shipment's history.
            days:        How many days back to look (default: 30).
        """
        from app.Db.connections import SessionLocal

        db = SessionLocal()
        try:
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            query = db.query(RevmSnapshot).filter(
                RevmSnapshot.tenant_id == tenant_id,
                RevmSnapshot.run_timestamp >= cutoff,
            )
            if shipment_id is not None:
                query = query.filter(RevmSnapshot.shipment_id == shipment_id)

            rows = query.order_by(RevmSnapshot.run_timestamp.asc()).all()
            return [
                {
                    "timestamp":    r.run_timestamp.isoformat(),
                    "shipment_id":  r.shipment_id,
                    "revm":         r.revm,
                    "risk_score":   r.risk_score,
                    "decision":     r.decision_action,
                    "confidence":   r.confidence_score,
                }
                for r in rows
            ]
        finally:
            db.close()
