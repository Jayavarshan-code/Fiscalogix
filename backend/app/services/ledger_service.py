import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel

class DecisionEntry(BaseModel):
    decision_id: str
    timestamp: str
    pillar_id: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    reasoning: str
    model_version: str
    previous_hash: str
    current_hash: str

class LedgerService:
    """
    Pillar 13: Decision Auditability & Compliance.
    Maintains an immutable, cryptographically-linked log of all platform decisions.
    Essential for legal defensibility in financial logistics.
    """
    
    def __init__(self):
        # In prod: This would load the last hash from a secure vault
        self.last_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    def _generate_hash(self, data: Dict[str, Any], prev_hash: str) -> str:
        """Creates a SHA-256 hash incorporating the previous entry."""
        combined = f"{json.dumps(data, sort_keys=True)}{prev_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()

    async def log_decision(
        self, 
        pillar: str, 
        inputs: Dict[str, Any], 
        outputs: Dict[str, Any], 
        reasoning: str,
        model_version: str = "v1.0.0"
    ) -> DecisionEntry:
        """
        Records a decision and returns the linked entry.
        """
        timestamp = datetime.utcnow().isoformat()
        raw_data = {
            "p": pillar,
            "i": inputs,
            "o": outputs,
            "r": reasoning,
            "t": timestamp,
            "m": model_version
        }
        
        current_hash = self._generate_hash(raw_data, self.last_hash)
        
        entry = DecisionEntry(
            decision_id=f"DEC_{hashlib.md5(timestamp.encode()).hexdigest()[:8]}",
            timestamp=timestamp,
            pillar_id=pillar,
            inputs=inputs,
            outputs=outputs,
            reasoning=reasoning,
            model_version=model_version,
            previous_hash=self.last_hash,
            current_hash=current_hash
        )
        
        # In prod: self.db.execute("INSERT INTO decision_ledger ...")
        self.last_hash = current_hash # Update the chain head
        return entry

    def verify_integrity(self, entries: List[DecisionEntry]) -> bool:
        """
        Verifies that the chain of decisions has not been tampered with.
        """
        for i in range(1, len(entries)):
            if entries[i].previous_hash != entries[i-1].current_hash:
                return False
        return True
