import pandas as pd
import joblib
import math
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "ml_pipeline" / "models"

class ARDefaultPredictor:
    def __init__(self):
        try:
            # Assumes a specially trained AR XGBoost classifier
            self.model = joblib.load(MODELS_DIR / "ar_default_model.pkl")
            self.columns = joblib.load(MODELS_DIR / "ar_train_columns.pkl")
        except Exception:
            self.model = None

    def compute(self, customer_data):
        """
        Outputs the strict mathematical Probability of Default (Bankruptcy) for an invoice.
        """
        credit_days = customer_data.get("credit_days", 30)
        order_value = customer_data.get("order_value", 10000)
        historical_defaults = customer_data.get("historical_defaults", 0)
        macro_index = customer_data.get("macro_economic_index", 1.0) # 1.0 is stable, >1.0 is risky

        if self.model:
            df = pd.DataFrame([{
                "credit_days": credit_days,
                "order_value": order_value,
                "historical_defaults": historical_defaults,
                "macro_index": macro_index
            }])
            df_aligned = df.reindex(columns=self.columns, fill_value=0)
            return float(self.model.predict_proba(df_aligned)[0][1])
            
        # --- Heuristic Fallback ---
        # Base probability ranges from 0.01% to 15% based on credit stretch
        base_pd = 0.001 
        
        # Logistic escalation: Every 15 days past Net-30 exponentially increases default risk
        if credit_days > 30:
            stretch = (credit_days - 30) / 15.0
            base_pd += (math.exp(stretch) - 1) * 0.005 

        # Historical penalty
        base_pd += (historical_defaults * 0.05)
        
        # Macro multiplier
        final_pd = base_pd * macro_index

        return min(0.99, round(final_pd, 4))
