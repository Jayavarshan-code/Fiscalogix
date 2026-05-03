"""
Financial Analytics API — exposes the three previously-orphaned financial engines
(DemandPredictionModel, TariffDutyModel, FXRiskModel) via REST.

These models were used internally by the ReVM pipeline but had no API surface,
making the demand forecasting, tariff analysis, and FX exposure features
invisible to the frontend and external integrations.

Routes
------
  POST /api/v1/financial/demand   — CLV / future-revenue forecast (batch)
  POST /api/v1/financial/tariff   — Import duty cost calculation (batch)
  POST /api/v1/financial/fx       — FX erosion cost (delay + AR window, batch)
"""

from functools import lru_cache
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from app.financial_system.dependencies import get_current_user
from app.financial_system.demand_model import DemandPredictionModel
from app.financial_system.tariff_model import TariffDutyModel
from app.financial_system.fx_model import FXRiskModel

router = APIRouter()


# ── Engine factories ──────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def get_demand_model() -> DemandPredictionModel:
    return DemandPredictionModel()

@lru_cache(maxsize=None)
def get_tariff_model() -> TariffDutyModel:
    return TariffDutyModel()

@lru_cache(maxsize=None)
def get_fx_model() -> FXRiskModel:
    return FXRiskModel()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/demand")
async def forecast_demand(
    payload: List[Dict[str, Any]],
    _user: dict = Depends(get_current_user),
    model: DemandPredictionModel = Depends(get_demand_model),
):
    """
    Batch CLV / demand forecast.

    Each row fields:
      route, carrier, order_value, total_cost, credit_days, delay_days,
      industry_vertical, order_month (1–12), days_overdue, shipment_id (optional)

    Returns predicted future revenue (CLV sizing) per shipment.
    Applies industry-vertical seasonal profiles and slow-pay penalty.
    """
    try:
        results = model.compute_batch(payload)
        return {
            "status": "success",
            "demand_forecast": [
                {
                    "shipment_id": row.get("shipment_id"),
                    "predicted_clv": results[i],
                    "industry_vertical": row.get("industry_vertical", "default"),
                }
                for i, row in enumerate(payload)
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tariff")
async def calculate_tariff(
    payload: List[Dict[str, Any]],
    _user: dict = Depends(get_current_user),
    model: TariffDutyModel = Depends(get_tariff_model),
):
    """
    Batch import duty / customs tariff calculation.

    Each row fields:
      route (e.g. "US-CN", "IN-EU"), order_value, hs_code (optional 6-digit),
      duty_drawback_rate (0.0–0.99, optional), shipment_id (optional)

    Rate resolution: HS chapter override > Redis live rate > route corridor average.
    Duty drawback (US CBP §1313) netted when drawback_rate > 0.
    Returns 0 for domestic/LOCAL routes.
    """
    try:
        results = model.compute_batch(payload)
        return {
            "status": "success",
            "tariff_analysis": [
                {
                    "shipment_id": row.get("shipment_id"),
                    "tariff_cost": results[i],
                    "route": row.get("route", "LOCAL"),
                    "is_cross_border": model._is_cross_border(
                        str(row.get("route", "LOCAL")).upper().strip()
                    ),
                    "hs_code_used": row.get("hs_code"),
                }
                for i, row in enumerate(payload)
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fx")
async def calculate_fx_exposure(
    payload: List[Dict[str, Any]],
    _user: dict = Depends(get_current_user),
    model: FXRiskModel = Depends(get_fx_model),
):
    """
    Batch FX erosion cost — two-component model.

    Each row fields:
      route, order_value, shipment_cost (optional; estimated as 12% of order_value),
      credit_days, payment_delay_days (optional), predicted_delay (float days),
      shipment_id (optional)

    Component 1: shipment cost erosion during delay window.
    Component 2: AR exposure erosion during full credit period (dominant for high-value orders).
    Geometric compounding applied when credit_days > 45.
    """
    try:
        delays = [float(row.get("predicted_delay", 0.0)) for row in payload]
        results = model.compute_batch(payload, delays)
        return {
            "status": "success",
            "fx_exposure": [
                {
                    "shipment_id": row.get("shipment_id"),
                    "fx_cost": results[i],
                    "route": row.get("route", "LOCAL"),
                    "predicted_delay_days": delays[i],
                }
                for i, row in enumerate(payload)
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
