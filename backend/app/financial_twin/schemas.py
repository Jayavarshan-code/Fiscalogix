from pydantic import BaseModel
from typing import Optional

class FinancialTwinResponse(BaseModel):
    order_id: int
    shipment_id: int
    customer_id: int
    order_value: float
    shipment_cost: float
    delay_days: int
    holding_cost_per_day: float
    wacc: float
    penalty_rate: float
    credit_days: int
    payment_delay_days: int
    holding_cost: float
    delay_cost: float
    opportunity_cost: float
    ar_cost: float
    total_cost: float
    profit: float

class FinancialSummary(BaseModel):
    total_profit: float
    total_revenue: float
    total_cost: float
    loss_shipments: int
    high_margin_shipments: int
    total_ar_cost: float

class InventoryTwinResponse(BaseModel):
    inventory_id: int
    warehouse_id: int
    sku_id: int
    quantity: int
    unit_cost: float
    wacc: float
    capital_locked: float
    inventory_opportunity_cost: float

class InventorySummary(BaseModel):
    total_capital_locked: float
    total_inventory_opportunity_cost: float