import copy

class ScenarioSimulationEngine:
    """
    Clones base reality to run parallel "What-If" decision models comparing
    delayed shipments or dropped demand against standard REVM/Cashflow outputs.
    """
    def __init__(self, risk_engine, time_model, future_model, cashflow_orchestrator):
        self.risk = risk_engine
        self.time = time_model
        self.future = future_model
        self.cashflow = cashflow_orchestrator
        
    def simulate(self, base_records, scenario_name, delay_shift=0, demand_shift_pct=0.0):
        cloned_records = copy.deepcopy(base_records)
        base_revm = sum(r["revm"] for r in base_records)
        
        for r in cloned_records:
            # Shift core variables
            r["delay_days"] = r.get("delay_days", 0) + delay_shift
            r["predicted_demand"] = r.get("predicted_demand", 0) * (1.0 + demand_shift_pct)
            
            # Re-run strict REVM layer penalty computations 
            risk_output = self.risk.compute(r, r["predicted_delay"])
            r["risk_score"] = risk_output["score"]
            risk_penalty = r["risk_score"] * r["order_value"]
            
            time_cost = self.time.compute(r)
            future_cost = self.future.compute(r, r["predicted_delay"], r["predicted_demand"])
            
            r["revm"] = r["contribution_profit"] - risk_penalty - time_cost - future_cost
            
        # Re-run Cashflow Baseline to detect exactly how significantly Peak Deficits fracture
        new_cashflow = self.cashflow.run(cloned_records)
        scenario_revm = sum(r["revm"] for r in cloned_records)
        
        revm_change = scenario_revm - base_revm
        
        return {
            "scenario": scenario_name,
            "impact": {
                "revm_change": round(revm_change, 2),
                "peak_deficit": new_cashflow["metrics"]["peak_deficit"]
            }
        }
