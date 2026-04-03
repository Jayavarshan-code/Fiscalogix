from typing import List, Dict, Any, Optional
from datetime import datetime
from ...models.document_intelligence import (
    DocumentType, 
    ValidationStatus, 
    ExtractedDocument, 
    PortFeeRecord, 
    CustomsDutyRecord,
    PenaltyClause
)

class DocumentAuditor:
    """
    The 'Judge' of the Fiscalogix system. 
    Audits financial and legal documents against live telemetry and ERP benchmarks.
    """
    
    def __init__(self, logger=None):
        self.logger = logger

    def audit_port_fees(self, 
                       extracted_invoice: ExtractedDocument, 
                       benchmark_fees: PortFeeRecord,
                       is_congested: bool = False) -> Dict[str, Any]:
        """
        Detects 'Surcharge Bloat' by comparing invoiced port fees against benchmarks.
        """
        invoiced_thc = extracted_invoice.structured_data.get("thc", 0.0)
        invoiced_congestion = extracted_invoice.structured_data.get("congestion_fee", 0.0)
        
        results = {
            "status": "verified",
            "overcharge_detected": 0.0,
            "flags": []
        }
        
        # 1. THC Check
        if invoiced_thc > benchmark_fees.standard_thc:
            delta = invoiced_thc - benchmark_fees.standard_thc
            results["overcharge_detected"] += delta
            results["flags"].append(f"THC Overcharge: ${delta} above benchmark")
            results["status"] = "flagged"
            
        # 2. Congestion Check (The RiskRadar Reality Sync)
        if invoiced_congestion > 0 and not is_congested:
            results["overcharge_detected"] += invoiced_congestion
            results["flags"].append(f"Unauthorized Congestion Fee: ${invoiced_congestion} (No congestion detected by RiskRadar)")
            results["status"] = "flagged"
            
        return results

    def audit_customs_duty(self, 
                          extracted_challan: ExtractedDocument, 
                          benchmark_duty: CustomsDutyRecord) -> Dict[str, Any]:
        """
        Detects misclassification overpayments by comparing paid duties with optimal HS-codes.
        """
        paid_duty = extracted_challan.structured_data.get("paid_duty", 0.0)
        hs_code_used = extracted_challan.structured_data.get("hs_code", "")
        
        results = {
            "status": "verified",
            "saving_opportunity": 0.0,
            "flags": []
        }
        
        if paid_duty > (benchmark_duty.total_effective_duty * 1.01): # 1% margin
            delta = paid_duty - benchmark_duty.total_effective_duty
            results["saving_opportunity"] = delta
            results["flags"].append(f"Duty Overpayment: ${delta} (Optimized HS-Code {benchmark_duty.hs_code} is cheaper)")
            results["status"] = "flagged"
            
        return results

    def audit_contract_penalties(self,
                               penalty_clause: PenaltyClause,
                               actual_delay_hours: int) -> Dict[str, Any]:
        """
        Calculates the 'Recoverable Capital' from contractual penalties.
        """
        applicable_penalty = 0.0
        
        # Sort tiers by threshold to find the highest applicable one
        sorted_tiers = sorted(penalty_clause.tiers, key=lambda x: x.threshold_hours, reverse=True)
        
        for tier in sorted_tiers:
            if actual_delay_hours >= tier.threshold_hours:
                applicable_penalty = tier.penalty_value
                break
                
        return {
            "penalty_to_claim": applicable_penalty,
            "currency": penalty_clause.currency,
            "delay_actual": actual_delay_hours,
            "status": "claim_generated" if applicable_penalty > 0 else "no_claim"
        }
