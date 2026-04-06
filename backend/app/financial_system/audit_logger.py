import logging
import uuid
import datetime
from sqlalchemy.orm import Session
from setup_db import AuditLog

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Immutable audit trail for SOC2/SOX compliance.

    FIX M4 (Critical): Added log_batch() method.
    WHAT WAS WRONG: orchestrator.py called self.audit.log_batch(enriched) but
    AuditLogger only had log_execution() — which also requires a db Session
    parameter the orchestrator never passed. AttributeError on every run meant
    the audit trail has been 100% broken since it was built.

    HOW IT WAS FIXED:
    1. Added log_batch() as the entry point for the orchestrator — no Session
       argument required (creates its own internal session).
    2. log_execution() is preserved for direct per-event logging from routes.
    3. Both methods use structured logging instead of print().
    """

    def log_batch(self, enriched_records: list, tenant_id: str = "default_tenant"):
        """
        Batch audit writer called by the orchestrator after each run.
        Creates its own DB session — orchestrator does not need to pass one.
        Logs one AuditLog entry per enriched record with the final decision.
        """
        from app.Db.connections import SessionLocal

        if not enriched_records:
            return

        db = SessionLocal()
        try:
            entries = []
            for record in enriched_records:
                shipment_id = str(record.get("shipment_id", "UNKNOWN"))
                decision_info = record.get("decision", {})
                entries.append(AuditLog(
                    tenant_id        = record.get("tenant_id", tenant_id),
                    timestamp        = datetime.datetime.utcnow(),
                    user_id          = "SYSTEM",
                    action_type      = "REVM_COMPUTATION",
                    target_entity_id = shipment_id,
                    confidence_score = record.get("risk_confidence", None),
                    new_state        = {
                        "revm":     record.get("revm"),
                        "decision": decision_info.get("action"),
                        "tier":     decision_info.get("tier"),
                    },
                    previous_state   = {},
                    erp_receipt      = {
                        "risk_score":   record.get("risk_score"),
                        "sla_penalty":  record.get("sla_penalty"),
                        "fx_cost":      record.get("fx_cost"),
                    }
                ))

            db.bulk_save_objects(entries)
            db.commit()
            logger.info(f"AuditLogger: batch of {len(entries)} records logged for tenant={tenant_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"AuditLogger.log_batch failed: {type(e).__name__}: {e}", exc_info=True)
            raise
        finally:
            db.close()

    @staticmethod
    def log_execution(
        db: Session,
        tenant_id: str,
        user_id: str,
        action_type: str,
        target_entity_id: str,
        confidence_score: float,
        erp_receipt: dict,
        previous_state: dict = None,
        new_state: dict = None
    ):
        """
        Single-event audit logger for direct route-level calls.
        Requires an injected db Session (from FastAPI's get_db dependency).
        """
        log_entry = AuditLog(
            tenant_id        = tenant_id,
            timestamp        = datetime.datetime.utcnow(),
            user_id          = user_id,
            action_type      = action_type,
            target_entity_id = target_entity_id,
            confidence_score = confidence_score,
            erp_receipt      = erp_receipt,
            previous_state   = previous_state or {},
            new_state        = new_state or {}
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        logger.info(f"[AUDIT] {action_type} on {target_entity_id} by {user_id}")
        return log_entry
