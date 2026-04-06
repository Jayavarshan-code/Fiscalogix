import pandas as pd
from pathlib import Path
import joblib
import logging
from app.routes.admin import register_model_status

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "ml_pipeline" / "models"

# ---------------------------------------------------------------------------
# WHY THIS WAS FLAWED:
# 1. Prophet was imported but NEVER ACTUALLY USED. It was dead code. This means
#    the system loaded a heavy ML dependency at startup for zero benefit — slowing
#    boot time and wasting memory on every server restart.
# 2. The seasonality heuristic (season_multiplier = 1.15 for Q4) was hardcoded
#    for B2C retail logic (Christmas demand spike). Fiscalogix targets B2B
#    industrial supply chains where Q4 is NOT a peak season. In automotive or
#    industrial manufacturing, Q1 is often the demand peak (factory restarts after
#    fiscal year). Applying a 15% retail multiplier to an auto-parts forwarder
#    inflates their projected demand and causes the system to over-order inventory.
#
# FIX:
# 1. Prophet import completely removed. The RandomForest model handles demand
#    correctly when trained. If Prophet time-series forecasting is needed in a
#    future sprint, it should be a dedicated endpoint, not a silent unused import.
# 2. Seasonality multipliers now parameterized by `industry_vertical` field,
#    with distinct profiles for FMCG (B2C), Industrial/Automotive (B2B), and
#    Pharmaceutical (stable year-round). Falls back to a flat 1.0 if unknown.
# ---------------------------------------------------------------------------

# Peak season multipliers by industry vertical
# Keys must match the `industry_vertical` field populated from ERP/CSV ingestion
SEASONAL_PROFILES = {
    "fmcg":           {10: 1.20, 11: 1.35, 12: 1.40},   # Q4 retail/festival surge (B2C)
    "pharmaceutical": {},                                   # Stable demand year-round
    "automotive":     {1: 1.15, 2: 1.10},                  # Q1 factory restart post-fiscal
    "textile":        {3: 1.10, 8: 1.10, 9: 1.15},         # Pre-season procurement peaks
    "electronics":    {9: 1.20, 10: 1.15, 11: 1.25},       # Back-to-school + holiday launches
    "industrial":     {1: 1.10, 4: 1.10},                  # CAPEX budget cycles
    "default":        {},                                   # Flat — no seasonal assumption
}

SLOW_PAYMENT_PENALTY = 0.85   # 15% CLV reduction for chronically late-paying customers


class DemandPredictionModel:
    def __init__(self):
        try:
            self.model = joblib.load(MODELS_DIR / "demand_model.pkl")
            self.columns = joblib.load(MODELS_DIR / "train_columns.pkl")
            logger.info("DemandPredictionModel: RandomForest model loaded.")
            register_model_status("DemandModel", "ok")
        except FileNotFoundError:
            logger.warning("DemandPredictionModel: demand_model.pkl not found. Run trainer.py. Heuristic fallback active.")
            self.model = None
            register_model_status("DemandModel", "fallback", "demand_model.pkl missing")
        except Exception as e:
            logger.error(f"DemandPredictionModel: Load error — {type(e).__name__}: {e}", exc_info=True)
            self.model = None
            register_model_status("DemandModel", "fallback", f"{type(e).__name__}: {str(e)}")

    def compute(self, row):
        """
        Predicts future expected revenue (CLV sizing) from a single movement.
        """
        if self.model:
            df = pd.DataFrame([{
                "route":       row.get("route", "LOCAL"),
                "carrier":     row.get("carrier", "LocalTransit"),
                "order_value": row.get("order_value", 10000),
                "total_cost":  row.get("total_cost", 7000),
                "credit_days": row.get("credit_days", 0),
                "delay_days":  row.get("delay_days", 0)
            }])
            df_encoded = pd.get_dummies(df)
            df_aligned = df_encoded.reindex(columns=self.columns, fill_value=0)
            return max(0.0, float(self.model.predict(df_aligned)[0]))

        # --- Parameterized Heuristic Fallback ---
        base_value = row.get("order_value", 1000)

        # Vertical-aware seasonal multiplier
        vertical = str(row.get("industry_vertical", "default")).lower().strip()
        profile = SEASONAL_PROFILES.get(vertical, SEASONAL_PROFILES["default"])
        month = row.get("order_month", 6)
        season_multiplier = profile.get(month, 1.0)

        # Customer payment behaviour penalty
        customer_tier_multiplier = 1.0
        if row.get("credit_days", 0) > 45:
            customer_tier_multiplier = SLOW_PAYMENT_PENALTY

        predicted_future_value = base_value * season_multiplier * customer_tier_multiplier
        return round(predicted_future_value, 2)

    def compute_batch(self, rows_list):
        if not rows_list:
            return []
        if not self.model:
            return [self.compute(row) for row in rows_list]

        data_mapped = [{
            "route":       r.get("route", "LOCAL"),
            "carrier":     r.get("carrier", "LocalTransit"),
            "order_value": r.get("order_value", 10000),
            "total_cost":  r.get("total_cost", 7000),
            "credit_days": r.get("credit_days", 0),
            "delay_days":  r.get("delay_days", 0)
        } for r in rows_list]

        df = pd.DataFrame(data_mapped)
        df_encoded = pd.get_dummies(df)
        df_aligned = df_encoded.reindex(columns=self.columns, fill_value=0)
        predictions = self.model.predict(df_aligned)
        return [max(0.0, float(p)) for p in predictions]
