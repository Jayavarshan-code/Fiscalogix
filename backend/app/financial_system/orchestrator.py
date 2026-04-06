import logging
from typing import List, Dict, Any
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
from app.financial_system.optimization.route_optimizer import GeopoliticalRouteOptimizer
from app.financial_system.ai_mapper import AIFieldMapper

class FinancialIntelligenceOrchestrator:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
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

        # NEW: ReVM Snapshot persistence for historical trend analytics
        from app.financial_system.revm_snapshot_logger import RevmSnapshotLogger
        self.revm_snapshot = RevmSnapshotLogger()
        
        self.confidence = ConfidenceTrustEngine()
        self.scenario = ScenarioSimulationEngine(self.risk, self.time, self.future, self.cashflow)
        self.monte_carlo = MonteCarloEngine()
        self.buffer = CashBufferEngine()
        self.liquidity = LiquidityScoreEngine()
        self.impact = ImpactEngine()
        
        # Geopolitical Route Optimization Engine (High-Fidelity Rerouting)
        self.route_optimizer = GeopoliticalRouteOptimizer(risk_aversion_beta=3.5)
        self._seed_geopolitical_graph()

        self.poe = ProfitOptimizationOrchestrator(self.risk, self.time, self.future, route_optimizer=self.route_optimizer)

    def _seed_geopolitical_graph(self):
        """
        Seeds the global supply chain topology for Dijkstra-based pathfinding.
        """
        # Global Ports & Transit Hubs
        self.route_optimizer.add_node("CN", territory_type="Friendly")
        self.route_optimizer.add_node("SG", territory_type="Friendly")
        self.route_optimizer.add_node("ADEN", territory_type="Enemy") # Conflict Risk
        self.route_optimizer.add_node("SUEZ", territory_type="Neutral")
        self.route_optimizer.add_node("EU", territory_type="Friendly")
        self.route_optimizer.add_node("CAPE", territory_type="Friendly") # Alternative
        self.route_optimizer.add_node("US", territory_type="Friendly")
        
        # Known Competitive Routes
        # Route 1: Asia to Europe (Suez)
        self.route_optimizer.add_edge("CN", "SG", 2600, 1.1, 45, 500)
        self.route_optimizer.add_edge("SG", "ADEN", 6200, 1.1, 45, 1000)
        self.route_optimizer.add_edge("ADEN", "SUEZ", 2400, 1.1, 45, 4500)
        self.route_optimizer.add_edge("SUEZ", "EU", 5800, 1.1, 45, 2000)
        
        # Route 2: Asia to Europe (Cape of Good Hope - Long but safe)
        self.route_optimizer.add_edge("SG", "CAPE", 11500, 1.1, 45, 1200)
        self.route_optimizer.add_edge("CAPE", "EU", 11200, 1.1, 45, 1200)

        # Route 3: Trans-Pacific
        self.route_optimizer.add_edge("CN", "US", 11000, 1.4, 60, 3000, transport_mode="Ocean")
        
        # --- Domestic / Inland Logistics Layers ---
        self.route_optimizer.add_node("HUB_A", territory_type="Friendly") # Truck Hub
        self.route_optimizer.add_node("HUB_B", territory_type="Friendly") # Rail Hub
        self.route_optimizer.add_node("RETAILER_X", territory_type="Friendly") # Final Destination
        
        # Domestic Edges (Trucking vs Rail)
        # Link 1: EU Port to Hub A (Truck - FAST & CHEAP - Dist: 500km)
        self.route_optimizer.add_edge("EU", "HUB_A", 500, 1.0, 30, 50, transport_mode="Truck")
        # Link 2: EU Port to Hub B (Rail - STABLE - Dist: 600km)
        self.route_optimizer.add_edge("EU", "HUB_B", 600, 2.0, 60, 500, transport_mode="Rail")
        
        # Last Mile
        self.route_optimizer.add_edge("HUB_A", "RETAILER_X", 100, 1.0, 30, 20, transport_mode="Truck")
        self.route_optimizer.add_edge("HUB_B", "RETAILER_X", 150, 1.0, 30, 20, transport_mode="Truck")
        
        # ACTIVE SCENARIO: Labor Strike on Primary Trucking Lane (EU -> HUB_A)
        self.route_optimizer.set_strike("EU", "HUB_A", active=True)
        
        # --- Tech Giant AI Sync ---
        # Inject the physical graph topology into the Risk Engine for contagion modeling
        self.risk.set_contagion_context(self.route_optimizer.graph)

    def run(self, tenant_id: str = "default_tenant"):
        raw_data = self.core.compute(tenant_id=tenant_id)
        if not raw_data:
            return {}

        # --- Fix C Integration: Taxonomical Normalization ---
        # Cleans raw ERP strings (e.g., "Pharma-Cold" -> "pharmaceutical") 
        # before any financial engine or ML model touches the data.
        data = [AIFieldMapper.normalize_row_taxonomy(row) for row in raw_data]

        # --- Phase 1: Massive C++ Pandas Vectorization for ML inference ---
        predicted_delays_array = self.delay_model.compute_batch(data)
        predicted_demands_array = self.demand_model.compute_batch(data)
        risk_outputs_array = self.risk.compute_batch(data, predicted_delays_array)
        fx_outputs_array = self.fx.compute_batch(data, predicted_delays_array)
        sla_outputs_array = self.sla.compute_batch(data, predicted_delays_array)
        
        # --- Phase 1.5: Sync GNN Contagion Signals into Route Optimizer ---
        # Map the batch risk outputs into the topological graph
        gnn_mapping = {data[i].get("shipment_id"): risk_outputs_array[i]["score"] for i in range(len(data))}
        # Also map geographical identifiers if present
        for i, row in enumerate(data):
            route_id = row.get("route", "").split("-")[0] # Simple heuristic
            if route_id:
                gnn_mapping[route_id] = risk_outputs_array[i]["score"]
        
        self.logger.info("[Phase 1.5] Syncing GNN Risks...")
        self.route_optimizer.sync_gnn_risk(gnn_mapping)

        enriched = []
        # --- Phase 2: Chronological Synthesis Iteration ---
        self.logger.info(f"[Phase 2] Synthesizing {len(data)} records...")
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
        except Exception as e:
            # Audit log failures must NEVER be swallowed silently.
            # If this fails, it means DecisionLog writes are broken — a critical
            # compliance gap. Log at ERROR so it surfaces in production observability.
            import logging
            logging.getLogger(__name__).error(
                f"Orchestrator: AuditLogger.log_batch failed — {type(e).__name__}: {e}",
                exc_info=True
            )

        # Persist ReVM snapshots for historical trend charting and investor demo analytics.
        # Must run after Phase 2 synthesis so all cost components are populated on each row.
        try:
            self.revm_snapshot.save_batch(enriched, tenant_id)
        except Exception as e:
            self.logger.error(
                f"Orchestrator: RevmSnapshotLogger.save_batch failed — {type(e).__name__}: {e}",
                exc_info=True
            )

        # --- Phase 3: Aggregation ---
        summary = self.aggregator.summarize(enriched)
        cashflow_report = self.cashflow.run(enriched)
        
        timeline = cashflow_report["timeline"]
        shocks = cashflow_report["shocks"]
        cash_metrics = cashflow_report["metrics"]
        ending_cash = cashflow_report.get("cash_position", {}).get("ending_cash", 50000.0)
        
        # --- Phase 4: Sequential Executive Logic (No Thread Thrashing) ---
        global_confidence = self.confidence.compute(enriched, shocks)
        scen_1 = self.scenario.simulate(enriched, "delay +2 days", delay_shift=2)
        scen_2 = self.scenario.simulate(enriched, "demand drop -5%", demand_shift_pct=-0.05)
        scenarios = [scen_1, scen_2]
        
        # Sequentially map Probabilistic VaR limits (1,000 algorithmic cycles)
        self.logger.info("[Phase 4.1] Running Monte Carlo...")
        monte_carlo_var = self.monte_carlo.simulate_var(enriched, 1000)
        
        self.logger.info("[Phase 4.2] Running Liquidity Optimization...")
        liquidity_score = self.liquidity.compute(ending_cash, timeline, shocks, enriched)
        self.logger.info("[Phase 4.3] Running POE Optimization...")
        optimization_payload = self.poe.optimize(enriched, ending_cash)
        
        buffer_rec = self.buffer.compute(cash_metrics["peak_deficit"], shocks, global_confidence)

        impact_metrics = self.impact.compute(enriched, optimization_payload, monte_carlo_var)

        # Step 1: Capture Every Decision (Evolving Intelligence)
        self._log_decisions(optimization_payload, tenant_id)

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

    def _log_decisions(self, optimized_payload: List[Dict[str, Any]], tenant_id: str = "default_tenant"):
        """
        Persists predicted decisions to the DecisionLog table.
        tenant_id is now passed through so no row gets a null tenant.
        """
        from setup_db import DecisionLog
        import uuid

        from app.Db.connections import SessionLocal
        self.logger.info(f"[Feedback Loop] Logging {len(optimized_payload)} decisions...")
        db = SessionLocal()
        try:
            entries = [
                DecisionLog(
                    decision_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    shipment_id=decision.get("shipment_id"),
                    route_selected=decision.get("action"),
                    predicted_efi=decision.get("expected_efi"),
                    confidence_score=decision.get("confidence_score"),
                    risk_posture=decision.get("risk_posture"),
                )
                for decision in optimized_payload
            ]
            db.bulk_save_objects(entries)
            db.commit()
        except Exception as e:
            db.rollback()
            self.logger.error(f"_log_decisions failed — {type(e).__name__}: {e}", exc_info=True)
        finally:
            db.close()
