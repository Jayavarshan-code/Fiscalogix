from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.financial_system.extensions.carbon_model import CarbonTaxEngine
from app.financial_system.extensions.ar_default_model import ARDefaultPredictor
from app.financial_system.extensions.freight_model import FreightHedgingEngine
from app.financial_system.extensions.meio_engine import MEIOEngine
from app.financial_system.extensions.gnn_mapper import GNNRiskMapper
from app.financial_system.extensions.llm_negotiator import GenerativeNegotiator

# Unified Enterprise Expansion Router enforcing strict architectural modularity
router = APIRouter(prefix="/enterprise", tags=["Enterprise AI Pipelines"])

# --- Pillar 7: Carbon Tax ---
class ShipmentData(BaseModel):
    shipment_id: str
    route: str
    carrier: str
    order_value: float
    total_cost: float
    weight_tons: float = 15.0

class CarbonResponse(BaseModel):
    shipment_id: str
    emissions_kg: float
    emissions_tons: float
    tax_liability_usd: float
    carrier_efficiency_rating: str

carbon_engine = CarbonTaxEngine()

@router.post("/carbon-tax", response_model=List[CarbonResponse])
def calculate_carbon_tax(shipments: List[ShipmentData]):
    results = []
    for s in shipments:
        results.append({"shipment_id": s.shipment_id, **carbon_engine.compute(s.model_dump())})
    return results

# --- Pillar 8: AR Default Predictor ---
class CustomerData(BaseModel):
    customer_id: str
    order_value: float
    credit_days: int
    historical_defaults: int = 0
    macro_economic_index: float = 1.0

class DefaultResponse(BaseModel):
    customer_id: str
    probability_of_default: float
    expected_credit_loss: float
    recommended_action: str

ar_engine = ARDefaultPredictor()

@router.post("/ar-default", response_model=List[DefaultResponse])
def calculate_ar_default(customers: List[CustomerData]):
    results = []
    for c in customers:
        pd_score = ar_engine.compute(c.model_dump())
        ecl = c.order_value * pd_score
        action = "APPROVE NET-TERMS"
        if pd_score > 0.15: action = "REQUIRE CASH-IN-ADVANCE"
        elif pd_score > 0.05: action = "INITIATE INVOICE FACTORING"
        results.append({
            "customer_id": c.customer_id, "probability_of_default": pd_score,
            "expected_credit_loss": round(ecl, 2), "recommended_action": action
        })
    return results

# --- Pillar 9: Dynamic Freight Hedging ---
class FreightData(BaseModel):
    route_id: str
    current_spot_rate: float
    current_contract_rate: float
    market_volatility_index: float = 1.0

class HedgingResponse(BaseModel):
    route_id: str
    predicted_spot_rate_6mo: float
    arbitrage_decision: str
    decision_confidence: float
    expected_savings_per_feu: float

freight_engine = FreightHedgingEngine()

@router.post("/freight-hedging", response_model=List[HedgingResponse])
def calculate_freight_hedging(routes: List[FreightData]):
    results = []
    for r in routes:
        results.append({"route_id": r.route_id, **freight_engine.compute(r.model_dump())})
    return results

# --- Pillar 10: Multi-Echelon Inventory Optimization (MEIO) ---
class SKUData(BaseModel):
    sku: str
    global_inventory: int
    wacc: float = 0.08
    holding_cost_usd: float
    stockout_penalty_usd: float

class MEIOResponse(BaseModel):
    sku: str
    optimal_allocation: dict
    financial_friction: dict

meio_engine = MEIOEngine()

@router.post("/meio-inventory", response_model=List[MEIOResponse])
def optimize_inventory(skus: List[SKUData]):
    return [meio_engine.compute(s.model_dump()) for s in skus]

# --- Pillar 11: Graph Neural Network (GNN) Risk Mapper ---
class GNNRequest(BaseModel):
    shipments: List[dict]

class GNNResponse(BaseModel):
    shipment_id: str
    original_risk: float
    propagated_risk: float
    systemic_contagion_detected: bool

gnn_engine = GNNRiskMapper()

@router.post("/gnn-systemic-risk", response_model=List[GNNResponse])
def calculate_systemic_risk(payload: GNNRequest):
    return gnn_engine.map_and_propagate(payload.shipments)

# --- Pillar 12: Generative LLM Negotiator ---
class SupplierData(BaseModel):
    supplier_id: str
    historical_delay_variance_pct: float = 15.0
    current_payment_terms: int = 30
    target_payment_terms: int = 60
    wacc_carrying_cost_usd: float

class NegotiatorResponse(BaseModel):
    supplier_id: str
    llm_engine: str
    system_prompt: str
    user_prompt: str
    status: str

llm_engine = GenerativeNegotiator()

@router.post("/llm-negotiator", response_model=List[NegotiatorResponse])
def generate_negotiation_prompts(suppliers: List[SupplierData]):
    return [llm_engine.generate_negotiation_payload(s.model_dump()) for s in suppliers]
