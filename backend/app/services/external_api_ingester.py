import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.external_events import ExternalSpatialEvent

logger = logging.getLogger(__name__)

import json
import logging
import os
import requests
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models.external_events import ExternalSpatialEvent

load_dotenv() # Load keys from .env file

logger = logging.getLogger(__name__)

class ExternalApiIngester:
    """
    The pipeline that pulls raw environmental truth (Weather, Geopolitics, Port Congestion) 
    directly into Fiscalogix.
    Supports both live API ingestion and fallback mock data for architectural proof.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.weather_key = os.getenv("OPENWEATHER_API_KEY")
        self.acled_key = os.getenv("ACLED_API_KEY")
        self.marinetraffic_key = os.getenv("MARINETRAFFIC_API_KEY")

    def fetch_live_weather_events(self, lat: float = 25.7617, lon: float = -80.1918) -> List[Dict[str, Any]]:
        """
        Connects to OpenWeatherMap to find severe weather events.
        Default coordinates set to Port of Miami for demonstration.
        """
        if not self.weather_key or self.weather_key == "your_openweather_api_key_here":
            logger.warning("No valid OpenWeatherMap key found. Using MOCK weather data.")
            return [{
                "h3_index": "8844c12bb1fffff", 
                "event_type": "WEATHER",
                "source": "OpenWeatherMap-MOCK",
                "severity": 0.95,
                "description": "Category 4 Hurricane approaching Port of Miami.",
                "raw_payload": {"wind_knots": 130, "status": "MOCK"}
            }]

        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.weather_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            # Simple normalization logic: if weather ID < 600 (Storms/Rain), calculate severity
            weather_id = data.get("weather", [{}])[0].get("id", 800)
            severity = 0.8 if weather_id < 600 else 0.1
            
            return [{
                "h3_index": "8844c12bb1fffff", # In production, convert lat/lon to H3 index
                "event_type": "WEATHER",
                "source": "OpenWeatherMap-LIVE",
                "severity": severity,
                "description": f"Live Weather: {data.get('weather', [{}])[0].get('description')}",
                "raw_payload": data
            }]
        except Exception as e:
            logger.error(f"Weather Ingestion Failed: {str(e)}")
            return []

    def fetch_live_geopolitical_events(self) -> List[Dict[str, Any]]:
        """
        Connects to ACLED API for real-time conflict event monitoring.
        """
        if not self.acled_key:
            logger.warning("No ACLED key found. Using MOCK geopolitical data.")
            return [{
                "h3_index": "8828308281fffff", 
                "event_type": "GEOPOLITICAL",
                "source": "ACLED-MOCK",
                "severity": 1.0,
                "description": "Armed conflict detected in Red Sea corridor.",
                "raw_payload": {"status": "MOCK"}
            }]

        try:
            # ACLED API typically requires key and email as parameters
            url = f"https://api.acleddata.com/acled/read/?key={self.acled_key}&email={os.getenv('ACLED_EMAIL')}&limit=1"
            response = requests.get(url, timeout=10)
            data = response.json().get("data", [])
            
            if not data: return []
            
            event = data[0]
            return [{
                "h3_index": "8828308281fffff", 
                "event_type": "GEOPOLITICAL",
                "source": "ACLED-LIVE",
                "severity": 0.9 if event.get("fatalities", 0) > 0 else 0.5,
                "description": f"ACLED Alert: {event.get('notes')}",
                "raw_payload": event
            }]
        except Exception as e:
            logger.error(f"Geopolitical Ingestion Failed: {str(e)}")
            return []

    def fetch_live_port_congestion(self, mmsi: str = "366971570") -> List[Dict[str, Any]]:
        """
        Connects to MarineTraffic for real-time port analytics and vessel positions.
        """
        if not self.marinetraffic_key:
            logger.warning("No MarineTraffic key found. Using MOCK congestion data.")
            return [{
                "h3_index": "8829a1d749fffff", 
                "event_type": "PORT_CONGESTION",
                "source": "MarineTraffic-MOCK",
                "severity": 0.65,
                "description": "Port of LA/LB anchored vessel queue exceeds 40 ships.",
                "raw_payload": {"anchored_vessels": 42}
            }]

        try:
            url = f"https://services.marinetraffic.com/api/exportvessel/v:5/{self.marinetraffic_key}/mmsi:{mmsi}/protocol:json"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            return [{
                "h3_index": "8829a1d749fffff", 
                "event_type": "PORT_CONGESTION",
                "source": "MarineTraffic-LIVE",
                "severity": 0.5,
                "description": f"Vessel Position: {data[0].get('SHIPNAME')} near destination.",
                "raw_payload": data[0] if data else {}
            }]
        except Exception as e:
            logger.error(f"MarineTraffic Ingestion Failed: {str(e)}")
            return []

    def execute_ingestion_cycle(self):
        """
        The main job loop. Fetches data, normalizes, and commits to DB.
        """
        all_events = []
        all_events.extend(self.fetch_live_weather_events())
        all_events.extend(self.fetch_live_geopolitical_events())
        all_events.extend(self.fetch_live_port_congestion())

        processed_count = 0
        for event in all_events:
            db_event = ExternalSpatialEvent(
                h3_index=event["h3_index"],
                event_type=event["event_type"],
                source_api=event["source"],
                severity_score=event["severity"],
                description=event["description"][:255], # Ensure char limit
                raw_payload=event["raw_payload"],
                is_active=True
            )
            self.db.add(db_event)
            processed_count += 1
            
        self.db.commit()
        logger.info(f"Ingestion Cycle Complete. {processed_count} spatial events stored.")
        return processed_count

# --- Quick Test Execution ---
if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use SQLite for rapid local testing of the ingestion script
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    ingester = ExternalApiIngester(db)
    count = ingester.execute_ingestion_cycle()
    print(f"Successfully processed and stored {count} external events in the database.")
