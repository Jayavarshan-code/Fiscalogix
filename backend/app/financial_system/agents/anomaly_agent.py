"""
AnomalyAgent — statistical outlier detection across the portfolio.

Only dispatched when the situation context flags sigma deviations > 2.
Identifies which specific shipments are statistical outliers and why.
"""

import statistics
from typing import Dict, Any, List
from .base_agent import BaseAgent


class AnomalyAgent(BaseAgent):
    name = "AnomalyAgent"

    async def run_logic(
        self,
        enriched_data: List[Dict[str, Any]],
        prior_results: Dict[str, Any],
        tenant_id: str,
    ) -> Dict[str, Any]:
        anomalies = []

        for metric in ("revm", "risk_score", "predicted_delay", "sla_penalty"):
            values = [
                row.get(metric) for row in enriched_data
                if row.get(metric) is not None
            ]
            if len(values) < 4:
                continue

            mean  = statistics.mean(values)
            stdev = statistics.stdev(values) or 1e-9

            for i, row in enumerate(enriched_data):
                val = row.get(metric)
                if val is None:
                    continue
                z = abs(val - mean) / stdev
                if z > 2.5:
                    anomalies.append({
                        "shipment_id": row.get("shipment_id") or row.get("po_number", f"idx-{i}"),
                        "metric":      metric,
                        "value":       round(val, 2),
                        "z_score":     round(z, 2),
                        "direction":   "HIGH" if val > mean else "LOW",
                        "mean":        round(mean, 2),
                        "route":       row.get("route", "N/A"),
                    })

        # Sort by severity
        anomalies.sort(key=lambda x: x["z_score"], reverse=True)

        return {
            "anomalies":       anomalies[:20],   # top 20 for the dashboard
            "anomaly_count":   len(anomalies),
            "metrics_checked": ["revm", "risk_score", "predicted_delay", "sla_penalty"],
        }
