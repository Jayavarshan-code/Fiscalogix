import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.external_events import ExternalSpatialEvent

logger = logging.getLogger(__name__)

class RerouteOptimizer:
    """
    The Intelligence Engine for Rerouting.
    Instead of relying on generalized p44 "Time" reroutes, this engine queries our 
    Sovereign Database for Weather/Geopolitical alerts and makes a "Profit-Optimized" decision.
    """
    def __init__(self, db_session: Session):
        self.db = db_session

        # Mock Carrier Contract Penalties (The Financial layer)
        self.port_penalties = {
            "USMIA": {"demurrage_per_day": 50000, "name": "Port of Miami"},
            "USSAV": {"demurrage_per_day": 25000, "name": "Port of Savannah"},
            "USHOU": {"demurrage_per_day": 40000, "name": "Port of Houston"}
        }

    def fetch_active_risks(self, target_h3_indices: List[str]) -> List[ExternalSpatialEvent]:
        """
        Queries the database for live environmental/geopolitical shocks affecting potential routes.
        """
        return self.db.query(ExternalSpatialEvent).filter(
            ExternalSpatialEvent.is_active == True,
            ExternalSpatialEvent.h3_index.in_(target_h3_indices)
        ).all()

    def calculate_profit_optimized_reroute(self, current_vessel_h3: str, destination_port: str) -> Dict[str, Any]:
        """
        Calculates the financial impact of maintaining course vs rerouting, 
        using live Sovereign database alerts.
        """
        logger.info(f"Analyzing reroute options for vessel approaching {destination_port}...")
        
        # MOCK route spatial grid for decision making
        route_options = {
            "Route_A_Primary": {"h3_zone": "8844c12bb1fffff", "target_port": "USMIA", "extra_transit_days": 0},
            "Route_B_Alt": {"h3_zone": "8844c12bb1faaaa", "target_port": "USSAV", "extra_transit_days": 2}
        }
        
        # Fetch Live Sovereign Risks from DB
        h3_targets = [r["h3_zone"] for r in route_options.values()]
        live_risks = self.fetch_active_risks(h3_targets)
        
        risk_map = {risk.h3_index: risk for risk in live_risks}

        decisions = []
        for route_name, details in route_options.items():
            port_cost = self.port_penalties.get(details["target_port"])
            h3_risk = risk_map.get(details["h3_zone"])
            
            # If a severe weather event exists on the route, assume significant delay
            weather_delay_hrs = 48 if (h3_risk and h3_risk.event_type == "WEATHER") else 0
            
            total_delay_days = details["extra_transit_days"] + (weather_delay_hrs / 24)
            financial_impact = total_delay_days * port_cost["demurrage_per_day"]
            
            decisions.append({
                "route_name": route_name,
                "target_port": port_cost["name"],
                "environmental_delay_hrs": weather_delay_hrs,
                "projected_penalty_inr": financial_impact,
                "risk_factor_detected": h3_risk.event_type if h3_risk else "CLEAR"
            })
            
        # Determine the cheapest option
        decisions.sort(key=lambda x: x["projected_penalty_inr"])
        best_choice = decisions[0]
        
        return {
            "insight": "PROFIT_OPTIMIZED_REROUTE",
            "recommendation": best_choice["target_port"],
            "reasoning": f"Avoids {best_choice['risk_factor_detected']} risk factors. "
                         f"Saves projected demurrage costs.",
            "financial_impact_inr": best_choice["projected_penalty_inr"],
            "all_options_analyzed": decisions
        }

# --- Quick Test Execution ---
if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.external_events import Base, ExternalSpatialEvent
    from datetime import datetime
    
    # Setup test DB
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Inject a live weather event (Simulating the output of the Ingester)
    hurricane = ExternalSpatialEvent(
        h3_index="8844c12bb1fffff", 
        event_type="WEATHER", 
        source_api="OpenWeatherMap", 
        severity_score=0.95,
        description="Category 4 Hurricane",
        is_active=True,
        detected_at=datetime.utcnow()
    )
    db.add(hurricane)
    db.commit()
    
    optimizer = RerouteOptimizer(db)
    result = optimizer.calculate_profit_optimized_reroute("CURRENT_H3", "USMIA")
    
    import json
    print(json.dumps(result, indent=2))
