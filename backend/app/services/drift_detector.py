from scipy import stats
import numpy as np
from typing import List

class DriftDetector:
    """
    Pillar 6 Upgrade: Autonomous Drift Detection.
    Uses Kolmogorov-Smirnov (K-S test) to detect distribution shifts.
    """
    
    def detect_distribution_shift(self, baseline_dist: List[float], current_dist: List[float], p_value_threshold: float = 0.05) -> dict:
        """
        Compares two distributions. If p-value < threshold, a shift (drift) is detected.
        """
        if len(baseline_dist) < 10 or len(current_dist) < 10:
            return {"drift_detected": False, "p_value": 1.0, "reason": "Insufficient Data"}
            
        # K-S Test: Null hypothesis is that they are from the same distribution
        ks_stat, p_value = stats.ks_2samp(baseline_dist, current_dist)
        
        drift_detected = p_value < p_value_threshold
        
        return {
            "drift_detected": drift_detected,
            "ks_statistic": round(ks_stat, 4),
            "p_value": round(p_value, 4),
            "confidence": 1 - p_value,
            "alert_level": "CRITICAL" if p_value < 0.01 else "WARNING" if drift_detected else "STABLE"
        }
