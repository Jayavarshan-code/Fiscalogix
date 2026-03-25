from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    CONTRACT = "contract"
    LICENSE = "license"
    PERMIT = "permit"
    BILL_OF_LADING = "bill_of_lading"
    INVOICE = "invoice"
    INSURANCE_POLICY = "insurance_policy"

class ValidationStatus(str, Enum):
    VERIFIED = "verified"
    PENDING_REVIEW = "pending_human_review"
    REJECTED = "rejected"
    CONFLICT = "model_conflict"

class PenaltyTier(BaseModel):
    threshold_hours: int
    penalty_value: float
    is_percentage: bool = True

class PenaltyClause(BaseModel):
    clause_id: str
    description: str
    tiers: List[PenaltyTier]
    currency: str = "USD"
    max_penalty: Optional[float] = None
    confidence_score: float = 1.0 # New
    validation_status: ValidationStatus = ValidationStatus.VERIFIED # New

class ComplianceRecord(BaseModel):
    document_id: str
    issuing_authority: str
    expiry_date: datetime
    is_valid: bool = True
    scope: Optional[List[str]] = None # e.g., ["Hazmat", "International"]

class ExtractedDocument(BaseModel):
    doc_id: str
    doc_type: DocumentType
    confidence_score: float
    raw_text: Optional[str] = None
    structured_data: Dict[str, Any] # Flexible KV store for various doc types
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processed_at: datetime = Field(default_factory=datetime.utcnow)

# --- Database Schema (SQLAlchemy / Mock) ---
# Note: In a full-scale app, these would be SQLAlchemy Base classes.
class DocumentLog:
    """SQLAlchemy model for persisting document processing history."""
    pass
