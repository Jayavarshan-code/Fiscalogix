from app.financial_system.orchestrator import FinancialIntelligenceOrchestrator
from app.financial_system.sla_model import SLAPenaltyModel

def run_verification():
    """
    Verification Plan for SLA and Pipeline Costs.
    Expectation: A $100,000 order value, delayed 3 days on a strict (30_days target) customer.
    SLA penalty should be exactly $9,000 (3 days * 3%).
    """
    print("--- Running Financial Mathematics Verification ---")
    row = {
        "shipment_id": 999,
        "order_value": 100000.0,
        "total_cost": 50000.0,
        "credit_days": 30, # Strict SLA
        "delay_days": 3,
        "wacc": 0.08,
        "contribution_profit": 35000.0, # Pre-risk profit
    }
    
    sla = SLAPenaltyModel()
    penalty = sla.compute(row, predicted_delay=3)
    
    print(f"Mathematical Proof:")
    print(f"Order Value: ${row['order_value']:,.2f}")
    print(f"Delay: 3 days")
    print(f"Credit Target: 30 days (Strict SLA Penalty @ 3%/day)")
    print(f"SLA Penalty Computed: ${penalty:,.2f}")
    
    assert penalty == 9000.0, "SLA Penalty Calculation Failed. Expected 9000.0"
    print("✓ SLA Penalty Mathematics Verified.")
    
    # We could also mock the whole orchestrator if needed, but proving the individual engine is cleaner
    
if __name__ == "__main__":
    run_verification()
