import concurrent.futures
from app.financial_system.engine import FinancialCoreEngine
from app.financial_system.delay_model import DelayPredictionModel
from app.financial_system.demand_model import DemandPredictionModel
from app.financial_system.risk_engine import RiskEngine
from app.financial_system.time_model import TimeValueModel
from app.financial_system.future_model import FutureImpactModel
from app.financial_system.fx_model import FXRiskModel
from app.financial_system.sla_model import SLAPenaltyModel
from app.financial_system.aggregator import FinancialAggregator
from app.financial_system.audit_logger import AuditLogger
from app.financial_system.decision_engine import DecisionEngine
from app.financial_system.cashflow.orchestrator import CashflowPredictorOrchestrator

from app.financial_system.executive.confidence_engine import ConfidenceTrustEngine
from app.financial_system.executive.scenario_engine import ScenarioSimulationEngine
from app.financial_system.executive.monte_carlo import MonteCarloEngine
from app.financial_system.executive.buffer_engine import CashBufferEngine
from app.financial_system.executive.liquidity_engine import LiquidityScoreEngine
from app.financial_system.executive.impact_engine import ImpactEngine
from app.financial_system.optimization.orchestrator import ProfitOptimizationOrchestrator

class FinancialIntelligenceOrchestrator:

    def __init__(self):
        self.core = FinancialCoreEngine()
        self.delay_model = DelayPredictionModel()
        self.demand_model = DemandPredictionModel()
        self.risk = RiskEngine()
        self.time = TimeValueModel()
        self.future = FutureImpactModel()
        self.fx = FXRiskModel()
        self.sla = SLAPenaltyModel()
        self.aggregator = FinancialAggregator()
        self.audit = AuditLogger()
        self.decision = DecisionEngine()
        self.cashflow = CashflowPredictorOrchestrator()
        
        self.confidence = ConfidenceTrustEngine()
        self.scenario = ScenarioSimulationEngine(self.risk, self.time, self.future, self.cashflow)
        self.monte_carlo = MonteCarloEngine()
        self.buffer = CashBufferEngine()
        self.liquidity = LiquidityScoreEngine()
        self.impact = ImpactEngine()
        
        self.poe = ProfitOptimizationOrchestrator(self.risk, self.time, self.future)

    def run(self, tenant_id: str = "default_tenant"):
        data = self.core.compute(tenant_id=tenant_id)
        if not data:
            return {}

        # --- Phase 1: Massive C++ Pandas Vectorization for ML inference ---
        predicted_delays_array = self.delay_model.compute_batch(data)
        predicted_demands_array = self.demand_model.compute_batch(data)
        risk_outputs_array = self.risk.compute_batch(data, predicted_delays_array)
        fx_outputs_array = self.fx.compute_batch(data, predicted_delays_array)
        sla_outputs_array = self.sla.compute_batch(data, predicted_delays_array)
        
        enriched = []
        # --- Phase 2: Chronological Synthesis Iteration ---
        for i, row in enumerate(data):
            contribution_profit = row.get("contribution_profit", 0.0)
            order_value = row.get("order_value", 0.0)

            predicted_delay = predicted_delays_array[i]
            predicted_demand = predicted_demands_array[i]
            
            risk_score = risk_outputs_array[i]["score"]
            risk_confidence = risk_outputs_array[i]["confidence"]
            risk_drivers = risk_outputs_array[i].get("drivers", [])
            risk_penalty = risk_score * order_value

            time_cost = self.time.compute(row, predicted_delay)
            future_cost = self.future.compute(row, predicted_delay, predicted_demand)
            fx_cost = fx_outputs_array[i]
            sla_penalty = sla_outputs_array[i]

            # The Ultimate Algebraic Financial Yield (ReVM)
            # True Enterprise accounting: Accounts for Opportunity Cost, Physical Pipeline, FX Erosion, and Strict Contract SLA fines.
            revm = contribution_profit - risk_penalty - time_cost - future_cost - fx_cost - sla_penalty

            final_row = {
                **row,
                "predicted_delay": predicted_delay,
                "predicted_demand": predicted_demand,
                "risk_score": risk_score,
                "risk_confidence": risk_confidence,
                "risk_drivers": risk_drivers,
                "risk_penalty": risk_penalty,
                "time_cost": time_cost,
                "future_cost": future_cost,
                "fx_cost": fx_cost,
                "sla_penalty": sla_penalty,
                "revm": revm
            }
            
            decision = self.decision.compute(final_row)
            final_row["decision"] = decision
            enriched.append(final_row)

        try:
            self.audit.log_batch(enriched)
        except Exception:
            pass 

        # --- Phase 3: Aggregation ---
        summary = self.aggregator.summarize(enriched)
        cashflow_report = self.cashflow.run(enriched)
        
        timeline = cashflow_report["timeline"]
        shocks = cashflow_report["shocks"]
        cash_metrics = cashflow_report["metrics"]
        ending_cash = cashflow_report.get("cash_position", {}).get("ending_cash", 50000.0)
        
        # --- Phase 4: Structural Multiprocessing (Concurrent Executive Logic) ---
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_confidence = executor.submit(self.confidence.compute, enriched, shocks)
            future_scen_1 = executor.submit(self.scenario.simulate, enriched, "delay +2 days", delay_shift=2)
            future_scen_2 = executor.submit(self.scenario.simulate, enriched, "demand drop -5%", demand_shift_pct=-0.05)
            
            # Submits exactly 1,000 algorithmic cycles into a separate processing thread mapping Probabilistic VaR limits
            future_monte = executor.submit(self.monte_carlo.simulate_var, enriched, 1000)
            
            future_liquidity = executor.submit(self.liquidity.compute, ending_cash, timeline, shocks, enriched)
            future_poe = executor.submit(self.poe.optimize, enriched, ending_cash)

            # Synchronous barrier resolving thread futures
            global_confidence = future_confidence.result()
            scenarios = [future_scen_1.result(), future_scen_2.result()]
            monte_carlo_var = future_monte.result()
            liquidity_score = future_liquidity.result()
            optimization_payload = future_poe.result()
        
        buffer_rec = self.buffer.compute(cash_metrics["peak_deficit"], shocks, global_confidence)

        impact_metrics = self.impact.compute(enriched, optimization_payload, monte_carlo_var)

        return {
            "summary": summary,
            "revm": enriched,
            "cashflow_predictor": cashflow_report,
            "shocks": shocks, 
            "poe": optimization_payload,
            "confidence": {"global_score": global_confidence},
            "scenario_analysis": scenarios,
            "stochastic_var": monte_carlo_var,
            "buffer": buffer_rec,
            "liquidity": {"liquidity_score": liquidity_score},
            "financial_impact": impact_metrics
        }
