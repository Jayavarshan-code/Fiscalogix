from typing import List, Dict, Any, Optional
from app.services.telemetry_gateway import TelemetryType

class SpatialRiskEngine:
    """
    Pillar 2: Risk Radar - Spatial Risk Engine.
    Uses H3 Hexagonal Grid-State to map risk density in real-time.
    """
    
    def __init__(self):
        # Global state of 'Hot' H3 cells (Simulation of a Redis/In-memory store)
        self.hex_risk_state: Dict[str, float] = {}

    def process_telemetry_batch(self, batch: List[Dict[str, Any]]):
        """
        Updates the global honeycomb risk state based on incoming telemetry.
        """
        for signal in batch:
            h3_index = signal.get("h3_index")
            telemetry_type = signal.get("type")
            
            if telemetry_type == TelemetryType.WEATHER:
                severity = signal.get("severity", 0.5)
                # Spike the risk of this hex cell
                self.hex_risk_state[h3_index] = severity
            
            elif telemetry_type == TelemetryType.AIS:
                # Ships don't generate risk intrinsically in this model yet;
                # they inherit risk from the cell they occupy.
                pass

    def get_realtime_risk(self, h3_index: str) -> float:
        """
        O(1) Risk Lookup. 
        Returns the environmental risk of a specific hexagon.
        """
        return self.hex_risk_state.get(h3_index, 0.05)

    def calculate_compound_risk(self, shipment_data: Dict[str, Any]) -> float:
        """
        Calculates the risk of a shipment by joining its H3 cell with the 
        active environmental threat state.
        """
        h3_index = shipment_data.get("h3_index")
        base_ml_risk = shipment_data.get("base_risk", 0.1)
        
        spatial_risk = self.get_realtime_risk(h3_index)
        
        # Compound formula: Base ML Risk + Spatial Penalty
        # (Simulation of a more complex probabilistic join)
        compound_risk = base_ml_risk + (spatial_risk * 0.5)
        
        return min(0.99, compound_risk)
