import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score
import xgboost as xgb
import os
from pathlib import Path

# Create models dir inside the ml_pipeline root
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
os.makedirs(MODELS_DIR, exist_ok=True)

print("🚀 Step 1: Generating realistic structural supply chain dataset (10,000 rows)...")
np.random.seed(42)
n = 10000

# Basic Logistics Features
routes = np.random.choice(["US-CN", "EU-US", "US-MX", "CN-EU", "LOCAL"], n)
carriers = np.random.choice(["Maersk", "DHL", "FedEx", "LocalTransit"], n)

# Base Financial Metrics
order_values = np.random.uniform(5000, 150000, n)
# Total cost is constrained to 30% - 80% to give realistic margin ranges
costs = order_values * np.random.uniform(0.3, 0.8, n) 
credit_days = np.random.choice([0, 15, 30, 60, 90], n)

print("🧪 Generating Delay Target (Y1)...")
# Delay Generation (Target 1)
delay_days = np.zeros(n)
for i in range(n):
    base_delay = 0 if carriers[i] in ["FedEx", "DHL"] else np.random.randint(2, 10)
    if routes[i] == "US-CN": base_delay += 14
    if routes[i] == "CN-EU": base_delay += 20
    delay_days[i] = max(0, base_delay + np.random.normal(0, 3))

print("🧪 Generating Risk Target (Y2)...")
# Risk Generation (Target 2)
# High delay + low margin + high cost ratio = high risk
margins = order_values - costs
margin_pct = margins / order_values
cost_ratio = costs / order_values
# Math mirroring our Logistic Sigmoid risk_engine
logit = (cost_ratio * 2.0) - (margin_pct * 4.0) + (delay_days * 0.5)
risk_prob = 1.0 / (1.0 + np.exp(-logit))
# Binarize output for XGBoost Classifier based on strict 50% boundary
risk_labels = (risk_prob > 0.5).astype(int)

print("🧪 Generating Future Demand Target (Y3)...")
# Demand Generation (Target 3)
# Based on route and past performance (CLV sizing) penalized heavily by massive delays
future_order_values = order_values * np.random.uniform(0.8, 1.5, n) - (delay_days * 800)
future_order_values = np.maximum(future_order_values, 0) # Floor at 0

# Build Master DataFrame
df = pd.DataFrame({
    "route": routes,
    "carrier": carriers,
    "order_value": order_values,
    "total_cost": costs,
    "credit_days": credit_days,
    "delay_days": delay_days,
    "risk_label": risk_labels,
    "future_demand": future_order_values
})

# Dummy Encoding (One-Hot)
# Converts 'route_US-CN' -> 1/0
df_encoded = pd.get_dummies(df, columns=["route", "carrier"])
# Save train columns explicitly so the API can reconstruct missing columns at runtime
train_columns = df_encoded.drop(columns=["delay_days", "risk_label", "future_demand"]).columns.tolist()
joblib.dump(train_columns, MODELS_DIR / "train_columns.pkl")


# -------------------------------------------------------------------------------------
print("\n--- 🧠 Training Delay Model (XGBoost Regression) ---")
X_delay = df_encoded.drop(columns=["delay_days", "risk_label", "future_demand"])
y_delay = df_encoded["delay_days"]
X_train, X_test, y_train, y_test = train_test_split(X_delay, y_delay, test_size=0.2)

delay_model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1)
delay_model.fit(X_train, y_train)
preds = delay_model.predict(X_test)
print(f"✅ Delay Model RMSE: {np.sqrt(mean_squared_error(y_test, preds)):.2f} days")
joblib.dump(delay_model, MODELS_DIR / "delay_model.pkl")


# -------------------------------------------------------------------------------------
print("\n--- 🧠 Training Risk Model (XGBoost Classifier) ---")
# Risk model utilizes actual predicted delay as a feature!
X_risk = df_encoded.drop(columns=["risk_label", "future_demand"]) 
y_risk = df_encoded["risk_label"]
X_train, X_test, y_train, y_test = train_test_split(X_risk, y_risk, test_size=0.2)

risk_model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1)
risk_model.fit(X_train, y_train)
preds = risk_model.predict(X_test)
print(f"✅ Risk Model Accuracy: {accuracy_score(y_test, preds)*100:.2f}%")
joblib.dump(risk_model, MODELS_DIR / "risk_model.pkl")


# -------------------------------------------------------------------------------------
print("\n--- 🧠 Training Demand Model (Random Forest Regression) ---")
X_demand = df_encoded.drop(columns=["future_demand", "risk_label"])
y_demand = df_encoded["future_demand"]
X_train, X_test, y_train, y_test = train_test_split(X_demand, y_demand, test_size=0.2)

demand_model = RandomForestRegressor(n_estimators=50, max_depth=8)
demand_model.fit(X_train, y_train)
preds = demand_model.predict(X_test)
print(f"✅ Demand Model RMSE: ${np.sqrt(mean_squared_error(y_test, preds)):.2f}")
joblib.dump(demand_model, MODELS_DIR / "demand_model.pkl")

print("\n🎉 ML Pipeline execution complete! All 3 raw Pickled models saved precisely into the API directory.")
