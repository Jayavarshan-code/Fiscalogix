import asyncio
from app.financial_system.orchestrator import FinancialIntelligenceOrchestrator
from app.connectors.netsuite import NetSuiteConnector
from app.connectors.sap import SAPS4HanaConnector

def test_erp_connectors():
    print("--- Testing ERP Connectors ---")
    ns = NetSuiteConnector()
    ns.authenticate()
    print(ns.fetch_orders("tenant_A"))
    
    sap = SAPS4HanaConnector()
    sap.authenticate()
    print(sap.fetch_inventory("tenant_B"))
    print("\n")

def test_financial_impact():
    print("--- Testing Financial Impact Engine & Orchestrator ---")
    engine = FinancialIntelligenceOrchestrator()
    # Assuming there's some data in default_tenant, or it returns empty {} safely
    result = engine.run(tenant_id="default_tenant")
    if not result:
        print("No data found for default_tenant, but orchestrator ran successfully.")
    else:
        impact = result.get("financial_impact", {})
        print(f"Financial Impact Narrative: {impact.get('cfo_narrative')}")
        print(f"Risk Drivers (from first REVM): {result.get('revm')[0].get('risk_drivers')}")
    print("\n")

if __name__ == "__main__":
    test_erp_connectors()
    test_financial_impact()
    print("✅ All SaaS gap validation tests complete.")
