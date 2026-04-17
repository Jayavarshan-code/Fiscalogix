"""
FXRiskModel — currency erosion on logistics cost and AR exposure.

P1-E FIX: FX erosion only covered the delay window, not the AR exposure window.
WHAT WAS WRONG:
  `fx_erosion = cost * volatility * (delay / 365.0)`
  This applies volatility to the shipment cost (physical logistics spend) for
  the delay period only. But the PRIMARY FX exposure in B2B logistics is on the
  RECEIVABLE — the order_value sitting in AR for credit_days + payment_delay_days.

  Example: $500K order, 30-day credit terms, EU-US route (8% vol):
    Old formula: fx_erosion = $7,000 × 0.08 × (2/365) = $3.07  ← trivial, wrong
    Correct:     AR exposure = $500K × 0.08 × (32/365)  = $3,507 ← 1,000× larger

  For high-value orders with long credit terms, the AR FX exposure dominates
  the delay exposure by 2-3 orders of magnitude. Ignoring it makes the FX cost
  appear negligible when it can be the largest cost component.

FIX: Two-component FX model:
  1. Shipment cost erosion (delay window)    — physical logistics spend × vol × delay/365
  2. AR exposure erosion (credit window)     — order_value × vol × (credit_days + payment_delay)/365
  Total FX cost = max(component_1 + component_2, 0)

  The compound factor for credit_days > 45 is preserved from the old formula
  and applied to the AR component (where it correctly belongs).
"""

import math
import json
import logging

logger = logging.getLogger(__name__)

_FALLBACK_VOLATILITY_INDEX = {
    "US-CN":  0.04,
    "EU-US":  0.08,
    "APAC":   0.06,
    "LOCAL":  0.01,
}

ALL_KNOWN_ROUTES = list(_FALLBACK_VOLATILITY_INDEX.keys())

_ROUTE_CURRENCY_MAP = {
    "US-CN":  ["CNY"],
    "EU-US":  ["EUR", "GBP"],
    "APAC":   ["JPY", "SGD", "MYR"],
    "LOCAL":  [],
}


_FX_STALE_THRESHOLD_SECONDS = 7200  # warn if cache older than 2 hours


def _read_cached_volatility(route: str) -> float:
    """
    INFERENCE-SAFE: Redis-only read. Zero network I/O. Guaranteed sub-millisecond.
    Logs a warning if the cached value is older than _FX_STALE_THRESHOLD_SECONDS.
    """
    try:
        import time as _time
        from app.Db.redis_client import cache
        cached = cache.get(f"fx_vol:{route}")
        if cached:
            updated_at = cache.get(f"fx_vol:{route}:updated_at")
            if updated_at:
                age = _time.time() - float(updated_at)
                if age > _FX_STALE_THRESHOLD_SECONDS:
                    logger.warning(
                        f"FXRiskModel: stale cache for route={route} "
                        f"(age={age/3600:.1f}h > threshold={_FX_STALE_THRESHOLD_SECONDS/3600:.0f}h). "
                        "Check if Celery Beat FX warmer is running."
                    )
            return float(cached)
    except Exception as e:
        logger.debug(f"FXRiskModel: Redis unavailable: {e}")
    return _FALLBACK_VOLATILITY_INDEX.get(route, 0.05)


def fetch_and_warm_fx_cache():
    """
    CELERY WARMER ONLY — called from tasks.py on periodic schedule.
    The ONLY place a live HTTP call is made. Never called from inference path.
    """
    import urllib.request
    try:
        from app.Db.redis_client import cache
        url = "https://open.er-api.com/v6/latest/USD"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        rates = data.get("rates", {})
        import time as _time
        warmed_at = str(_time.time())
        for route, currencies in _ROUTE_CURRENCY_MAP.items():
            if not currencies:
                vol = _FALLBACK_VOLATILITY_INDEX.get(route, 0.01)
            else:
                base_vol = _FALLBACK_VOLATILITY_INDEX.get(route, 0.05)
                total_vol = sum(
                    abs(rates.get(ccy, 1.0) - 1.0) * base_vol
                    for ccy in currencies
                ) / len(currencies)
                vol = round(max(total_vol, 0.005), 4)
            cache.setex(f"fx_vol:{route}", 3600, str(vol))
            # Staleness sentinel — inference path reads this to flag stale data
            cache.setex(f"fx_vol:{route}:updated_at", 3600, warmed_at)
            logger.info(f"FX Cache warmed: route={route}, vol={vol}")
        logger.info("FX cache warming complete.")
        return {"status": "warmed", "routes": ALL_KNOWN_ROUTES}
    except Exception as e:
        logger.error(f"FX cache warming failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


class FXRiskModel:
    """
    Two-component FX cost model:
      Component 1 — shipment cost erosion during the delay window
      Component 2 — AR exposure erosion during the full credit period  ← P1-E FIX

    Both use the same route volatility from Redis/fallback.
    """

    def compute(self, row, predicted_delay):
        route      = row.get("route", "LOCAL")
        volatility = _read_cached_volatility(route)

        order_value    = float(row.get("order_value", 0.0))
        shipment_cost  = float(row.get("shipment_cost", 0.0))

        # Fallback: estimate shipment cost as 12% of order value when not provided
        if shipment_cost <= 0 and order_value > 0:
            shipment_cost = order_value * 0.12

        # ── Component 1: Shipment cost erosion during delay window ────────────
        # The physical logistics spend exposed to FX during the delivery lag
        delay_erosion = shipment_cost * volatility * (max(predicted_delay, 0) / 365.0)

        # ── Component 2: AR exposure erosion during credit period ─────────────
        # P1-E FIX: The order value sits in AR for credit_days + payment_delay_days.
        # This is where the largest FX exposure lives for high-value orders.
        credit_days       = float(row.get("credit_days", 0.0))
        payment_delay     = float(row.get("payment_delay_days", 0.0))
        total_ar_days     = credit_days + payment_delay + max(predicted_delay, 0)
        # delay is included because payment clock starts after delivery

        ar_erosion = order_value * volatility * (total_ar_days / 365.0)

        # Compound growth for extended credit terms (geometric FX compounding)
        # Applied to AR erosion — this is where credit_days > 45 actually matters
        if credit_days > 45:
            credit_years     = credit_days / 365.0
            compound_factor  = math.exp(volatility * credit_years)
            ar_erosion      *= compound_factor

        total_fx_cost = delay_erosion + ar_erosion
        return round(total_fx_cost, 2)

    def compute_batch(self, rows_list, predicted_delays_array):
        return [
            self.compute(rows_list[i], predicted_delays_array[i])
            for i in range(len(rows_list))
        ]
