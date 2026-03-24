import math

class FutureImpactModel:
    def compute(self, row, predicted_delay, predicted_demand):
        """
        What long-term financial damage will this cause? (Behavioral AI)
        Calculates Churn Probability (Weibull decay) against Future Lifetime Value at Risk.
        """
        # Assume Customer Lifetime Value (CLV) is 5x their predicted next demand
        clv_at_risk = predicted_demand * 5.0
        
        # Behavioral Churn Model: Customers tolerate minor delays, but churn explodes after thresholds.
        tolerance_threshold = 3.0
        
        if predicted_delay <= tolerance_threshold:
            # Linear low-risk churn increment
            churn_prob = 0.02 * (predicted_delay / tolerance_threshold)
        else:
            # Exponential decay of loyalty once patience threshold is breached
            excess_delay = predicted_delay - tolerance_threshold
            churn_prob = 1.0 - math.exp(-0.25 * excess_delay)
            
        # Amplified Brand Damage: If margin is already negative, we shipped a rushed/compromised product
        if row.get("contribution_profit", 0) < 0:
            churn_prob = min(churn_prob * 1.5, 1.0)
            
        future_loss_value = clv_at_risk * churn_prob
        return future_loss_value
