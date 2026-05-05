"""
FeatureBuilder — single source of truth for cross-term feature engineering.

Called by BOTH train_models.py (training) and risk_engine.py (inference),
guaranteeing that training and serving always see identical feature spaces
and eliminating training-serving skew.

Why interaction features fix the linearity problem:
  - A linear model on [cost_ratio, delay_days] cannot distinguish
    a high-cost / low-delay shipment from a low-cost / high-delay one
    with the same raw sum. The cross-term (cost_ratio * delay_days)
    breaks that degeneracy.
  - Tree-based models (XGBoost, GBM) can learn these internally, but
    explicit cross-terms speed convergence and improve the fallback model
    which has fewer parameters.
"""

import datetime
from typing import Any, Dict

# ── Seasonality index: month (1-12) → industry demand multiplier ─────────────
# Source: Freightos Global Freight Pricing Index, Flexport Commodity Seasonality
_SEASONALITY: Dict[str, list] = {
    "fmcg":        [1.05, 0.95, 1.00, 0.95, 0.98, 0.95, 1.00, 1.05, 1.10, 1.20, 1.40, 1.30],
    "automotive":  [1.15, 1.10, 1.20, 1.10, 1.05, 0.95, 0.90, 0.95, 1.05, 1.10, 1.05, 1.00],
    "pharma":      [1.00, 1.00, 1.05, 1.00, 0.95, 0.95, 0.95, 1.00, 1.05, 1.10, 1.15, 1.10],
    "electronics": [1.00, 0.95, 0.98, 0.95, 0.98, 1.00, 1.05, 1.10, 1.20, 1.25, 1.35, 1.15],
    "default":     [1.00, 0.97, 1.00, 0.98, 1.00, 0.97, 0.98, 1.00, 1.02, 1.05, 1.10, 1.05],
}

# ── Cargo holding rate: cargo_type → daily capital lock-up rate ───────────────
_HOLDING_RATES: Dict[str, float] = {
    "perishable":    0.012,   # cold chain + spoilage risk
    "pharma":        0.010,   # compliance + temperature
    "electronics":   0.008,   # obsolescence risk
    "luxury":        0.006,   # insurance + security
    "automotive":    0.005,   # assembly-line dependency
    "general_cargo": 0.003,
    "bulk":          0.002,
    "default":       0.003,
}

# ── Route complexity: coarse route string → float 1.0–4.0 ────────────────────
_ROUTE_COMPLEXITY: Dict[str, float] = {
    "local":          1.0,
    "domestic":       1.4,
    "regional":       2.0,
    "international":  2.8,
    "transcontinental": 3.5,
    "us_cn":  3.8, "cn_us": 3.8,
    "eu_us":  3.2, "us_eu": 3.2,
    "cn_eu":  3.6, "eu_cn": 3.6,
    "us_mx":  1.8, "mx_us": 1.8,
    "apac":   2.5,
    "in_eu":  3.3, "eu_in": 3.3,
}


def _seasonality_idx(vertical: str, month: int) -> float:
    arr = _SEASONALITY.get(str(vertical).lower(), _SEASONALITY["default"])
    return arr[(month - 1) % 12]


def _holding_rate(cargo_type: str) -> float:
    return _HOLDING_RATES.get(str(cargo_type).lower(), _HOLDING_RATES["default"])


def _route_complexity_score(route: str) -> float:
    key = str(route).lower().replace(" ", "_").replace("-", "_")
    val = _ROUTE_COMPLEXITY.get(key)
    if val:
        return val
    for k, v in _ROUTE_COMPLEXITY.items():
        if k in key:
            return v
    return _ROUTE_COMPLEXITY["international"]


def build(row: Dict[str, Any], spatial_severity: float = 0.0) -> Dict[str, Any]:
    """
    Enriches a raw shipment dict with derived scalars and interaction features.
    All downstream models (XGBoost, GBM fallback, heuristic) must call this
    before constructing their feature vectors so training/inference match.

    Args:
        row:              raw dict with keys: order_value, total_cost,
                          credit_days, delay_days, contribution_profit,
                          cargo_type, industry_vertical, route, carrier
        spatial_severity: float [0,1] from SpatialRiskInjector.
                          0.0 when injector is unavailable (safe fallback).

    Returns:
        new dict with all original keys plus derived + interaction features.
    """
    order_value = max(float(row.get("order_value") or 1), 1.0)
    total_cost  = float(row.get("total_cost") or 0)
    credit_days = float(row.get("credit_days") or 0)
    delay_days  = float(row.get("delay_days") or 0)
    margin      = float(
        row.get("contribution_profit") if row.get("contribution_profit") is not None
        else (order_value - total_cost)
    )
    cargo_type  = str(row.get("cargo_type") or "general_cargo")
    vertical    = str(row.get("industry_vertical") or "default")
    route       = str(row.get("route") or "domestic")
    carrier_key = str(row.get("carrier") or "unknown").lower().replace(" ", "_")

    # Carrier reliability: try live registry first, fall back to 0.75
    try:
        from app.financial_system.delay_model import CARRIER_RELIABILITY_REGISTRY
        carrier_reliability = CARRIER_RELIABILITY_REGISTRY.get(carrier_key, 0.75)
    except Exception:
        carrier_reliability = 0.75

    # ── Core derived scalars ──────────────────────────────────────────────────
    cost_ratio        = total_cost / order_value
    margin_pct        = margin / order_value
    carrier_risk      = 1.0 - carrier_reliability
    route_complexity  = _route_complexity_score(route)
    holding_rate      = _holding_rate(cargo_type)
    month             = datetime.datetime.utcnow().month
    seasonality_idx   = _seasonality_idx(vertical, month)

    # ── Interaction terms ─────────────────────────────────────────────────────
    # Each term encodes a relationship that a flat feature set cannot express:

    # Cost pressure amplified by time: expensive + long delay = dangerous
    cost_x_delay          = cost_ratio * delay_days

    # Carrier weakness compounded by route difficulty
    carrier_x_route       = carrier_risk * route_complexity

    # Live disruption severity scaled by route exposure length
    spatial_x_route       = spatial_severity * route_complexity

    # Disruption × holding cost: perishable cargo in a port strike = severe
    spatial_x_cargo       = spatial_severity * holding_rate * 100.0

    # Margin erosion: how much margin survives a spatial shock
    margin_x_spatial      = margin_pct * (1.0 - spatial_severity)

    # Seasonal demand pressure × physical holding cost
    seasonal_x_cargo      = seasonality_idx * holding_rate * 100.0

    # Year-normalised credit + delay joint exposure (liquidity drag)
    credit_delay_exposure = credit_days * delay_days / 365.0

    # How thin is margin relative to cost structure (compression ratio)
    margin_compression    = margin_pct / max(cost_ratio, 0.01)

    # 3-way: cost × carrier unreliability × route difficulty — highest-signal term
    risk_pressure         = cost_ratio * carrier_risk * route_complexity

    return {
        **row,
        # Derived scalars
        "cost_ratio":            round(cost_ratio, 6),
        "margin_pct":            round(margin_pct, 6),
        "carrier_reliability":   round(carrier_reliability, 4),
        "carrier_risk":          round(carrier_risk, 4),
        "route_complexity":      round(route_complexity, 4),
        "holding_rate":          round(holding_rate, 6),
        "seasonality_idx":       round(seasonality_idx, 4),
        "spatial_severity":      round(float(spatial_severity), 4),
        # Interaction terms
        "cost_x_delay":          round(cost_x_delay, 6),
        "carrier_x_route":       round(carrier_x_route, 6),
        "spatial_x_route":       round(spatial_x_route, 6),
        "spatial_x_cargo":       round(spatial_x_cargo, 6),
        "margin_x_spatial":      round(margin_x_spatial, 6),
        "seasonal_x_cargo":      round(seasonal_x_cargo, 6),
        "credit_delay_exposure": round(credit_delay_exposure, 6),
        "margin_compression":    round(margin_compression, 6),
        "risk_pressure":         round(risk_pressure, 6),
    }


# ── Column manifests consumed by train_models.py ─────────────────────────────

NUMERIC_FEATURES = [
    # Raw inputs
    "order_value", "total_cost", "credit_days", "delay_days",
    # Derived scalars
    "cost_ratio", "margin_pct", "carrier_reliability", "carrier_risk",
    "route_complexity", "holding_rate", "seasonality_idx", "spatial_severity",
    # Interaction terms
    "cost_x_delay", "carrier_x_route", "spatial_x_route", "spatial_x_cargo",
    "margin_x_spatial", "seasonal_x_cargo", "credit_delay_exposure",
    "margin_compression", "risk_pressure",
]

CATEGORICAL_FEATURES = ["route", "carrier"]
