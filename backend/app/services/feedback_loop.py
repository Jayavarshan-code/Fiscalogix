import numpy as np
from typing import List, Dict, Any
from datetime import datetime

class FeedbackLoopService:
    """
    The Learning Brain: Computes the 'Delta' between prediction and reality.
    """
    
    def calculate_metrics(self, predicted_val: float, actual_val: float) -> Dict[str, float]:
        """
        Calculates core learning metrics for a single decision/outcome pair.
        """
        error = actual_val - predicted_val
        # Avoid division by zero
        denom = actual_val if actual_val != 0 else 1.0
        accuracy = 1 - (abs(error) / abs(denom))
        
        return {
            "error": round(error, 2),
            "accuracy": round(max(0, accuracy), 4)
        }

    def compute_learning_batch(self, decisions: List[Dict[str, Any]], outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes a batch of decisions and outcomes to compute aggregate metrics.
        """
        efi_errors = []
        delay_errors = []
        cost_errors = []
        
        # In a real system, we would join these on decision_id
        for i in range(len(decisions)):
            d = decisions[i]
            o = outcomes[i]
            
            efi_m = self.calculate_metrics(d["predicted_efi"], o["actual_efi"])
            delay_m = self.calculate_metrics(d["predicted_delay"], o["actual_delay"])
            cost_m = self.calculate_metrics(d["predicted_cost"], o["actual_cost"])
            
            efi_errors.append(efi_m["error"])
            delay_errors.append(delay_m["error"])
            cost_errors.append(cost_m["error"])
            
        # Bias = Avg(Predicted - Actual)
        # Note: If Bias is positive, the model is over-optimistic (predicting more than reality).
        bias = np.mean([d["predicted_efi"] - o["actual_efi"] for d, o in zip(decisions, outcomes)])
        
        return {
            "avg_efi_error": round(float(np.mean(efi_errors)), 2),
            "avg_delay_accuracy": round(float(np.mean([abs(e) for e in delay_errors])), 4), # Simplified for demo
            "avg_cost_accuracy": round(float(np.mean([abs(e) for e in cost_errors])), 4),
            "system_bias": round(float(bias), 2),
            "status": "OVER_OPTIMISTIC" if bias > 1000 else "CONSERVATIVE" if bias < -1000 else "BALANCED",
            "last_updated": datetime.utcnow().isoformat()
        }

    def residual_learning_correction(self, base_prediction: float, historical_bias: float) -> float:
        """
        Residual Learning: New Prediction = Base Model + Error Correction.
        """
        return base_prediction - historical_bias
