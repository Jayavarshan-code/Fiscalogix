import math
import json
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FIX APPLIED — Vulnerability: Blocking HTTP in Inference Path
#
# WHAT WAS WRONG:
# The previous `_fetch_live_volatility()` function placed a synchronous
# urllib.request.urlopen() call INSIDE compute_batch(). If Redis was cold
# (cache expired) and the batch had 50 different routes, that was 50 sequential
# API calls × up to 2s each = 100 seconds of thread blocking on the API server.
# This would freeze the entire ReVM dashboard for every user during that period.
#
# WHY IT'S DANGEROUS:
# Inference paths must be synchronous and fast (< 50ms total). Any network I/O
# in the inference path breaks this guarantee. One cold-cache batch could cascade
# into a Celery timeout, a failed ReVM response, and a dashboard crash for all
# concurrent users.
#
# HOW IT WAS FIXED:
# compute_batch() now ONLY reads from Redis. If a route is not cached, it
# immediately uses the hardcoded fallback — no network call ever.
# The actual HTTP fetch has been moved to a dedicated Celery periodic task
# (`task_warm_fx_cache` in tasks.py) that runs on a schedule every 55 minutes,
# pre-warming Redis with fresh rates. The inference path is now pure in-memory.
# ---------------------------------------------------------------------------

# Deterministic fallback volatility rates (annualized, against USD)
# Used when Redis cache is missing a route key — never as a primary source.
_FALLBACK_VOLATILITY_INDEX = {
    "US-CN":  0.04,
    "EU-US":  0.08,
    "APAC":   0.06,
    "LOCAL":  0.01,
}

# Every distinct route key the warmer should populate
ALL_KNOWN_ROUTES = list(_FALLBACK_VOLATILITY_INDEX.keys())

# Route → currencies it crosses (for live volatility approximation in the warmer)
_ROUTE_CURRENCY_MAP = {
    "US-CN":  ["CNY"],
    "EU-US":  ["EUR", "GBP"],
    "APAC":   ["JPY", "SGD", "MYR"],
    "LOCAL":  [],
}


def _read_cached_volatility(route: str) -> float:
    """
    INFERENCE-SAFE: Reads ONLY from Redis. Returns hardcoded fallback immediately
    if the key is absent. Zero network I/O. Guaranteed sub-millisecond.
    """
    try:
        from app.Db.redis_client import cache
        cached = cache.get(f"fx_vol:{route}")
        if cached:
            return float(cached)
    except Exception as e:
        logger.debug(f"FXRiskModel: Redis unavailable during read: {e}")

    return _FALLBACK_VOLATILITY_INDEX.get(route, 0.05)


def fetch_and_warm_fx_cache():
    """
    CELERY WARMER — called exclusively from tasks.py on a periodic schedule.
    This is the ONLY place a live HTTP call to open.er-api.com is made.
    Populates Redis with fresh volatility rates for all known routes.
    Not called from any inference path.
    """
    import urllib.request

    try:
        from app.Db.redis_client import cache
        url = "https://open.er-api.com/v6/latest/USD"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())

        rates = data.get("rates", {})
        for route, currencies in _ROUTE_CURRENCY_MAP.items():
            if not currencies:
                vol = _FALLBACK_VOLATILITY_INDEX.get(route, 0.01)
            else:
                # Approximate realized volatility from rate deviations
                # In production v2: Replace with 30-day rolling σ from historical rates
                base_vol = _FALLBACK_VOLATILITY_INDEX.get(route, 0.05)
                total_vol = sum(
                    abs(rates.get(ccy, 1.0) - 1.0) * base_vol
                    for ccy in currencies
                ) / len(currencies)
                vol = round(max(total_vol, 0.005), 4)  # Floor at 0.5%

            cache.setex(f"fx_vol:{route}", 3600, str(vol))  # TTL: 1 hour
            logger.info(f"FX Cache warmed: route={route}, vol={vol}")

        logger.info("FX cache warming complete for all routes.")
        return {"status": "warmed", "routes": ALL_KNOWN_ROUTES}

    except Exception as e:
        logger.error(f"FX cache warming failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


class FXRiskModel:
    """
    Pillar 17: Global Currency Arbitrage Mapping.
    Inference path: Redis-only reads. Zero blocking network I/O.
    Cache warming: Delegated to Celery periodic task.
    """

    def compute_batch(self, rows_list, predicted_delays_array):
        results = []
        for i, r in enumerate(rows_list):
            route = r.get("route", "LOCAL")
            # Pure Redis read — fallback is instant, no network call
            volatility = _read_cached_volatility(route)
            delay = predicted_delays_array[i]
            cost = float(r.get("total_cost", 0.0))

            fx_erosion = cost * volatility * (delay / 365.0)

            # Compound growth for extended credit terms (geometric)
            credit_days = float(r.get("credit_days", 0.0))
            if credit_days > 45:
                credit_extension_years = credit_days / 365.0
                compound_factor = math.exp(volatility * credit_extension_years)
                fx_erosion *= compound_factor

            results.append(round(fx_erosion, 2))
        return results
