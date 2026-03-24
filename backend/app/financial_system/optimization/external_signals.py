import random
from typing import Dict, List, Any
from datetime import datetime

class ExternalSignalAggregator:
    """
    Simulates high-fidelity ingestion from external APIs:
    - Weather (Storms, Typhoons)
    - AIS (Port Vessel Density/Queues)
    - News (Strikes, Geopolitics, Port Closures)
    """
    
    @staticmethod
    def get_signals_for_node(node_id: str) -> List[Dict[str, Any]]:
        """
        Fetch simulated real-time signals for a specific node.
        In production, this would hit: weather.com, marinetraffic.com, etc.
        """
        signals = []
        
        # 1. Weather Signals (High Impact Rules)
        if "PORT" in node_id or "OCEAN" in node_id:
            if random.random() > 0.7:
                signals.append({
                    "type": "WEATHER",
                    "id": "WV-402",
                    "severity": "HIGH",
                    "message": "Heavy Squall / Typhoon Warning in sector.",
                    "mode_impact": ["OCEAN", "BARGE"]
                })

        # 2. AIS Port Congestion (Queue signals)
        if "PORT" in node_id:
            vessel_queue = random.randint(5, 45)
            if vessel_queue > 30:
                signals.append({
                    "type": "AIS",
                    "id": "AIS-Q-01",
                    "severity": "MEDIUM",
                    "message": f"Elevated Hub Congestion: {vessel_queue} vessels awaiting berth.",
                    "metric": {"vessel_count": vessel_queue}
                })

        # 3. News / Geopolitical Signals
        if random.random() > 0.85:
            signals.append({
                "type": "NEWS",
                "id": "NEWS-STRIKE-01",
                "severity": "CRITICAL",
                "message": "Flash Strike detected at industrial terminal.",
                "source": "Reuters"
            })
            
        return signals

    @staticmethod
    def get_signals_for_route(origin: str, destination: str) -> List[Dict[str, Any]]:
        """Aggregate signals across a transit lane."""
        return ExternalSignalAggregator.get_signals_for_node(origin) + \
               ExternalSignalAggregator.get_signals_for_node(destination)
