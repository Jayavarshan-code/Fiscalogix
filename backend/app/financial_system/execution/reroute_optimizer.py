import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.external_events import ExternalSpatialEvent

logger = logging.getLogger(__name__)


class RerouteOptimizer:
    """
    The Intelligence Engine for Profit-Optimized Rerouting.

    Instead of relying on generalized p44 "Time" reroutes, this engine:
    1. Queries the sovereign `external_spatial_events` table for live risks.
    2. Queries the `port_registry` table for real demurrage & storage rates.
    3. Computes the financial impact of each route option and recommends the
       cheapest path.

    FIX (PortRegistry): Replaced hardcoded Python dict for port penalties with
    live DB lookup. Previously:
      self.port_penalties = {"USMIA": {"demurrage_per_day": 50000, ...}}
    This was invisible to CFOs, couldn't be updated without a code deploy, and
    silently broke for any port not in the dict.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self._port_cache: Optional[Dict] = None  # Local request-level cache

    def _get_port_data(self) -> Dict[str, Dict]:
        """
        Loads port registry from DB with lazy request-level caching.
        Returns: { port_id: { demurrage_per_day, storage_per_day, port_name, h3_index } }
        """
        if self._port_cache is not None:
            return self._port_cache

        try:
            from setup_db import PortRegistry
            ports = self.db.query(PortRegistry).filter(PortRegistry.is_active == True).all()
            self._port_cache = {
                p.port_id: {
                    "name":              p.port_name,
                    "demurrage_per_day": p.demurrage_per_day or 0.0,
                    "storage_per_day":   p.storage_per_day or 0.0,
                    "h3_index":          p.h3_index,
                    "peak_risk_months":  p.peak_risk_months or [],
                }
                for p in ports
            }
            logger.info(f"RerouteOptimizer: loaded {len(self._port_cache)} ports from registry.")
        except Exception as e:
            logger.warning(
                f"RerouteOptimizer: failed to load port registry — {type(e).__name__}: {e}. "
                "Falling back to hardcoded defaults."
            )
            # Graceful hardcoded fallback (same values as before, but now explicit)
            self._port_cache = {
                "USMIA": {"name": "Port of Miami",    "demurrage_per_day": 50000, "storage_per_day": 200, "h3_index": "8844c1a3fffffff", "peak_risk_months": [11, 12, 1]},
                "USSAV": {"name": "Port of Savannah", "demurrage_per_day": 25000, "storage_per_day": 150, "h3_index": "8844c0a3fffffff", "peak_risk_months": [8, 9]},
                "USHOU": {"name": "Port of Houston",  "demurrage_per_day": 40000, "storage_per_day": 175, "h3_index": "8844c503fffffff", "peak_risk_months": [9, 10]},
            }

        return self._port_cache

    def fetch_active_risks(self, target_h3_indices: List[str]) -> List[ExternalSpatialEvent]:
        """
        Queries the database for live environmental/geopolitical shocks affecting potential routes.
        """
        if not target_h3_indices:
            return []
        return self.db.query(ExternalSpatialEvent).filter(
            ExternalSpatialEvent.is_active == True,
            ExternalSpatialEvent.h3_index.in_(target_h3_indices)
        ).all()

    def calculate_profit_optimized_reroute(
        self,
        current_vessel_h3: str,
        destination_port: str,
        route_options: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Calculates the financial impact of maintaining course vs rerouting,
        using live sovereign database alerts and DB-loaded port rates.

        Args:
            current_vessel_h3: H3 index of current vessel position.
            destination_port:  Primary target port ID (e.g. 'USMIA').
            route_options:     Optional override for route alternatives. If None,
                               uses primary vs nearest alternate port.
        """
        logger.info(f"RerouteOptimizer: analyzing options for vessel → {destination_port}")

        port_data = self._get_port_data()

        # Default route options: primary target + first available alternate
        if route_options is None:
            available_ports = [pid for pid in port_data if pid != destination_port]
            alt_port = available_ports[0] if available_ports else destination_port
            route_options = {
                "Route_A_Primary": {
                    "h3_zone":          port_data.get(destination_port, {}).get("h3_index", current_vessel_h3),
                    "target_port":      destination_port,
                    "extra_transit_days": 0,
                },
                "Route_B_Alternate": {
                    "h3_zone":          port_data.get(alt_port, {}).get("h3_index", current_vessel_h3),
                    "target_port":      alt_port,
                    "extra_transit_days": 2,
                },
            }

        # Fetch live sovereign risks from DB for all candidate H3 zones
        h3_targets = [r["h3_zone"] for r in route_options.values() if r.get("h3_zone")]
        live_risks = self.fetch_active_risks(h3_targets)
        risk_map = {risk.h3_index: risk for risk in live_risks}

        import datetime
        current_month = datetime.datetime.utcnow().month

        decisions = []
        for route_name, details in route_options.items():
            port_id    = details["target_port"]
            port_info  = port_data.get(port_id, {})

            if not port_info:
                logger.warning(f"RerouteOptimizer: port {port_id} not in registry, skipping.")
                continue

            h3_risk = risk_map.get(details.get("h3_zone", ""))

            # Weather delay estimate from sovereign event severity
            weather_delay_hrs = 0
            if h3_risk:
                if h3_risk.event_type == "WEATHER":
                    weather_delay_hrs = int(48 * h3_risk.severity_score)
                elif h3_risk.event_type == "PORT_CONGESTION":
                    weather_delay_hrs = int(24 * h3_risk.severity_score)
                elif h3_risk.event_type == "GEOPOLITICAL":
                    weather_delay_hrs = int(72 * h3_risk.severity_score)

            # Seasonal congestion surcharge
            peak_surcharge = 1.25 if current_month in port_info.get("peak_risk_months", []) else 1.0

            total_delay_days   = details["extra_transit_days"] + (weather_delay_hrs / 24)
            demurrage_cost     = total_delay_days * port_info["demurrage_per_day"] * peak_surcharge
            storage_cost       = total_delay_days * port_info["storage_per_day"]
            total_financial_impact = demurrage_cost + storage_cost

            decisions.append({
                "route_name":             route_name,
                "target_port":            port_info["name"],
                "target_port_id":         port_id,
                "environmental_delay_hrs": weather_delay_hrs,
                "extra_transit_days":     details["extra_transit_days"],
                "total_delay_days":       round(total_delay_days, 2),
                "demurrage_cost_usd":     round(demurrage_cost, 2),
                "storage_cost_usd":       round(storage_cost, 2),
                "total_financial_impact_usd": round(total_financial_impact, 2),
                "risk_factor_detected":   h3_risk.event_type if h3_risk else "CLEAR",
                "seasonal_surcharge_applied": peak_surcharge > 1.0,
            })

        if not decisions:
            return {"insight": "NO_VIABLE_ROUTES", "recommendation": destination_port}

        # Rank by total financial impact — lowest cost wins
        decisions.sort(key=lambda x: x["total_financial_impact_usd"])
        best = decisions[0]
        worst = decisions[-1]
        savings = worst["total_financial_impact_usd"] - best["total_financial_impact_usd"]

        return {
            "insight":          "PROFIT_OPTIMIZED_REROUTE",
            "recommendation":   best["target_port"],
            "recommendation_id": best["target_port_id"],
            "reasoning":        (
                f"Route via {best['target_port']} avoids {best['risk_factor_detected']} risk. "
                f"Saves ${savings:,.0f} vs worst alternative."
            ),
            "projected_savings_usd":     round(savings, 2),
            "best_route_total_cost_usd": best["total_financial_impact_usd"],
            "all_options_analyzed":       decisions,
        }
