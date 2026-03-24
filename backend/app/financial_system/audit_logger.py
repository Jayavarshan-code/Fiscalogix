from sqlalchemy.orm import Session
from setup_db import AuditLog
from datetime import datetime

class AuditLogger:
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
        Immutable audit log insertion for SOC2 / SOX compliance requirements.
        """
        log_entry = AuditLog(
            tenant_id=tenant_id,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action_type=action_type,
            target_entity_id=target_entity_id,
            confidence_score=confidence_score,
            erp_receipt=erp_receipt,
            previous_state=previous_state or {},
            new_state=new_state or {}
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        print(f"[AUDIT] Logged action {action_type} on {target_entity_id} by {user_id}")
        return log_entry
