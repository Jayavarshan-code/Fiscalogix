import sys
import os
import json

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.financial_system.execution.dispute_engine import AutomatedDisputeEngine
from app.services.erp_writeback import ERPWriteBackService

def run_phase3_pipeline_test():
    print("🚀 Initiating E2E Phase 3 Recovery Pipeline Test...\n")

    # MOCK INPUTS (Simulating Data passed from earlier pipelines)
    shipment_data = {"shipment_id": "LGX-992-DEMO"}
    
    # 1. EFI Output (Loss Detected)
    efi_data = {
        "headline_delta_inr": 450000,  # Crosses 10k threshold
        "calculation_audit_trail": "2 days @ 2.5% value/day = 450000"
    }

    # 2. NLP Output (Contract Audit)
    nlp_data = {
        "contract_id": "MSA_MAERSK_2026",
        "penalties": {"liquidated_damages": "2.5% delay penalty per 24 hours."}
    }

    # 3. Spatial DB Output (Proof of Delay)
    h3_log = [
        {"h3": "8844c12bb1fffff", "status": "off_route_delay", "duration_hrs": 48}
    ]

    # --- EXECUTION ---
    print("STEP 1: Engaging Pilar 14 - Automated Dispute Engine...")
    dispute_engine = AutomatedDisputeEngine()
    result = dispute_engine.execute_autonomous_recovery(shipment_data, efi_data, h3_log, nlp_data)
    
    if result["status"] == "CLAIM_GENERATED":
        print("✅ SUCCESS: Claim Generated and Evidence Bundled.")
        print(f"📦 Evidence Package: {result['evidence']['physical_package_path']}")
        print(f"\n📜 DRAFT DOCUMENT PREVIEW:\n{result['draft_document'][:300]}...\n")
    else:
        print("❌ FAILED: Claim eligibility rejected.")
        return

    # --- SIMULATE CARRIER NEGOTIATION ---
    print("STEP 2: Simulating Carrier 'Force Majeure' Rejection...")
    # (Assuming DisputeResolutionTracker logic here directly for testing)
    carrier_reply = "Claim Denied due to Force Majeure."
    print(f"Carrier Response: '{carrier_reply}' -> Status: CONTESTED -> Running External API Weather Audit...")
    print("Weather Audit: NO STORMS LOGGED AT LOCATION. Counter-Claim Sent. Carrier agrees to Settle.\n")

    # --- ERP WRITE-BACK ---
    print("STEP 3: Initiating ERP Write-Back (Closing the Accounting Loop)...")
    erp_service = ERPWriteBackService("SAP_S4HANA")
    writeback_success = erp_service.execute_erp_reconciliation(
        claim_id=result["payload"]["claim_reference"],
        recovered_amount=result["payload"]["claim_amount"],
        carrier_id="MAERSK-GLOBAL",
        clause_ref=nlp_data["contract_id"]
    )

    if writeback_success:
        print("✅ SUCCESS: Phase 3 Pipeline Complete. CFO ledger updated with recovered capital.")
    else:
        print("❌ FAILED: ERP Write-Back failed.")

if __name__ == "__main__":
    run_phase3_pipeline_test()
