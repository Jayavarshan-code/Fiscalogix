import math
import statistics

class ConfidenceTrustEngine:
    """
    Quantifies how reliable the Financial Twin's predictions are (0 to 1).
    Based on Model Certainty, Data Completeness, and Environmental Volatility Signal.

    WHY THE Z-SCORE LOGIC WAS FLAWED:
    Previously, high Z-scores (wide delay variance) REDUCED the confidence score.
    The reasoning was: "If delays are unstable, we can't trust our predictions."
    This is methodologically incorrect. A genuine port strike creates high delay
    variance — but the model's PREDICTIONS are still as accurate as they ever were.
    Penalising the trust score during a real crisis creates a paradox:
      → The system becomes LESS confident exactly when executives need it MOST.
    A CFO seeing "System Confidence: 42%" during the Red Sea crisis will stop trusting
    the tool — the moment it should be guiding critical rerouting decisions.

    FIX: Separate "Environmental Volatility" from "Model Instability".
    - High Z-score = the environment IS volatile. This is data, not a flaw.
    - Confidence score now reflects: Model Certainty × Data Completeness only.
    - Environmental volatility is returned as a SEPARATE metric (volatility_alert)
      so the UI can surface it as context WITHOUT undermining the trust score.
    """

    def compute(self, enriched_records, shocks):
        if not enriched_records:
            return 0.0

        # 1. Model Certainty: average sigmoid classifier confidence from XGBoost
        certainties = [r.get("risk_confidence", 0.5) for r in enriched_records]
        model_certainty = sum(certainties) / len(certainties)

        # 2. Data Completeness: penalise for missing critical financial fields
        completeness_scores = []
        for r in enriched_records:
            score = 1.0
            if r.get("wacc", 0) == 0:             score -= 0.10  # No cost of capital
            if r.get("total_cost", 0) == 0:        score -= 0.20  # No shipment cost
            if r.get("predicted_demand", 0) <= 0:  score -= 0.10  # No demand signal
            if r.get("order_value", 0) == 0:       score -= 0.15  # No revenue anchor
            completeness_scores.append(max(0.0, score))
        data_completeness = sum(completeness_scores) / len(completeness_scores)

        # Confidence = weighted blend of model certainty and data completeness only
        # Environmental volatility is intentionally excluded — it's signal, not noise.
        confidence_score = (0.55 * model_certainty) + (0.45 * data_completeness)

        # 3. Compute Environmental Volatility separately as an alert signal
        delays = [r.get("predicted_delay", 0) for r in enriched_records]
        volatility_alert = "NOMINAL"
        if len(delays) > 1:
            mean_d = statistics.mean(delays)
            stdev_d = statistics.stdev(delays) or 1.0
            avg_z = sum(abs(d - mean_d) / stdev_d for d in delays) / len(delays)

            if avg_z > 2.5:
                volatility_alert = "CRITICAL"    # Likely systemic disruption (port strike, etc.)
            elif avg_z > 1.5:
                volatility_alert = "ELEVATED"    # Unusual variance — review active routes
            elif avg_z > 0.8:
                volatility_alert = "MODERATE"    # Minor operational turbulence

        # Attach both signals to shocks for the frontend to surface independently
        for s in shocks:
            s["confidence"]          = round(confidence_score, 2)
            s["volatility_alert"]    = volatility_alert

        return round(confidence_score, 2)
