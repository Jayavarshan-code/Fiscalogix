from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

class SemanticDelta(BaseModel):
    """
    Next-Gen: The Compressed 'Meaning' of an Edge Decision.
    Does NOT contain raw PII or sensitive logistics data.
    """
    hive_id: str
    region: str
    timestamp: datetime = datetime.utcnow()
    
    # High-level state summaries
    efi_delta: float # The net impact on global EFI from local decisions
    risk_snapshot: Dict[str, float] # { "h3_index": local_risk_score }
    
    # Decisions taken locally
    decisions: List[str] # ["Rerouted Ship A", "Delayed Ship B"]
    
    # Reasoning compressed into embeddings or concise tokens
    intent_vector_summary: str 
    
    metadata: Dict[str, Any] = {}

class HiveNodeStatus(BaseModel):
    hive_id: str
    status: str # "Active", "Desynced", "Updating"
    last_sync: datetime
    local_compute_load: float
