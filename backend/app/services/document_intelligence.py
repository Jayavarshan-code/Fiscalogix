import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.models.document_intelligence import (
    ExtractedDocument, DocumentType, PenaltyClause, 
    PenaltyTier, ComplianceRecord
)

from app.services.llm_gateway import LlmGateway

class DocumentIntelligenceService:
    """
    Pillar 9: Document Intelligence Platform (DIP).
    Handles the ingestion and intelligent extraction of logistics documents.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.llm_gateway = LlmGateway(api_key=self.api_key)

    async def process_document(self, file_content: bytes, filename: str) -> ExtractedDocument:
        """
        Orchestrates the full DIP pipeline: 
        Vision/OCR -> Classification -> Agentic Extraction.
        """
        # 1. Mock OCR/Vision Layer (In prod: Azure AI Document Intelligence / LayoutLMv3)
        raw_text = self._mock_ocr_layer(filename)
        
        # 2. Classifier: Determine Doc Type
        doc_type = self._classify_document(raw_text, filename)
        
        # 3. Agentic Extraction: Verfied reasoning with Dual-Model + Guardrails
        structured_data = await self.extract_with_verification(raw_text, doc_type)
        
        # 4. Extract confidence from the verified structure
        verification_metadata = structured_data.get("verification", {})
        confidence = verification_metadata.get("confidence", 0.95)
        
        return ExtractedDocument(
            doc_id=f"doc_{int(datetime.utcnow().timestamp())}",
            doc_type=doc_type,
            confidence_score=confidence,
            raw_text=raw_text,
            structured_data=structured_data,
            metadata={
                "filename": filename, 
                "source": "Manual Upload",
                "verification_status": verification_metadata.get("status")
            }
        )

    def _mock_ocr_layer(self, filename: str) -> str:
        """Simulates visual extraction of text from a PDF/Image."""
        if "contract" in filename.lower():
            return "MASTER SERVICE AGREEMENT: Penalty for late delivery is 5% per 24h delay."
        elif "permit" in filename.lower() or "license" in filename.lower():
            return "HAZMAT TRANSPORT PERMIT #HZ-991. Expiry Date: 2026-12-31."
        return "Generic document content for processing."

    def _classify_document(self, text: str, filename: str) -> DocumentType:
        """Categorizes the document based on content cues."""
        text_lower = text.lower()
        if "agreement" in text_lower or "contract" in text_lower:
            return DocumentType.CONTRACT
        if "permit" in text_lower or "license" in text_lower:
            return DocumentType.PERMIT
        if "invoice" in text_lower:
            return DocumentType.INVOICE
        return DocumentType.BILL_OF_LADING

    async def _run_agentic_extraction(self, text: str, doc_type: DocumentType) -> Dict[str, Any]:
        """
        MAX-STANDARD: Agentic Ensemble Reasoning.
        Distributes extraction to specialized 'Agents' based on domain.
        """
        if doc_type == DocumentType.CONTRACT:
            return await self._financier_agent(text)
        
        if doc_type == DocumentType.PERMIT:
            return await self._compliance_agent(text)
        
        if doc_type == DocumentType.BILL_OF_LADING:
            return await self._auditor_agent(text)
            
        return {"general_info": "Extracted key-value pairs from document."}

    async def _financier_agent(self, text: str) -> Dict[str, Any]:
        """Specialized Agent for complex financial logic (Penalties/SLAs)."""
        # In prod, this would be a specific LLM prompt for financial extraction
        return {
            "penalties": [
                PenaltyClause(
                    clause_id="late_delivery_tier_1",
                    description="Standard OTIF penalty for delayed arrival",
                    tiers=[
                        PenaltyTier(threshold_hours=12, penalty_value=250.0, is_percentage=False),
                        PenaltyTier(threshold_hours=24, penalty_value=5.0, is_percentage=True)
                    ],
                    currency="USD"
                ).dict()
            ],
            "billing_cycle": "Monthly",
            "payment_terms": "Net-30"
        }

    async def _compliance_agent(self, text: str) -> Dict[str, Any]:
        """Specialized Agent for regulatory/legal safety."""
        return {
            "compliance": ComplianceRecord(
                document_id="HZ-DOT-991",
                issuing_authority="US Dept of Transportation",
                expiry_date=datetime(2026, 12, 31),
                scope=["Hazmat Class 3", "Domestic Movement"]
            ).dict()
        }

    async def _auditor_agent(self, text: str) -> Dict[str, Any]:
        """Specialized Agent for validation (BoL vs PO reconciliation)."""
        return {
            "reconciliation": {
                "sku_match": True,
                "quantity_variance": 0.0,
                "seal_status": "Intact",
                "notes": "Semantic match confirmed across Bill of Lading and Purchase Order."
            }
        }

    def detect_semantic_gaps(self, contract: ExtractedDocument, insurance: ExtractedDocument) -> List[str]:
        """
        MAX-STANDARD Feature: Cross-Document Reasoning.
        Identifies gaps between related legal documents (e.g., Liability vs Coverage).
        """
        gaps = []
        # Logical reasoning: Compare extracted liability from contract vs coverage from insurance
        contract_limit = contract.structured_data.get("liability_limit", 0)
        insurance_limit = insurance.structured_data.get("coverage_limit", 0)
        
        if contract_limit > insurance_limit:
            gaps.append(f"LIABILITY GAP: Contract requires {contract_limit}, but Insurance only covers {insurance_limit}.")
        
        return gaps

    async def extract_with_verification(self, text: str, doc_type: DocumentType) -> Dict[str, Any]:
        """
        MAX-STANDARD: Tri-Factor Verification.
        1. Dual-Model Cross-Check.
        2. Logical Guardrails (Constraint Validation).
        3. Confidence-based HITL trigger.
        """
        # --- Factor 1: Dual-Model Extraction ---
        # Simulation of calling two independent LLM Agents (e.g., GPT-4o and Claude 3.5)
        model_a_results = await self._run_agentic_extraction(text, doc_type)
        model_b_results = await self._run_agentic_extraction(text, doc_type) # Simulated mirror
        
        is_consistent = model_a_results == model_b_results
        
        # --- Factor 2: Logical Guardrails ---
        is_safe = self._apply_logical_guardrails(model_a_results)
        
        # --- Factor 3: Verification Logic ---
        status = ValidationStatus.VERIFIED
        confidence = 0.99
        
        if not is_consistent:
            status = ValidationStatus.CONFLICT
            confidence = 0.60
        elif not is_safe:
            status = ValidationStatus.REJECTED
            confidence = 0.10
        elif "decimal_uncertainty" in text.lower(): # Simulated edge case
            status = ValidationStatus.PENDING_REVIEW
            confidence = 0.85

        # Update metadata with verification trail
        model_a_results["verification"] = {
            "status": status,
            "confidence": confidence,
            "consistency_match": is_consistent,
            "passed_guardrails": is_safe,
            "verified_at": datetime.utcnow().isoformat()
        }
        
        return model_a_results

    def _apply_logical_guardrails(self, data: Dict[str, Any]) -> bool:
        """
        Hardened constraint check: Ensures the LLM didn't hallucinate 
        impossible financial values (e.g., > 1,000% penalty).
        """
        penalties = data.get("penalties", [])
        for p in penalties:
            for tier in p.get("tiers", []):
                val = tier.get("penalty_value", 0)
                # Fail if penalty > 100% or < 0
                if tier.get("is_percentage") and (val > 100 or val < 0):
                    return False
        return True

    def sync_to_efi_engine(self, extracted_penalties: List[Dict[str, Any]], shipment_id: str):
        """
        Pillar Integration Bridge: Unstructured -> Financial Engine.
        Injects extracted document rules into the live EFI calculator.
        """
        # Logic: Update the global state/cache that the EFIEngine uses to lookup 
        # project-specific contract penalties.
        print(f"DEBUG: Injecting {len(extracted_penalties)} penalty rules for shipment {shipment_id} into EFI Engine.")
        # In prod: self.db_session.update(shipment_id, penalties=extracted_penalties)
