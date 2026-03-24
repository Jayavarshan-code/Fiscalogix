import copy

class CandidateActionGenerator:
    def __init__(self, route_optimizer=None, risk_engine=None):
        self.route_optimizer = route_optimizer
        self.risk_engine = risk_engine

    def generate(self, row):
        """
        Generates actionable operational branches (Ship, Delay, Expedite, Cancel) for a specific shipment.
        """
        actions = []
        
        # Action A: Baseline (Status Quo)
        baseline = copy.deepcopy(row)
        baseline["action_name"] = "SHIP_NOW"
        actions.append(baseline)
        
        # Action B: Delay (Save cash immediately, but risk catastrophic future CLV penalties)
        if row.get("delay_days", 0) < 10:
            delayed = copy.deepcopy(row)
            delayed["action_name"] = "DELAY_3_DAYS"
            delayed["total_cost"] = delayed.get("total_cost", 0) * 0.95 # Save 5% upfront capital
            delayed["delay_days"] = delayed.get("delay_days", 0) + 3
            actions.append(delayed)
            
        # Action C: Expedite (Capital intensive upfront, structurally saves REVM from churn)
        if row.get("total_cost", 0) > 0:
            expedite = copy.deepcopy(row)
            expedite["action_name"] = "EXPEDITE"
            expedite["total_cost"] = expedite.get("total_cost", 0) * 1.25 # Cost spikes 25%
            expedite["delay_days"] = max(0, expedite.get("delay_days", 0) - 5)
            actions.append(expedite)
            
        # Action D: Reroute (Optimized via Multimodal Engine)
        is_critical = row.get("is_critical", False)
        if self.route_optimizer:
            # Extract origin/dest from route string (e.g., "US-CN" -> "US", "CN")
            current_route = row.get("route", "UNKNOWN-UNKNOWN")
            parts = current_route.split("-")
            if len(parts) == 2:
                opt_res = self.route_optimizer.find_best_route(
                    parts[0], parts[1], 
                    is_critical=is_critical, 
                    risk_engine=self.risk_engine
                )
                if opt_res:
                    reroute = copy.deepcopy(row)
                    # Tactical branding based on Goods Nature
                    reroute["action_name"] = "SAFE_TRUCK_REROUTE" if is_critical else "REROUTE_OPTIMIZED"
                    reroute["route"] = opt_res["route"]
                    reroute["total_cost"] = opt_res["operational_cost_usd"]
                    reroute["delay_days"] = round(opt_res["total_duration_hours"] / 24.0, 1)
                    reroute["reason"] = f"Multimodal Opt ({'Critical' if is_critical else 'Standard'}): {opt_res['total_distance_km']}km via {opt_res['nodes'][1]}"
                    actions.append(reroute)
        else:
            # Fallback to simple reroute if no engine provided
            reroute = copy.deepcopy(row)
            reroute["action_name"] = "REROUTE"
            reroute["carrier"] = "PremiumCarrier"
            reroute["total_cost"] = reroute.get("total_cost", 0) * 1.10
            reroute["delay_days"] = max(0, reroute.get("delay_days", 0) - 2)
            actions.append(reroute)
        
        # Action E: Cancel (Nukes everything)
        cancel = copy.deepcopy(row)
        cancel["action_name"] = "CANCEL"
        cancel["order_value"] = 0
        cancel["total_cost"] = 0
        cancel["contribution_profit"] = 0
        actions.append(cancel)
        
        return actions
