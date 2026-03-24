import os
import time
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from xgboost import XGBRegressor, XGBClassifier
from sklearn.model_selection import RandomizedSearchCV, train_test_split

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def synthesize_hyper_scale_data(N=100000):
    """
    Generates deeply interconnected operational matrices mirroring real-world chaos.
    """
    np.random.seed(42)
    print(f"🌍 Synthesizing {N} Massive Non-Linear Arrays...")
    
    data = []
    routes = ["US-CN", "EU-US", "APAC", "LOCAL"]
    carriers = ["Maersk", "DHL", "FedEx", "Hapag-Lloyd"]

    for i in range(N):
        route = np.random.choice(routes, p=[0.4, 0.3, 0.2, 0.1])
        carrier = np.random.choice(carriers)
        order_value = float(np.random.uniform(5000, 250000))
        weight_tons = float(np.random.uniform(1.0, 100.0))
        credit_days = int(np.random.randint(15, 120))
        
        # 1. Base Delay Correlation mapping structural bounds
        base_delay = np.random.exponential(3.0) 
        
        # [Non-Linear Correlation A]: Heavy Asian routes suffer extreme port bottlenecking
        if route == "US-CN" and weight_tons > 50:
            base_delay *= 2.5
        
        # [Non-Linear Correlation B]: Local DHL shipping is structurally immune to heavy delay
        if route == "LOCAL" and carrier == "DHL":
            base_delay *= 0.2
            
        actual_delay_days = max(0.0, base_delay + np.random.normal(0, 1.0))
        
        # 2. Base Default Correlation mapping Enterprise reliability
        default_prob = 0.05
        
        # [Non-Linear Correlation C]: Enterprise clients ($100k+) structurally do not default on invoices
        if order_value > 100000:
            default_prob = 0.005
            
        # [Non-Linear Correlation D]: Heavy credit stretches over 90 days exponentially increase insolvency risk
        if credit_days > 90:
            default_prob *= 3.5
            
        actual_defaulted = 1 if np.random.random() < default_prob else 0
        
        data.append({
            "route": route,
            "carrier": carrier,
            "order_value": order_value,
            "total_cost": float(order_value * np.random.uniform(0.5, 0.85)),
            "weight_tons": weight_tons,
            "credit_days": credit_days,
            "actual_delay_days": actual_delay_days,
            "actual_defaulted": actual_defaulted
        })
        
    df = pd.DataFrame(data)
    print(f"✅ Data Synthesized: {df.shape}")
    return df

def execute_hyperparameter_gridsearch():
    df = synthesize_hyper_scale_data(100000)
    
    X = pd.get_dummies(df.drop(columns=["actual_delay_days", "actual_defaulted"]))
    y_delay = df["actual_delay_days"]
    y_risk = df["actual_defaulted"]
    
    # Save the exact boolean matrix structure for inference alignment
    joblib.dump(list(X.columns), MODELS_DIR / "train_columns.pkl")
    
    X_train, X_test, yd_train, yd_test, yr_train, yr_test = train_test_split(
        X, y_delay, y_risk, test_size=0.1, random_state=42
    )
    
    print("\n🔥 [1] Optimizing XGBoost Regressor (Delay Model)...")
    delay_param_grid = {
        'max_depth': [3, 5, 7, 9],
        'learning_rate': [0.01, 0.05, 0.1, 0.2],
        'subsample': [0.6, 0.8, 1.0],
        'n_estimators': [100, 200]
    }
    
    delay_model = XGBRegressor(objective='reg:squarederror')
    # RandomizedSearchCV to prevent OS freezing over 100,000 rows (samples 10 absolute boundaries)
    delay_search = RandomizedSearchCV(delay_model, delay_param_grid, n_iter=10, scoring='neg_mean_absolute_error', cv=3, verbose=1, random_state=42)
    
    t0 = time.time()
    delay_search.fit(X_train, yd_train)
    print(f"✅ Delay Optimization Complete ({time.time() - t0:.1f}s)")
    print(f"   -> Absolute Optimal Limits: {delay_search.best_params_}")
    
    print("\n🔥 [2] Optimizing XGBoost Classifier (AR Default / Risk Model)...")
    
    # Weight resolution to force structural Precision via dynamic Scale_Pos_Weight balancing
    ratio = float(len(yr_train) / sum(yr_train)) if sum(yr_train) > 0 else 1.0
    
    risk_param_grid = {
        'max_depth': [3, 6, 8],
        'learning_rate': [0.05, 0.1, 0.2],
        'scale_pos_weight': [1.0, ratio * 0.5, ratio] # Manipulating the precision threshold dynamically
    }
    
    risk_model = XGBClassifier(objective='binary:logistic', eval_metric='logloss')
    risk_search = RandomizedSearchCV(risk_model, risk_param_grid, n_iter=10, scoring='roc_auc', cv=3, verbose=1, random_state=42)
    
    t0 = time.time()
    risk_search.fit(X_train, yr_train)
    print(f"✅ Predictor Optimization Complete ({time.time() - t0:.1f}s)")
    print(f"   -> Absolute Optimal Limits: {risk_search.best_params_}")
    
    print("\n🔥 [3] Optimizing RandomForest Regressor (Demand / CLV Model)...")
    from sklearn.ensemble import RandomForestRegressor
    
    # Generate Synthetic Future CLV Target (Heavily correlated to order_value and negative delays)
    y_demand = df["order_value"] * 1.5 - (df["actual_delay_days"] * 500)
    ydem_train, ydem_test = train_test_split(y_demand, test_size=0.1, random_state=42)
    
    demand_param_grid = {
        'n_estimators': [50, 100, 200],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 5, 10]
    }
    
    demand_model = RandomForestRegressor(random_state=42)
    demand_search = RandomizedSearchCV(demand_model, demand_param_grid, n_iter=5, scoring='neg_mean_absolute_error', cv=3, verbose=1, random_state=42)
    
    t0 = time.time()
    demand_search.fit(X_train, ydem_train)
    print(f"✅ Demand Optimization Complete ({time.time() - t0:.1f}s)")
    print(f"   -> Absolute Optimal Limits: {demand_search.best_params_}")
    
    print("\n🚀 Overwriting Production `.pkl` Tensors...")
    joblib.dump(delay_search.best_estimator_, MODELS_DIR / "delay_model.pkl")
    joblib.dump(risk_search.best_estimator_, MODELS_DIR / "risk_model.pkl")
    joblib.dump(demand_search.best_estimator_, MODELS_DIR / "demand_model.pkl")
    print("✅ Hyper-Scale Architecture Master Update Complete. Fiscalogix V3.0 ML Weights Locked.")

if __name__ == "__main__":
    execute_hyperparameter_gridsearch()
