from app.financial_system.cashflow.event_generator import CashEventGenerator
from app.financial_system.cashflow.timeline_builder import TimelineBuilder
from app.financial_system.cashflow.shock_detector import ShockDetector
from app.financial_system.cashflow.root_cause_engine import RootCauseEngine
from app.financial_system.cashflow.decision_support import CashflowDecisionSupport

class CashflowPredictorOrchestrator:
    def __init__(self):
        self.generator = CashEventGenerator()
        self.builder = TimelineBuilder()
        self.detector = ShockDetector()
        self.root_cause = RootCauseEngine()
        self.decision = CashflowDecisionSupport()
        
    def run(self, enriched_records, starting_cash=50000.0):
        # 1. Transform enriched logic into raw events
        events = self.generator.compute(enriched_records)
        # 2. Build mathematical timeline
        timeline, metrics = self.builder.build(events, starting_cash)
        # 3. Predict liquidity shocks
        shocks = self.detector.detect(timeline)
        # 4. Map back to shipments
        root_causes = self.root_cause.analyze(shocks, events)
        # 5. Provide Supply Chain Actions
        recommendations = self.decision.compute(shocks, root_causes)
        
        ending_cash = timeline[-1]["cumulative_cash"] if timeline else starting_cash
        
        return {
            "cash_position": {
                "starting_cash": starting_cash, 
                "ending_cash": ending_cash
            },
            "metrics": metrics,
            "timeline": timeline,
            "shocks": shocks,
            "root_causes": root_causes,
            "recommendations": recommendations
        }
