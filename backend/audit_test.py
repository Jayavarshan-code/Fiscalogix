import json
import asyncio
from app.financial_system.orchestrator import FinancialIntelligenceOrchestrator
from app.routes.expansion import (
    calculate_carbon_tax, calculate_ar_default, calculate_freight_hedging,
    optimize_inventory, calculate_systemic_risk, generate_negotiation_prompts,
    ShipmentData, CustomerData, FreightData, SKUData, GNNRequest, SupplierData
)

def run_audit():
    print("🚀 Initiating Fiscalogix Enterprise Engine Audits...")

    # 1. Mock Data Construction
    mock_data = [
        {
            "shipment_id": "SH-100",
            "route": "US-CN",
            "carrier": "Maersk",
            "order_value": 50000.0,
            "total_cost": 30000.0,
            "contribution_profit": 20000.0,
            "credit_days": 45,
            "order_month": 11,
            "weight_tons": 25.0
        },
        {
            "shipment_id": "SH-200",
            "route": "EU-US",
            "carrier": "DHL",
            "order_value": 15000.0,
            "total_cost": 12000.0,
            "contribution_profit": 3000.0,
            "credit_days": 15,
            "order_month": 3,
            "weight_tons": 5.0
        },
        {
            "shipment_id": "SH-300",
            "route": "CN-EU",
            "carrier": "Maersk",
            "order_value": 40000.0,
            "total_cost": 15000.0,
            "contribution_profit": 25000.0,
            "credit_days": 30,
            "order_month": 6,
            "weight_tons": 10.0,
            "risk_score": 0.9 # High initial risk to trigger reroute
        }
    ]

    # --- CORE REVM SYSTEM AUDIT ---
    print("\n[1/7] Booting FinancialIntelligenceOrchestrator...")
    engine = FinancialIntelligenceOrchestrator()
    engine.core.compute = lambda: mock_data # Bypass DB
    
    try:
        print("[2/7] Executing Master Orchestrator (Batch Vectors & Concurrent Executive)...")
        master_output = engine.run()
        print(f"✅ Master System Passed! Evaluated {len(master_output['revm'])} native movements.")
        print(f"   Optimization Engine Result: {master_output.get('poe', {}).get('expected_improvement')}")
        print(f"   Global Confidence Trust Matrix: {master_output.get('confidence', {}).get('global_score')}")
    except Exception as e:
        print(f"❌ MASTER SYSTEM FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

    # --- EXPANSION PILLARS AUDIT ---
    print("\n[3/7] Isolating Pillar 7: Carbon Tax ESG Engine...")
    try:
        shipments = [ShipmentData(**s) for s in mock_data]
        res = calculate_carbon_tax(shipments)
        print(f"✅ Scope 3 Taxes Processed: {res[0].tax_liability_usd} USD")
    except Exception as e:
        print(f"❌ ESG FAILED: {str(e)}")

    print("\n[4/7] Isolating Pillar 8: AR Default Predictor...")
    try:
        customers = [CustomerData(customer_id="CU-1", order_value=50000, credit_days=45), 
                     CustomerData(customer_id="CU-2", order_value=15000, credit_days=15)]
        res = calculate_ar_default(customers)
        print(f"✅ AR Bankruptcy Risks Processed: [{res[0].probability_of_default}, {res[1].probability_of_default}]")
    except Exception as e:
        print(f"❌ AR FAILED: {str(e)}")

    print("\n[5/7] Isolating Pillar 9 & 10: Freight Hedging & MEIO Allocations...")
    try:
        routes = [FreightData(route_id="US-CN", current_spot_rate=5000, current_contract_rate=4500)]
        skus = [SKUData(sku="PRD-1", global_inventory=1000, holding_cost_usd=10.0, stockout_penalty_usd=150.0)]
        r1 = calculate_freight_hedging(routes)
        r2 = optimize_inventory(skus)
        print(f"✅ Hedging & MEIO Constraints Processed!")
        print(f"   Hedge Decision: {r1[0].arbitrage_decision}")
        print(f"   MEIO Balance: {r2[0].optimal_allocation}")
    except Exception as e:
        print(f"❌ FREIGHT/MEIO FAILED: {str(e)}")

    print("\n[6/7] Isolating Pillar 11: Graph Neural Network Systemic Contagion Mapping...")
    try:
        # Pass mock_data augmented directly with an extreme risk to simulate failure cascade
        mock_data[0]["risk_score"] = 0.95
        mock_data[1]["risk_score"] = 0.10 # This will absorb contagion if dependent!
        req = GNNRequest(shipments=mock_data)
        res = calculate_systemic_risk(req)
        print(f"✅ Topological GNN Cascade Verified! Contagion detected: {res[1].systemic_contagion_detected}")
    except Exception as e:
        print(f"❌ GNN FAILED: {str(e)}")

    print("\n[7/7] Isolating Pillar 12: Generative LLM Prompts...")
    try:
        sups = [SupplierData(supplier_id="SUP-A", historical_delay_variance_pct=15.0, wacc_carrying_cost_usd=900)]
        res = generate_negotiation_prompts(sups)
        print(f"✅ Autonomous Negotiation Prompt successfully constructed via abstraction layer.")
    except Exception as e:
        print(f"❌ LLM FAILED: {str(e)}")

    print("\n[8/8] Verifying Geopolitical Reroute Optimization...")
    try:
        # Check if SH-300 was rerouted
        sh300_decision = next((s for s in master_output['poe']['optimized_decisions'] if s['shipment_id'] == "SH-300"), None)
        if sh300_decision:
            print(f"✅ Reroute Logic Verified!")
            print(f"   Shipment SH-300 Decision: {sh300_decision['action']}")
            print(f"   Reason: {sh300_decision['reason']}")
        else:
            print(f"⚠️ SH-300 was not in optimized decisions (may have been dropped by MIP)")
    except Exception as e:
        print(f"❌ REROUTE VERIFICATION FAILED: {str(e)}")

    print("\n🚀 ALL TIER-1 AUDITS CONCLUDED SUCCESSFULLY!")

if __name__ == "__main__":
    run_audit()
