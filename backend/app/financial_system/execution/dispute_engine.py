from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

class AutomatedDisputeEngine:
    """
    Pillar 14: The Autonomous Profit Execution Layer.
    Translates observed financial loss (EFI) into legally defensible, executable claims.
    """
    def __init__(self):
        self.claim_threshold_inr = 50000  # Minimum EFI to auto-trigger a dispute

    def evaluate_claim_eligibility(self, efi_data: Dict[str, Any], contract_nlp_data: Dict[str, Any]) -> bool:
        """
        Determines if a shipment delay qualifies for automated dispute filing based on
        hard-calc EFI threshold and NLP-verified contract clauses.
        """
        total_delta = efi_data.get("headline_delta_inr", 0)
        penalty_clause = contract_nlp_data.get("liquidated_damages_clause", None)

        if total_delta >= self.claim_threshold_inr and penalty_clause:
            return True
        return False

    def build_evidence_bundle(self, shipment_id: str, efi_data: Dict, h3_spatial_log: List, contract_nlp_data: Dict) -> Dict:
        """
        Tri-Factor Reality Sync: Compiles the unassailable proof required to win the claim.
        1. Spatial Proof (H3 route deviation)
        2. Legal Proof (NLP exact clause extraction)
        3. Financial Proof (Deterministic math breakdown)
        """
        package_path = EvidencePackager.package_claim_evidence(shipment_id, h3_spatial_log, contract_nlp_data)
        return {
            "bundle_id": f"EVD-{str(uuid.uuid4())[:8].upper()}",
            "timestamp": datetime.utcnow().isoformat(),
            "shipment_id": shipment_id,
            "spatial_deviations": [log for log in h3_spatial_log if log.get('status') == 'off_route_delay'],
            "legal_basis": contract_nlp_data.get("liquidated_damages_clause"),
            "financial_calculation": efi_data.get("calculation_audit_trail"),
            "physical_package_path": package_path
        }

    def generate_carrier_claim_payload(self, shipment_id: str, evidence_bundle: Dict, efi_data: Dict) -> Dict[str, Any]:
        """
        Generates the final API payload ready to be pushed to the Carrier's EDI or the Tenant's ERP.
        """
        return {
            "claim_reference": f"CLM-{shipment_id}-{datetime.utcnow().strftime('%Y%m%d')}",
            "action": "FILE_DISPUTE",
            "claim_amount": efi_data.get("headline_delta_inr"),
            "currency": "INR",
            "reason_code": "DELAY_PENALTY_BREACH",
            "evidence_bundle_ref": evidence_bundle.get("bundle_id"),
            "status": "QUEUED_FOR_SUBMISSION"
        }

    def generate_claim_document_draft(self, claim_payload: Dict, evidence_bundle: Dict) -> str:
        """
        [PHASE 3: STEP 3] - Generates a formal, auditable Claim Draft.
        This is the document that proves Fiscalogix 'Makes You Money.'
        """
        draft = f"""
================================================================================
📜 OFFICIAL CLAIM NOTICE: {claim_payload['claim_reference']}
================================================================================
Recipient: Carrier Operations / Legal Dept
Date: {datetime.utcnow().strftime('%Y-%m-%d')}
Subject: Notice of Liquidated Damages - Shipment {evidence_bundle['shipment_id']}

1. THE BREACH:
   Our deterministic audit has verified a delay of {len(evidence_bundle['spatial_deviations'])} hrs 
   for Shipment {evidence_bundle['shipment_id']}.

2. LEGAL BASIS:
   As per {evidence_bundle['legal_basis']}, a penalty is triggered for delay performance.

3. FINANCIAL QUANTIFICATION:
   Total Claim Amount: INR {claim_payload['claim_amount']:,}
   Audit Trail: {evidence_bundle['financial_calculation']}

4. SUPPORTING EVIDENCE:
   Evidence Bundle Reference: {evidence_bundle['bundle_id']} (Includes H3 Spatial Logs)

Status: [DRAFT] Awaiting Human-in-the-Loop Approval.
================================================================================
        """
        return draft.strip()

    def execute_autonomous_recovery(self, shipment_data: Dict, efi_data: Dict, h3_log: List, nlp_data: Dict) -> Optional[Dict]:
        """
        The Main Execution Loop.
        If eligible, bundles evidence and returns the 'ready-to-fire' claim payload + Document Draft.
        """
        shipment_id = shipment_data.get("shipment_id", "UNKNOWN")
        
        # 1. Evaluate [PHASE 3: STEP 1 & 2]
        if not self.evaluate_claim_eligibility(efi_data, nlp_data):
            return {"status": "INELIGIBLE", "reason": "Threshold not met or no penalty clause found."}
            
        # 2. Bundle Evidence
        evidence = self.build_evidence_bundle(shipment_id, efi_data, h3_log, nlp_data)
        
        # 3. Generate Claim Payload
        claim_payload = self.generate_carrier_claim_payload(shipment_id, evidence, efi_data)
        
        # 4. Generate Formal Draft [PHASE 3: STEP 3]
        claim_draft = self.generate_claim_document_draft(claim_payload, evidence)
        
        return {
            "status": "CLAIM_GENERATED",
            "payload": claim_payload,
            "evidence": evidence,
            "draft_document": claim_draft
        }

# --- Quick Test Execution ---
if __name__ == "__main__":
    engine = AutomatedDisputeEngine()
    
    mock_efi = {"headline_delta_inr": 250000, "calculation_audit_trail": "(10 * 25000)"}
    mock_nlp = {"liquidated_damages_clause": "Section 4.2: Late delivery incurs Rs 25,000 per day."}
    mock_h3 = [{"h3_index": "8828308281fffff", "status": "off_route_delay", "duration_hrs": 240}]
    
    result = engine.execute_autonomous_recovery({"shipment_id": "LGX-992"}, mock_efi, mock_h3, mock_nlp)
    print(f"Dispute Engine Result: {result.get('status')} | Ref: {result.get('payload', {}).get('claim_reference')}")
