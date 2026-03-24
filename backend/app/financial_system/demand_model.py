import pandas as pd
from datetime import datetime
import joblib
from pathlib import Path

try:
    from prophet import Prophet
except ImportError:
    Prophet = None

MODELS_DIR = Path(__file__).parent / "ml_pipeline" / "models"

class DemandPredictionModel:
    def __init__(self):
        try:
            self.model = joblib.load(MODELS_DIR / "demand_model.pkl")
            self.columns = joblib.load(MODELS_DIR / "train_columns.pkl")
        except Exception:
            self.model = None

    def compute(self, row):
        """
        Predicts future expected revenue (CLV sizing) from a single movement using Random Forest
        """
        if self.model:
            df = pd.DataFrame([{
                "route": row.get("route", "LOCAL"),
                "carrier": row.get("carrier", "LocalTransit"),
                "order_value": row.get("order_value", 10000),
                "total_cost": row.get("total_cost", 7000),
                "credit_days": row.get("credit_days", 0),
                "delay_days": row.get("delay_days", 0)
            }])
            df_encoded = pd.get_dummies(df)
            df_aligned = df_encoded.reindex(columns=self.columns, fill_value=0)
            
            return max(0.0, float(self.model.predict(df_aligned)[0]))

        # --- Base Fallback Heuristic ---
        base_value = row.get("order_value", 1000)

        # Factor in simple seasonality
        season_multiplier = 1.0
        # If order happens in Q4, boost expected CLV slightly
        month = row.get("order_month", 6)
        if month in [10, 11, 12]:
            season_multiplier = 1.15

        # Penalize if customer is traditionally slow paying (weak health)
        customer_tier_multiplier = 1.0
        if row.get("credit_days", 0) > 45:
            customer_tier_multiplier = 0.85

        predicted_future_value = base_value * season_multiplier * customer_tier_multiplier

        return round(predicted_future_value, 2)

    def compute_batch(self, rows_list):
        """
        Vectorizes Lifetime Value extraction across full SQL arrays, bypassing row creation loops.
        """
        if not self.model or not rows_list:
            return [self.compute(row) for row in rows_list]
            
        data_mapped = [{
            "route": r.get("route", "LOCAL"),
            "carrier": r.get("carrier", "LocalTransit"),
            "order_value": r.get("order_value", 10000),
            "total_cost": r.get("total_cost", 7000),
            "credit_days": r.get("credit_days", 0),
            "delay_days": r.get("delay_days", 0)
        } for r in rows_list]
        
        df = pd.DataFrame(data_mapped)
        df_encoded = pd.get_dummies(df)
        df_aligned = df_encoded.reindex(columns=self.columns, fill_value=0)
        
        predictions = self.model.predict(df_aligned)
        return [max(0.0, float(p)) for p in predictions]
