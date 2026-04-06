"""
ML Training Pipeline — Fiscalogix
Preference order:
  1. Real historical data from the DW (dw_shipment_facts)  ← production-grade
  2. Synthetic data (10,000 rows)                          ← demo / cold-start fallback

Run manually:   python -m app.financial_system.ml_pipeline.train_models
Run via Celery: task name "retrain_ml_models"
"""
import pandas as pd
import numpy as np
import joblib
import logging
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score
import xgboost as xgb

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MIN_REAL_ROWS = 500  # Only use real data if we have enough to train on


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def _load_from_db() -> pd.DataFrame:
    """
    Pulls historical shipment facts from the data warehouse.
    Returns empty DataFrame if DB is unavailable or has insufficient rows.
    """
    try:
        from app.Db.connections import engine
        query = """
            SELECT
                route,
                carrier,
                total_value_usd       AS order_value,
                total_cost_usd        AS total_cost,
                credit_days,
                delay_days_calculated AS delay_days,
                margin_usd            AS contribution_profit
            FROM dw_shipment_facts
            WHERE delay_days_calculated IS NOT NULL
              AND total_value_usd       IS NOT NULL
              AND total_cost_usd        IS NOT NULL
            LIMIT 100000
        """
        df = pd.read_sql(query, engine)
        logger.info(f"train_models: loaded {len(df)} rows from dw_shipment_facts.")
        return df
    except Exception as e:
        logger.warning(f"train_models: DB load failed ({type(e).__name__}: {e}). Using synthetic data.")
        return pd.DataFrame()


def _generate_synthetic(n: int = 10000) -> pd.DataFrame:
    """
    Generates a realistic synthetic supply chain dataset as a cold-start fallback.
    All assumptions are documented and deterministic (seed=42).
    """
    np.random.seed(42)
    routes = np.random.choice(["US-CN", "EU-US", "US-MX", "CN-EU", "LOCAL"], n)
    carriers = np.random.choice(["Maersk", "DHL", "FedEx", "LocalTransit"], n)

    order_values = np.random.uniform(5000, 150000, n)
    total_costs = order_values * np.random.uniform(0.3, 0.8, n)
    credit_days = np.random.choice([0, 15, 30, 60, 90], n)

    # Delay: carrier + route dependent, Gaussian noise
    delay_days = np.zeros(n)
    for i in range(n):
        base = 0 if carriers[i] in ["FedEx", "DHL"] else np.random.randint(2, 10)
        if routes[i] == "US-CN":  base += 14
        if routes[i] == "CN-EU":  base += 20
        delay_days[i] = max(0, base + np.random.normal(0, 3))

    contribution_profit = order_values - total_costs

    return pd.DataFrame({
        "route": routes,
        "carrier": carriers,
        "order_value": order_values,
        "total_cost": total_costs,
        "credit_days": credit_days,
        "delay_days": delay_days,
        "contribution_profit": contribution_profit,
    })


_last_build_meta: dict = {}   # module-level store so train_all() can read it


def _build_dataset() -> pd.DataFrame:
    global _last_build_meta
    df = _load_from_db()
    if len(df) >= MIN_REAL_ROWS:
        logger.info(f"train_models: training on {len(df)} REAL rows.")
        source = "real"
    else:
        logger.warning(
            f"train_models: only {len(df)} real rows (need {MIN_REAL_ROWS}). "
            "Falling back to synthetic dataset."
        )
        df = _generate_synthetic()
        source = "synthetic"
    _last_build_meta = {"training_rows": len(df), "data_source": source}

    # Derived targets
    margins = df["contribution_profit"] if "contribution_profit" in df.columns else (df["order_value"] - df["total_cost"])
    margin_pct = margins / df["order_value"].clip(lower=1)
    cost_ratio = df["total_cost"] / df["order_value"].clip(lower=1)
    logit = (cost_ratio * 2.0) - (margin_pct * 4.0) + (df["delay_days"] * 0.5)
    risk_prob = 1.0 / (1.0 + np.exp(-logit))
    df["risk_label"] = (risk_prob > 0.5).astype(int)

    # Future demand: penalised by delay
    df["future_demand"] = (df["order_value"] * np.random.uniform(0.8, 1.5, len(df)) - (df["delay_days"] * 800)).clip(lower=0)

    logger.info(f"train_models: dataset ready — {len(df)} rows, source={source}.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

NUMERIC_FEATURES = ["order_value", "total_cost", "credit_days", "delay_days"]
CATEGORICAL_FEATURES = ["route", "carrier"]


def _build_preprocessor():
    return ColumnTransformer([
        ("num", "passthrough", NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: MODEL TRAINING
# ─────────────────────────────────────────────────────────────────────────────

def train_all():
    df = _build_dataset()

    # ── Delay Model ──────────────────────────────────────────────────────────
    logger.info("Training Delay Model (XGBoost Regressor)...")
    X_delay = df[NUMERIC_FEATURES[:-1] + CATEGORICAL_FEATURES]  # exclude delay_days itself
    # Rebuild numeric without delay_days
    num_no_delay = ["order_value", "total_cost", "credit_days"]
    preprocessor_delay = ColumnTransformer([
        ("num", "passthrough", num_no_delay),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])
    X_delay = df[num_no_delay + CATEGORICAL_FEATURES]
    y_delay = df["delay_days"]
    Xtr, Xte, ytr, yte = train_test_split(X_delay, y_delay, test_size=0.2, random_state=42)

    delay_pipe = Pipeline([
        ("preprocessor", preprocessor_delay),
        ("regressor", xgb.XGBRegressor(n_estimators=150, max_depth=5, learning_rate=0.08, random_state=42)),
    ])
    delay_pipe.fit(Xtr, ytr)
    delay_rmse = np.sqrt(mean_squared_error(yte, delay_pipe.predict(Xte)))
    logger.info(f"Delay Model RMSE: {delay_rmse:.2f} days")
    joblib.dump(delay_pipe, MODELS_DIR / "delay_model.pkl")

    # ── Risk Model ───────────────────────────────────────────────────────────
    logger.info("Training Risk Model (XGBoost Classifier + SHAP pipeline)...")
    X_risk = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_risk = df["risk_label"]
    Xtr, Xte, ytr, yte = train_test_split(X_risk, y_risk, test_size=0.2, random_state=42)

    risk_preprocessor = _build_preprocessor()
    risk_clf = xgb.XGBClassifier(
        n_estimators=150, max_depth=4, learning_rate=0.08,
        scale_pos_weight=(y_risk == 0).sum() / max((y_risk == 1).sum(), 1),  # class imbalance
        eval_metric="logloss", random_state=42
    )
    risk_pipe = Pipeline([
        ("preprocessor", risk_preprocessor),
        ("classifier", risk_clf),
    ])
    risk_pipe.fit(Xtr, ytr)
    acc = accuracy_score(yte, risk_pipe.predict(Xte))
    logger.info(f"Risk Model Accuracy: {acc * 100:.2f}%")
    joblib.dump(risk_pipe, MODELS_DIR / "risk_pipeline.pkl")

    # Save train column names so inference can align feature order at runtime
    train_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    joblib.dump(train_columns, MODELS_DIR / "train_columns.pkl")

    # ── Demand Model ─────────────────────────────────────────────────────────
    logger.info("Training Demand Model (RandomForest Regressor)...")
    demand_preprocessor = ColumnTransformer([
        ("num", "passthrough", num_no_delay),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])
    X_demand = df[num_no_delay + CATEGORICAL_FEATURES]
    y_demand = df["future_demand"]
    Xtr, Xte, ytr, yte = train_test_split(X_demand, y_demand, test_size=0.2, random_state=42)

    demand_pipe = Pipeline([
        ("preprocessor", demand_preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=100, max_depth=10, n_jobs=-1, random_state=42)),
    ])
    demand_pipe.fit(Xtr, ytr)
    demand_rmse = np.sqrt(mean_squared_error(yte, demand_pipe.predict(Xte)))
    logger.info(f"Demand Model RMSE: ${demand_rmse:.2f}")
    joblib.dump(demand_pipe, MODELS_DIR / "demand_model.pkl")
    logger.info("ML Pipeline complete. All models saved.")
    return {
        "status": "success",
        "delay_rmse": delay_rmse,
        "risk_accuracy": acc,
        "demand_rmse": demand_rmse,
        **_last_build_meta,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    train_all()
