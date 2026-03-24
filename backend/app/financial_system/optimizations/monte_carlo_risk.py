import numpy as np
from typing import Dict, List, Any

class MonteCarloRiskEngine:
    @staticmethod
    def simulate(
        legs: List[Dict[str, float]], 
        target_arrival_days: int,
        simulations: int = 10000
    ) -> Dict[str, Any]:
        """
        Runs a Monte Carlo simulation across multiple transit legs to find the 
        probabilistic certainty of arriving before the target date.
        """
        total_days_simulated = np.zeros(simulations)
        
        for leg in legs:
            leg_samples = np.random.normal(loc=leg["avg_days"], scale=leg["std_dev"], size=simulations)
            total_days_simulated += leg_samples
            
        successes = np.sum(total_days_simulated <= target_arrival_days)
        probability_of_success = successes / simulations
        percentile_95 = np.percentile(total_days_simulated, 95)
        
        return {
            "simulations_run": simulations,
            "probability_on_time": round(float(probability_of_success), 4),
            "percentile_95_arrival_days": round(float(percentile_95), 1),
            "risk_assessment": "CRITICAL" if probability_of_success < 0.8 else "SAFE"
        }
