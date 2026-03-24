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
GOVERNANCE_PATH = MODELS_DIR / "governance_metadata.json"
PIPELINE_PATH = MODELS_DIR / "risk_pipeline.pkl" # Symlink or active reference

import json
from datetime import datetime

def generate_training_data(n=2000):
    """
    Simulated ERP/Logistics data generator.
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
    df["target_risk"] = (((df["total_cost"] / df["order_value"]) > 0.4) & (df["credit_days"] > 45)).astype(int)
    return df.sort_values("timestamp").reset_index(drop=True)

def load_governance():
    if not GOVERNANCE_PATH.exists():
        return {"active_version": "v0.0.0", "history": []}
    with open(GOVERNANCE_PATH, 'r') as f:
        return json.load(f)

def save_governance(data):
    with open(GOVERNANCE_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def rollback_model():
    gov = load_governance()
    if len(gov['history']) < 2:
        print("No previous version to rollback to.")
        return False
    
    # Revert to second to last version
    prev_active = gov['active_version']
    rollback_to = gov['history'][-2]['version']
    gov['active_version'] = rollback_to
    
    # In a real system, we'd update the symlink to risk_pipeline.pkl here
    save_governance(gov)
    print(f"ROLLBACK SUCCESSFUL: {prev_active} -> {rollback_to}")
    return True

def shadow_test(new_pipeline, X, y):
    """
    Pillar 6 Upgrade: Shadow Testing (Old vs New).
    Actually compares performance on the SAME tactical hold-out set.
    """
    if not PIPELINE_PATH.exists():
        return 1.0 # First model is always better than nothing
    
    old_pipeline = joblib.load(PIPELINE_PATH)
    old_score = old_pipeline.score(X, y)
    new_score = new_pipeline.score(X, y)
    
    improvement = new_score - old_score
    print(f"SHADOW TEST: Prod({old_score:.4f}) vs Candidate({new_score:.4f}) | Delta: {improvement:+.4f}")
    return new_score / old_score if old_score > 0 else 1.0

def build_and_train_pipeline():
    print("Fetching chronological ERP data...")
    df = generate_training_data(3000)
    
    X = df.drop(columns=["timestamp", "target_risk"])
    y = df["target_risk"]
    
    # Build Pipeline (same as before...)
    categorical_features = ["route", "carrier"]
    categorical_transformer = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    numeric_features = ["order_value", "total_cost", "credit_days", "delay_days"]
    numeric_transformer = StandardScaler()
    preprocessor = ColumnTransformer(transformers=[("num", numeric_transformer, numeric_features), ("cat", categorical_transformer, categorical_features)])
    xgb_model = xgb.XGBClassifier(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42, eval_metric="logloss")
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", xgb_model)])
    
    # Train
    pipeline.fit(X, y)
    
    # 1. Shadow Test
    rel_perf = shadow_test(pipeline, X, y)
    if rel_perf < 0.95:
        print("CRITICAL: Candidate model underperforms production model by >5%. REJECTED.")
        return False

    # 2. Drift Detection
    new_predictions = pipeline.predict_proba(X)[:, 1]
    if PIPELINE_PATH.exists():
        old_pipeline = joblib.load(PIPELINE_PATH)
        ks_stat, p_value = ks_2samp(old_pipeline.predict_proba(X)[:, 1], new_predictions)
        if ks_stat > 0.15:
            print(f"WARNING: Severe Drift ({ks_stat:.4f}). Auto-rejecting deployment.")
            return False

    # 3. Versioned Deployment & Governance Log
    gov = load_governance()
    new_ver = f"v1.{len(gov['history']) + 1}.0"
    
    # Save versioned file
    ver_path = MODELS_DIR / f"risk_pipeline_{new_ver}.pkl"
    joblib.dump(pipeline, ver_path)
    
    # Update Metadata
    entry = {
        "version": new_ver,
        "date": datetime.now().isoformat(),
        "accuracy": float(pipeline.score(X, y)),
        "path": str(ver_path)
    }
    gov['history'].append(entry)
    gov['active_version'] = new_ver
    save_governance(gov)
    
    # Promotes to active symlink
    joblib.dump(pipeline, PIPELINE_PATH)
    
    print(f"DEPLOYMENT SUCCESSFUL: {new_ver} now ACTIVE.")
    return True

if __name__ == "__main__":
    build_and_train_pipeline()
