from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class ExternalSpatialEvent(Base):
    """
    Stores raw, sovereign external data (Weather, Geopolitics, Port Congestion).
    Tied directly to H3 Indices to ensure 'Deterministic Rerouting' based on 
    environmental truth rather than 3rd-party probabilistic black-boxes.
    """
    __tablename__ = "external_spatial_events"

    id = Column(Integer, primary_key=True, index=True)
    h3_index = Column(String(15), index=True, nullable=False)  # The specific spatial hex map
    
    event_type = Column(String(50), index=True, nullable=False)  # 'WEATHER', 'GEOPOLITICAL', 'PORT_CONGESTION'
    source_api = Column(String(50), nullable=False)              # 'OpenWeatherMap', 'ACLED', 'MarineTraffic'
    
    severity_score = Column(Float, nullable=False)               # 0.0 to 1.0 (Controls EFI impact multipliers)
    description = Column(String(255))
    
    # Raw JSON payload from the API for auditability (The 'Sovereign Proof')
    raw_payload = Column(JSON)
    
    is_active = Column(Boolean, default=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)                 # When the event is expected to clear

    def __repr__(self):
        return f"<ExternalSpatialEvent(type={self.event_type}, h3={self.h3_index}, severity={self.severity_score})>"
