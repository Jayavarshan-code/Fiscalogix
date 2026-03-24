class CashBufferEngine:
    def compute(self, peak_deficit, shocks, confidence_score):
        """
        Determines exactly how much liquid cash is mathematically required to survive worst-case scenarios.
        """
        deficit = abs(peak_deficit)
        
        # Risk adjustment scales with volume of massive shocks mapped directly onto the timeline
        risk_adjustment = 0.05 * len(shocks) # Extrapolates 5% pure safety margin per distinct cash shock
        
        # Uncertainty penalty scales inversely with Trust Engine confidence
        uncertainty_penalty = max(0.0, 1.0 - confidence_score)
        
        # Base Buffer Tracker + Compound Risk Penalty + Systemic Uncertainty Cover
        required_buffer = deficit * (1.0 + risk_adjustment + uncertainty_penalty)
        
        # If no deficit exists, enforce a strictly baseline operational cash minimum
        if required_buffer == 0:
            required_buffer = 10000.0 # Standard defensive fallback
            
        return {
            "required_buffer": round(required_buffer, 2)
        }
