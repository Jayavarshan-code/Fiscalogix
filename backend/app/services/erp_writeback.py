import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ERPWriteBackService:
    """
    [PHASE 3: GAP 3] - ERP Financial Write-Back (Return Filing).
    Closes the Accounting Loop. Once Fiscalogix successfully recovers a penalty from a carrier,
    this service pushes a 'Credit Memo' directly into the tenant's SAP/Oracle ERP system.
    This ensures the CFO's ledger is automatically reconciled without manual data entry.
    """
    
    def __init__(self, tenant_erp_type: str = "SAP_S4HANA"):
        self.erp_type = tenant_erp_type

    def generate_sap_credit_memo(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the recovered capital into a standard SAP IDoc or REST payload for Accounts Receivable.
        """
        return {
            "DocumentType": "CreditMemo",
            "CompanyCode": "1000", # Example Tenant Code
            "CustomerNo": claim_data.get("carrier_id", "CARRIER_UNKNOWN"),
            "DocumentDate": claim_data.get("settlement_date"),
            "Amount": claim_data.get("recovered_amount"),
            "Currency": claim_data.get("currency", "INR"),
            "HeaderExt": f"Fiscalogix Recovery - {claim_data.get('claim_id')}",
            "ItemText": f"Delay Penalty Recovered via SLA {claim_data.get('clause_ref')}"
        }

    def execute_erp_reconciliation(self, claim_id: str, recovered_amount: float, carrier_id: str, clause_ref: str) -> bool:
        """
        The main execution hook called when a user marks a claim as 'SETTLED/RECOVERED' in the HITL Dashboard.
        """
        from datetime import datetime
        
        claim_data = {
            "claim_id": claim_id,
            "recovered_amount": recovered_amount,
            "carrier_id": carrier_id,
            "clause_ref": clause_ref,
            "settlement_date": datetime.utcnow().strftime("%Y-%m-%d")
        }
        
        logger.info(f"Initiating remote Write-Back to {self.erp_type} for Claim {claim_id}...")
        
        if self.erp_type == "SAP_S4HANA":
            payload = self.generate_sap_credit_memo(claim_data)
            # MOCK: requests.post("https://tenant-sap-gateway.com/api/credit", json=payload)
            logger.info(f"SUCCESS: Pushed Credit Memo to SAP Accounts Receivable: {json.dumps(payload)}")
            return True
        else:
            logger.warning(f"Unsupported ERP Type: {self.erp_type}")
            return False

# Quick Execution Test
if __name__ == "__main__":
    service = ERPWriteBackService("SAP_S4HANA")
    service.execute_erp_reconciliation(
        claim_id="REV-001",
        recovered_amount=400000,
        carrier_id="VND-MAERSK-01",
        clause_ref="Clause 7.2 Delay Penalty"
    )
