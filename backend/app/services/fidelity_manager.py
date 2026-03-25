from typing import Dict, Any, List
import numpy as np

class FidelityManager:
    """
    Pillar 1/5 Bridge: The 'Anti-Hallucination' Guardrail.
    Calculates a Data Integrity Score (DIS) to prevent 'Garbage In, Garbage Out' in EFI.
    """
    
    @staticmethod
    def calculate_fidelity_score(
        input_data: Dict[str, Any],
        source: str = "manual", # native_erp, partner_api, manual_csv
        historical_stats: Dict[str, Any] = None
    ) -> float:
        """
        Computes a DIS from 0.0 to 1.0.
        """
        score = 1.0
        
        # 1. Source Trust Penalty
        trust_weights = {
            "native_erp": 1.0, # High trust
            "partner_api": 0.8, # Medium trust
            "manual": 0.5 # Low trust
        }
        score *= trust_weights.get(source, 0.5)
        
        # 2. Completeness Check
        required_fields = ["revenue", "cost", "shipment_id"]
        found_fields = [f for f in required_fields if input_data.get(f)]
        completeness = len(found_fields) / len(required_fields)
        score *= (0.5 + (0.5 * completeness))
        
        # 3. Plausibility Check (Simple Z-Score simulation)
        # If the cost is 100x the historical average, it's likely a typo/hallucination
        if historical_stats and "avg_cost" in historical_stats:
            current_cost = input_data.get("cost", 0)
            avg = historical_stats["avg_cost"]
            if current_cost > (10.0 * avg) or current_cost < (0.1 * avg):
                score *= 0.7 # Plausibility penalty
                
        return round(max(0.01, min(1.0, score)), 2)

    @staticmethod
    def get_integrity_report(score: float) -> str:
        if score > 0.9: return "High Fidelity: Trusted Decision"
        if score > 0.7: return "Medium Fidelity: Verify Input Sources"
        return "Low Fidelity: FINANCIAL HALLUCINATION RISK"
