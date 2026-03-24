import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import TimeSeriesSplit
from scipy.stats import ks_2samp
import xgboost as xgb
import os

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
PIPELINE_PATH = MODELS_DIR / "risk_pipeline.pkl"

def generate_training_data(n=2000):
    """
    Simulates fetching a time-series chronological dataset from the ERP/Analytics Warehouse.
    """
    np.random.seed(42)
    dates = pd.date_range(start="2026-01-01", periods=n, freq="H")
    
    df = pd.DataFrame({
        "timestamp": dates,
        "route": np.random.choice(["LOCAL", "INTL_OCEAN", "INTL_AIR", "REGIONAL_TRUCK"], n),
        "carrier": np.random.choice(["Maersk", "FedEx", "LocalTransit", "JB_Hunt"], n),
        "order_value": np.random.uniform(5000, 150000, n),
        "total_cost": np.random.uniform(500, 20000, n),
        "credit_days": np.random.choice([0, 15, 30, 60, 90], n),
        "delay_days": np.random.uniform(0, 15, n)
    })
    
    # Simulate realistic risk triggers
    cost_ratio_risk = (df["total_cost"] / df["order_value"]) > 0.4
    delay_risk = df["delay_days"] > 5
    credit_risk = df["credit_days"] > 45
    
    # 1 if risky shipment, 0 if safe
    df["target_risk"] = ((cost_ratio_risk | delay_risk) & credit_risk).astype(int)
    
    # Sort chronologically (Crucial for TimeSeriesSplit)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

def build_and_train_pipeline():
    print("Fetching chronological ERP data...")
    df = generate_training_data(3000)
    
    X = df.drop(columns=["timestamp", "target_risk"])
    y = df["target_risk"]
    
    print("Building Enterprise Feature Store Pipeline...")
    # 1. Protect against Model Crashes (Handle Unknown Categories)
    categorical_features = ["route", "carrier"]
    categorical_transformer = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    
    numeric_features = ["order_value", "total_cost", "credit_days", "delay_days"]
    numeric_transformer = StandardScaler()
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )
    
    # 2. Define the XGBoost Model
    xgb_model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42,
        eval_metric="logloss"
    )
    
    # 3. Create the Indestructible Pipeline
    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", xgb_model)
    ])
    
    # 4. Strict Time-Series Cross Validation (No Data Leakage)
    print("Validating with TimeSeriesSplit to prevent Future Leakage...")
    tscv = TimeSeriesSplit(n_splits=3)
    
    scores = []
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        pipeline.fit(X_train, y_train)
        score = pipeline.score(X_test, y_test)
        scores.append(score)
        
    print(f"TimeSeries Validation Accuracy: {np.mean(scores):.2f}")
    
    # Final Fit on all data
    pipeline.fit(X, y)
    new_predictions = pipeline.predict_proba(X)[:, 1]
    
    # 5. Drift Detection (Kolmogorov-Smirnov Test)
    if PIPELINE_PATH.exists():
        print("Checking for Data Drift against Production Model...")
        old_pipeline = joblib.load(PIPELINE_PATH)
        old_predictions = old_pipeline.predict_proba(X)[:, 1]
        
        ks_stat, p_value = ks_2samp(old_predictions, new_predictions)
        print(f"K-S Drift Statistic: {ks_stat:.4f}, p-value: {p_value:.4f}")
        
        if ks_stat > 0.1 and p_value < 0.05:
            print("WARNING: Severe Model Drift Detected! Rejecting deployment. Manual review required.")
            return False
        else:
            print("Drift check passed. Model distributions are stable.")
    
    # 6. Save the FULL pipeline (Encoder + Scaler + Model inside one file)
    joblib.dump(pipeline, PIPELINE_PATH)
    print(f"Production Pipeline Saved to {PIPELINE_PATH}")
    return True

if __name__ == "__main__":
    build_and_train_pipeline()
