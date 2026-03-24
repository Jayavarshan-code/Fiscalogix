import copy

class CandidateActionGenerator:
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
            
        # Action D: Reroute (Carrier swap, modifies base systemic risk profile)
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
