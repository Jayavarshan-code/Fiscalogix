import statistics

class ConfidenceTrustEngine:
    def compute(self, enriched_records, shocks):
        """
        Quantifies how reliable the Financial Twin's predictions are (0 to 1).
        Based on Data Stability, Model Certainty, and Data Completeness.
        """
        if not enriched_records:
            return 0.0
            
        # 1. Model Certainty (Average predictive risk confidence natively output by Sigmoid classifier)
        certainties = [r.get("risk_confidence", 0.5) for r in enriched_records]
        model_certainty = sum(certainties) / len(certainties)

        # 2. Data Stability (Z-Score approximation on delays to detect heavy environmental abnormalities)
        delays = [r.get("delay_days", 0) for r in enriched_records]
        if len(delays) > 1:
            mean_delay = statistics.mean(delays)
            stdev_delay = statistics.stdev(delays) or 1.0 # prevent div by zero
            # If current delays are wildly out of band, stability heavily drops
            z_scores = [abs(d - mean_delay) / stdev_delay for d in delays]
            avg_z = sum(z_scores) / len(z_scores)
            data_stability = max(0.0, 1.0 - (avg_z * 0.15)) # 15% penalty per std deviation stretch
        else:
            data_stability = 0.9 # Default stable if single isolated record
            
        # 3. Data Completeness (Checking for default fallbacks or corrupt inputs)
        completeness_scores = []
        for r in enriched_records:
            score = 1.0
            if r.get("wacc", 0) == 0: score -= 0.1
            if r.get("total_cost", 0) == 0: score -= 0.2
            if r.get("predicted_demand", 0) <= 0: score -= 0.1
            completeness_scores.append(max(0.0, score))
        data_completeness = sum(completeness_scores) / len(completeness_scores)

        # Weighted formula emphasizing foundational Data Integrity strongly alongside Model confidence
        confidence_score = (0.4 * model_certainty) + (0.4 * data_stability) + (0.2 * data_completeness)
        
        # Retroactively attach systemic confidence directly back onto projected timeline shocks
        for s in shocks:
            s["confidence"] = round(confidence_score, 2)
            
        return round(confidence_score, 2)
