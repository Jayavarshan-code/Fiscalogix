import pandas as pd
import joblib
from pathlib import Path

# Paths mapping directly to active memory instances
MODELS_DIR = Path(__file__).parent / "models"

class FeedbackEngine:
    """
    Self-Learning Module: Ingests empirical supply chain truths (post-execution) and mathematically alters the 
    weights of the active XGBoost models to structurally prevent concept drift.
    """
    def __init__(self):
        try:
            self.train_columns = joblib.load(MODELS_DIR / "train_columns.pkl")
            
            # Load the current memory states
            self.delay_model = joblib.load(MODELS_DIR / "delay_model.pkl")
            self.risk_model = joblib.load(MODELS_DIR / "risk_model.pkl")
            
        except Exception as e:
            print(f"Warning: A core model failed to load into Feedback Engine - {e}")
            self.delay_model = None

    def _align_dataframe(self, raw_dicts):
        """
        Forces structural compliance exactly mapping the actual operations to the model tensors.
        """
        df = pd.DataFrame(raw_dicts)
        columns_to_keep = ["route", "carrier", "order_value", "total_cost", "credit_days", "delay_days"]
        df_filtered = df[[col for col in columns_to_keep if col in df.columns]]
        
        df_encoded = pd.get_dummies(df_filtered)
        df_aligned = df_encoded.reindex(columns=self.train_columns, fill_value=0)
        return df_aligned

    def process_telemetry(self, outcomes):
        """
        Takes an array of completely finished shipments where 'actual' variables are securely known.
        Uses XGBoost incremental learning to permanently embed this new reality into Fiscalogix intelligence.
        """
        if not self.delay_model or not self.risk_model:
            return {"status": "FAILED", "reason": "Base Models Offline"}

        valid_outcomes = [row for row in outcomes if "actual_delay_days" in row and "actual_defaulted" in row]
        if not valid_outcomes:
            return {"status": "SKIPPED", "reason": "No valid empirical truth targets provided"}

        # Extract independent X arrays
        X_aligned = self._align_dataframe(valid_outcomes)

        # Extract supervised true reality y arrays
        y_delay = [float(row["actual_delay_days"]) for row in valid_outcomes]
        y_risk = [int(row["actual_defaulted"]) for row in valid_outcomes]

        # 1. XGBoost Recursive Learning: Fit the current model utilizing the existing architecture as the baseline!
        # This prevents catastrophic forgetting while natively absorbing new chronological data.
        self.delay_model.fit(X_aligned, y_delay, xgb_model=self.delay_model)
        self.risk_model.fit(X_aligned, y_risk, xgb_model=self.risk_model)

        # 2. Overwrite the Active `.pkl` instances mapping the new intelligence matrix
        joblib.dump(self.delay_model, MODELS_DIR / "delay_model.pkl")
        joblib.dump(self.risk_model, MODELS_DIR / "risk_model.pkl")

        return {
            "status": "SUCCESS",
            "weights_adjusted": True,
            "shipments_ingested": len(valid_outcomes),
            "affected_models": ["XGBoost Delay", "XGBoost Risk"]
        }
