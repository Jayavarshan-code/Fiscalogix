from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class CashEvent(BaseModel):
    shipment_id: int
    event_date: date
    event_type: str
    amount: float
    priority: str
    description: str

class CashTimeline(BaseModel):
    date: date
    daily_net: float
    cumulative_cash: float
    rolling_7d_net: float
    rolling_30d_net: float

class Shock(BaseModel):
    date: date
    type: str # 'CASH_DEFICIT', 'LOW_LIQUIDITY', 'SUDDEN_DROP'
    severity: float
    duration_days: int
    velocity: float
    severity_score: float

class RootCause(BaseModel):
    shipment_id: int
    contribution_to_deficit: float
    impact_percentage: float
    reason: str

class Recommendation(BaseModel):
    shock_date: date
    action_type: str
    action: str
    reason: str

class CashflowResponse(BaseModel):
    cash_position: dict
    metrics: dict
    timeline: List[CashTimeline]
    shocks: List[Shock]
    root_causes: List[RootCause]
    recommendations: List[Recommendation]
