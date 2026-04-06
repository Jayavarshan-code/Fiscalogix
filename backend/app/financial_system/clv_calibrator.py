"""
CLVCalibrator — Per-account Customer Lifetime Value calibration
from actual shipment history.

Gap 7 Fix:
  FutureImpactModel.compute() uses static tier multipliers:
    enterprise=12x, strategic=8x, growth=5x, standard=3x, spot=1.5x
  These are industry benchmarks, not per-customer reality.

  Problem: A customer labelled "enterprise" who has placed exactly one order
  in 18 months is not worth 12x CLV. Conversely, a "spot" customer who
  reorders every 3 weeks with growing basket size is massively undervalued
  at 1.5x. The static tiers make the future_loss signal noisy and unreliable
  for any customer with real order history.

Solution:
  Compute a History-Adjusted CLV Multiplier from the actual repeat-purchase
  data in dw_shipment_facts:

    base_multiplier       = tier benchmark (Bain/Reichheld)
    actual_repeat_ratio   = orders_last_12m / max(orders_all_time, 1)
    avg_order_value_12m   = mean order_value of last 12-month orders
    baseline_order_value  = mean order_value of all orders

    growth_signal         = avg_order_value_12m / max(baseline_order_value, 1)
    frequency_signal      = orders_last_12m / annualised_expected_frequency

    calibrated_multiplier = base_multiplier
                            × clip(frequency_signal, 0.4, 2.5)
                            × clip(growth_signal,    0.5, 2.0)

  Blending:
    If ≥ MIN_ORDERS_FOR_CALIBRATION history rows exist → full calibration
    If some history but insufficient → blend (60% history, 40% tier)
    If no history → return None (caller uses pure tier multiplier)

  The result is cached in Redis per customer_id with a 24-hour TTL so the
  DB is not queried on every portfolio run.

Redis key schema:
  clv:calibration:{tenant_id}:{customer_id}  → JSON blob
"""

import json
import logging
import math
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Minimum orders in history to trust the calibration fully
MIN_ORDERS_FOR_CALIBRATION = 5

# Minimum orders to blend (partial confidence)
MIN_ORDERS_FOR_BLEND = 2

# Cache TTL: 24 hours — purchase patterns don't change intraday
_REDIS_TTL = 3600 * 24

_REDIS_KEY_FMT = "clv:calibration:{tenant_id}:{customer_id}"

# Annualised expected order frequency by tier (orders/year)
# Used to normalise frequency_signal when history < 12 months
_TIER_ANNUAL_FREQUENCY = {
    "enterprise": 24,   # 2 shipments/month — JIT or blanket PO schedules
    "strategic":  12,   # 1 shipment/month
    "growth":     6,    # bi-monthly
    "standard":   4,    # quarterly
    "spot":       1,    # one-off
    "trial":      1,
}

# Hard bounds on the calibrated multiplier to prevent extreme outliers
_MULTIPLIER_FLOOR = 0.5
_MULTIPLIER_CEIL  = 20.0


class CLVCalibrator:
    """
    Computes and caches per-account CLV multipliers from shipment history.

    Usage (called once per portfolio run before financial agents):
        calibrator = CLVCalibrator()
        calibrations = calibrator.calibrate_batch(data, tenant_id="acme")
        # calibrations: {customer_id: calibration_dict}
        # Stamp onto each row: row["clv_calibration"] = calibrations.get(customer_id)
    """

    def __init__(self):
        try:
            from app.Db.redis_client import cache
            self._cache = cache
        except Exception:
            self._cache = None
            logger.warning("CLVCalibrator: Redis unavailable — no caching, DB queried per run.")

        self._base_tier_multipliers = {
            "enterprise": 12.0,
            "strategic":   8.0,
            "growth":      5.0,
            "standard":    3.0,
            "spot":        1.5,
            "trial":       1.0,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def calibrate_batch(
        self,
        rows: List[dict],
        tenant_id: str = "default_tenant",
    ) -> Dict[str, Optional[dict]]:
        """
        Calibrates CLV multipliers for all unique customer_ids in the portfolio.

        Returns:
            {customer_id: calibration_dict | None}
            None means no history — caller uses pure tier multiplier.

        calibration_dict shape:
            {
                "calibrated_multiplier": float,
                "base_tier_multiplier":  float,
                "frequency_signal":      float,
                "growth_signal":         float,
                "orders_12m":            int,
                "orders_all_time":       int,
                "avg_order_value_12m":   float,
                "confidence":            "full" | "blended" | "tier_only",
                "customer_id":           str,
                "tier":                  str,
            }
        """
        unique_customers: Dict[str, str] = {}   # customer_id → customer_tier
        for row in rows:
            cid = str(row.get("customer_id", "")).strip()
            if cid:
                unique_customers[cid] = str(row.get("customer_tier", "standard")).lower().strip()

        if not unique_customers:
            return {}

        # Check Redis cache first
        results: Dict[str, Optional[dict]] = {}
        uncached: Dict[str, str] = {}

        for cid, tier in unique_customers.items():
            cached = self._get_cached(tenant_id, cid)
            if cached is not None:
                results[cid] = cached
            else:
                uncached[cid] = tier

        # Fetch history for uncached customers in a single batch query
        if uncached:
            history = self._fetch_history_batch(list(uncached.keys()), tenant_id)
            for cid, tier in uncached.items():
                customer_history = history.get(cid, [])
                calibration = self._compute_calibration(cid, tier, customer_history)
                results[cid] = calibration
                if calibration is not None:
                    self._cache_result(tenant_id, cid, calibration)

        return results

    # ── Core calibration math ─────────────────────────────────────────────────

    def _compute_calibration(
        self,
        customer_id: str,
        tier: str,
        history: List[dict],
    ) -> Optional[dict]:
        """
        Computes the calibrated CLV multiplier from raw history rows.

        Each history row: {order_value, days_ago}
        """
        base_mult = self._base_tier_multipliers.get(tier, 3.0)
        annual_freq = _TIER_ANNUAL_FREQUENCY.get(tier, 4)

        if not history:
            return None  # No history — caller uses pure tier multiplier

        orders_all_time = len(history)
        orders_12m = [r for r in history if r.get("days_ago", 999) <= 365]
        n_12m = len(orders_12m)

        # ── Growth signal: are recent orders bigger? ──────────────────────────
        all_values = [r.get("order_value", 0) for r in history]
        recent_values = [r.get("order_value", 0) for r in orders_12m]

        baseline_avg = sum(all_values) / max(len(all_values), 1)
        recent_avg   = sum(recent_values) / max(len(recent_values), 1) if recent_values else baseline_avg

        growth_signal = min(max(recent_avg / max(baseline_avg, 1.0), 0.5), 2.0)

        # ── Frequency signal: ordering faster or slower than tier baseline? ───
        # Annualise: if customer made n_12m orders in last 12m vs annual_freq baseline
        frequency_signal = min(max(n_12m / max(annual_freq, 1), 0.4), 2.5)

        # ── Calibrated multiplier ─────────────────────────────────────────────
        calibrated = base_mult * frequency_signal * growth_signal
        calibrated = round(min(max(calibrated, _MULTIPLIER_FLOOR), _MULTIPLIER_CEIL), 3)

        # ── Confidence level ──────────────────────────────────────────────────
        if orders_all_time >= MIN_ORDERS_FOR_CALIBRATION and n_12m >= 2:
            confidence = "full"
            final_multiplier = calibrated
        elif orders_all_time >= MIN_ORDERS_FOR_BLEND:
            confidence = "blended"
            # 60% calibrated, 40% base tier — partial trust in thin history
            final_multiplier = round(0.60 * calibrated + 0.40 * base_mult, 3)
        else:
            # Only 1 order — barely any signal, use mostly tier
            confidence = "blended_thin"
            final_multiplier = round(0.25 * calibrated + 0.75 * base_mult, 3)

        return {
            "customer_id":           customer_id,
            "tier":                  tier,
            "calibrated_multiplier": final_multiplier,
            "base_tier_multiplier":  base_mult,
            "frequency_signal":      round(frequency_signal, 4),
            "growth_signal":         round(growth_signal,    4),
            "orders_12m":            n_12m,
            "orders_all_time":       orders_all_time,
            "avg_order_value_12m":   round(recent_avg, 2),
            "confidence":            confidence,
        }

    # ── DB query ──────────────────────────────────────────────────────────────

    def _fetch_history_batch(
        self,
        customer_ids: List[str],
        tenant_id: str,
    ) -> Dict[str, List[dict]]:
        """
        Batch-queries dw_shipment_facts for the order history of all
        provided customer_ids (single SQL round-trip).

        Returns: {customer_id: [{order_value, days_ago}, ...]}
        """
        if not customer_ids:
            return {}

        try:
            from sqlalchemy import text
            from app.Db.connections import engine as db_engine

            # Use parameterised IN clause to avoid N+1 and SQL injection
            placeholders = ", ".join(f":cid_{i}" for i in range(len(customer_ids)))
            query = text(f"""
                SELECT
                    customer_id,
                    total_value_usd                              AS order_value,
                    (CURRENT_DATE - created_at::date)::int      AS days_ago
                FROM dw_shipment_facts
                WHERE tenant_id = :tenant_id
                  AND customer_id IN ({placeholders})
                  AND created_at IS NOT NULL
                  AND total_value_usd IS NOT NULL
                  AND total_value_usd > 0
                ORDER BY customer_id, created_at DESC
                LIMIT 5000
            """)
            params = {"tenant_id": tenant_id}
            params.update({f"cid_{i}": cid for i, cid in enumerate(customer_ids)})

            with db_engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()

            history: Dict[str, List[dict]] = {cid: [] for cid in customer_ids}
            for row in rows:
                cid = str(row.customer_id)
                if cid in history:
                    history[cid].append({
                        "order_value": float(row.order_value),
                        "days_ago":    int(row.days_ago),
                    })

            queried = sum(len(v) for v in history.values())
            logger.info(
                f"CLVCalibrator: fetched {queried} history rows for "
                f"{len(customer_ids)} customers (tenant={tenant_id})."
            )
            return history

        except Exception as e:
            logger.warning(
                f"CLVCalibrator._fetch_history_batch failed ({type(e).__name__}: {e}). "
                "Returning empty history — FutureImpactModel will use tier multipliers."
            )
            return {cid: [] for cid in customer_ids}

    # ── Redis helpers ─────────────────────────────────────────────────────────

    def _get_cached(self, tenant_id: str, customer_id: str) -> Optional[dict]:
        if not self._cache:
            return None
        try:
            key = _REDIS_KEY_FMT.format(tenant_id=tenant_id, customer_id=customer_id)
            val = self._cache.get(key)
            if val:
                return json.loads(val)
        except Exception:
            pass
        return None

    def _cache_result(self, tenant_id: str, customer_id: str, data: dict):
        if not self._cache:
            return
        try:
            key = _REDIS_KEY_FMT.format(tenant_id=tenant_id, customer_id=customer_id)
            self._cache.setex(key, _REDIS_TTL, json.dumps(data))
        except Exception as e:
            logger.debug(f"CLVCalibrator: Redis write failed for {customer_id} — {e}")
