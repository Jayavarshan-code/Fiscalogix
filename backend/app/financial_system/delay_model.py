import math
import pandas as pd
import joblib
import json
import hashlib
from pathlib import Path
from app.Db.redis_client import cache

MODELS_DIR = Path(__file__).parent / "ml_pipeline" / "models"

class DelayPredictionModel:
    def __init__(self):
        try:
            self.model = joblib.load(MODELS_DIR / "delay_model.pkl")
            self.columns = joblib.load(MODELS_DIR / "train_columns.pkl")
        except Exception:
            self.model = None

    def compute(self, row):
        """
        Predicts delay days through an XGBoost Regressor model if compiled, else falls back to heuristics.
        """
        # Create a unique key for the row to check cache
        row_key = f"delay_pred:{hashlib.md5(json.dumps(row, sort_keys=True).encode()).hexdigest()}"
        cached_val = cache.get(row_key)
        if cached_val:
            return float(cached_val)

        if self.model:
            df = pd.DataFrame([{
                "route": row.get("route", "LOCAL"),
                "carrier": row.get("carrier", "LocalTransit"),
                "order_value": row.get("order_value", 10000),
                "total_cost": row.get("total_cost", 7000),
                "credit_days": row.get("credit_days", 0)
            }])
            df_encoded = pd.get_dummies(df)
            # Reindex to exact training schema to prevent feature misalignment
            df_aligned = df_encoded.reindex(columns=self.columns, fill_value=0)
            
            # XGBRegressor prediction returns a numpy array, extract standard float
            res = max(0.0, float(self.model.predict(df_aligned)[0]))
            cache.setex(row_key, 3600, res) # Cache for 1 hour
            return res

        # --- Base Fallback Heuristic ---
        base_delay = 2.0
        
        # Heuristics
        carrier = row.get("carrier", "standard")
        carrier_reliability = 0.95 if carrier == "premium" else 0.80

        route = row.get("route", "local")
        route_complexity = 1.0
        if route == "international":
            route_complexity = 3.5

        predicted_delay = base_delay * math.exp(route_complexity * (1.0 - carrier_reliability))
        res = round(predicted_delay, 1)
        cache.setex(row_key, 3600, res)
        return res

    def compute_batch(self, rows_list):
        """
        Executes highly optimized C++ native matrix inference across thousands of shipments simultaneously.
        Now wrapped with Redis caching for ultra-fast repeated queries.
        """
        if not rows_list:
            return []

        # Create a hash for the entire batch
        batch_payload = json.dumps(rows_list, sort_keys=True)
        batch_hash = hashlib.sha256(batch_payload.encode()).hexdigest()
        cache_key = f"delay_batch:{batch_hash}"

        cached_results = cache.get(cache_key)
        if cached_results:
            return json.loads(cached_results)

        if not self.model:
            results = [self.compute(row) for row in rows_list]
        else:
            data_mapped = [{
                "route": r.get("route", "LOCAL"),
                "carrier": r.get("carrier", "LocalTransit"),
                "order_value": r.get("order_value", 10000),
                "total_cost": r.get("total_cost", 7000),
                "credit_days": r.get("credit_days", 0)
            } for r in rows_list]
            
            df = pd.DataFrame(data_mapped)
            df_encoded = pd.get_dummies(df)
            df_aligned = df_encoded.reindex(columns=self.columns, fill_value=0)
            
            predictions = self.model.predict(df_aligned)
            results = [max(0.0, float(p)) for p in predictions]
        
        # Store in Redis for 1 hour
        cache.setex(cache_key, 3600, json.dumps(results))
        return results
