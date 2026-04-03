import asyncio
import json
from backend.app.financial_system.metrics.efi_engine import UniversalEFIEngine
from backend.app.services.llm_gateway import LlmGateway
from backend.app.services.spatial_h3_service import SpatialH3Service
from backend.app.services.copilot_service import CopilotService

async def run_efi_sales_demo():
    print("🚀 FISCALOGIX: REAL-WORLD EFI DEMO (SALES-READY)")
    print("-" * 50)
    
    # 1. Initialize Services
    h3_service = SpatialH3Service()
    llm = LlmGateway()
    copilot = CopilotService(h3_service, llm)
    
    # 2. Define Scenario: Shanghai to Mundra (Delayed at Singapore)
    shipment_id = "SHIP-IN-99"
    current_lat, current_lon = 1.28, 103.85 # Singapore
    value = 10000000 # ₹1 Crore
    
    # 3. Simulate EFI Engine Data
    # 50 Monte Carlo scenarios
    rev = [12000000] * 50
    core_cost = [8000000] * 50
    penalties = [100000 * i for i in range(1, 4)] * 17 # ₹1L to ₹3L
    losses = [0] * 50
    duties = [500000] * 50 # ₹5L
    holding_costs = [50000 * i for i in range(1, 5)] * 13 # ₹50k to ₹200k
    opp_costs = [30000] * 50
    
    efi_result = UniversalEFIEngine.calculate_efi(
        revenue_scenarios=rev,
        cost_scenarios=core_cost,
        delay_penalty_scenarios=penalties,
        loss_factor_scenarios=losses,
        duty_scenarios=duties,
        holding_cost_scenarios=holding_costs,
        opportunity_cost_scenarios=opp_costs,
        fidelity_score=0.98
    )
    
    # 4. Generate the 3-Tier Response via Copilot
    risk_context = ["Active Port Strike in Singapore (H3: 87283)", "Heavy Congestion in Neighboring Cell"]
    advice = await llm.get_integrated_copilot_advice(
        h3_id="87283",
        risk_context=risk_context,
        efi_data=efi_result,
        doc_status="VERIFIED"
    )
    
    # 5. Output EXACT 3-Tier Structure
    print("\n[AI OUTPUT]:")
    print(advice.content)
    print("\n" + "="*50)
    print("📈 VALUE PROPOSITION:")
    print("EFI Gets Attention | Breakdown Builds Trust | Recommendation Closes the Deal")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_efi_sales_demo())
