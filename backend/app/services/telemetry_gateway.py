import h3
from typing import List, Dict, Any, Optional
from datetime import datetime

class TelemetryType:
    AIS = "AIS" # Vessel tracking
    WEATHER = "WEATHER" # Storms/Cyclones
    ELD = "ELD" # Truck telematics

class TelemetryGateway:
    """
    Pillar 2: Risk Radar - The 'Lens'.
    Aggregates disparate telemetry feeds into a unified H3-indexed state.
    """
    
    def __init__(self, h3_resolution: int = 7):
        self.h3_resolution = h3_resolution

    def ingest_ais_signal(self, mmsi: str, lat: float, lon: float) -> Dict[str, Any]:
        """Maps a ship signal to an H3 cell."""
        h3_index = h3.geo_to_h3(lat, lon, self.h3_resolution)
        return {
            "type": TelemetryType.AIS,
            "id": mmsi,
            "h3_index": h3_index,
            "timestamp": datetime.utcnow().isoformat()
        }

    def ingest_weather_event(self, event_id: str, lat: float, lon: float, severity: float) -> Dict[str, Any]:
        """Maps a weather event (storm/cyclone) to an H3 cell."""
        h3_index = h3.geo_to_h3(lat, lon, self.h3_resolution)
        return {
            "type": TelemetryType.WEATHER,
            "id": event_id,
            "h3_index": h3_index,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }

    def detect_spatial_overlap(self, event_a: Dict[str, Any], event_b: Dict[str, Any]) -> bool:
        """
        O(1) Spatial Join using H3 indices. 
        Detects if a ship and a weather event are in the same hexagon.
        """
        return event_a.get("h3_index") == event_b.get("h3_index")
