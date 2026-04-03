import math

class FXRiskModel:
    """
    Pillar 17: Global Currency Arbitrage Mapping.
    Calculates dynamic currency depreciation risk algebraically. If a shipment crosses 
    volatile currency zones and is heavily delayed, it exponentially models absolute USD margin erosion.
    """
    def __init__(self):
         # Standard approximation algorithms for annualized volatility against USD index
         self.volatility_index = {"US-CN": 0.04, "EU-US": 0.08, "APAC": 0.06, "LOCAL": 0.01}
         
    def compute_batch(self, rows_list, predicted_delays_array):
         """
         Vectorizes the computation of massive FX erosion penalties bridging cost decay and credit extension.
         """
         results = []
         for i, r in enumerate(rows_list):
             route = r.get("route", "LOCAL")
             volatility = self.volatility_index.get(route, 0.05)
             delay = predicted_delays_array[i]
             cost = float(r.get("total_cost", 0.0))
             
             # Base FX Erosion: Cost × Volatility × (Delay / 365)
             fx_erosion = cost * volatility * (delay / 365.0)
             
             # Fixed: Replace flat 1.5x multiplier with correct compound growth model.
             # If credit terms extend payment beyond 45 days, currency risk compounds geometrically.
             # Formula: fx_erosion *= e^(volatility × (credit_days / 365))
             credit_days = float(r.get("credit_days", 0.0))
             if credit_days > 45:
                 credit_extension_years = credit_days / 365.0
                 compound_factor = math.exp(volatility * credit_extension_years)
                 fx_erosion *= compound_factor
                 
             results.append(round(fx_erosion, 2))
         return results

