"""
FX Rate Utility — USD ↔ multi-currency conversion with Redis caching.

Resolution order (highest authority wins):
  1. Redis cache  (key: fx:USD_MULTI, refreshed daily by Celery)
  2. Frankfurter public API (no key required, ECB-backed, ~1s)
  3. Hardcoded fallback rates (never fails)

The rate is intentionally fetched once per day — this is a CFO dashboard,
not a forex terminal. Daily refresh is more than sufficient.
"""

import json
import logging
from typing import Dict, Optional

log = logging.getLogger(__name__)

_FALLBACK_RATES: Dict[str, float] = {
    "INR": 84.5,
    "EUR": 0.92,
    "GBP": 0.79,
    "SGD": 1.34,
    "AED": 3.67,
}

_SUPPORTED_CURRENCIES = list(_FALLBACK_RATES.keys())
_MULTI_RATES_KEY = "fx:USD_MULTI"
_REDIS_TTL = 86_400  # 24 hours

# Backwards compat aliases
FALLBACK_RATE = _FALLBACK_RATES["INR"]
REDIS_KEY = "fx:USD_INR"
REDIS_TTL = _REDIS_TTL


def _fetch_live_rates() -> Optional[Dict[str, float]]:
    """Fetch all supported rates from Frankfurter (ECB-backed, no API key)."""
    try:
        import urllib.request
        symbols = ",".join(_SUPPORTED_CURRENCIES)
        url = f"https://api.frankfurter.app/latest?base=USD&symbols={symbols}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        rates = {k: float(v) for k, v in data.get("rates", {}).items()}
        if rates:
            log.info(f"[fx] Fetched live rates: {rates}")
            return rates
    except Exception as exc:
        log.warning(f"[fx] Frankfurter fetch failed: {exc}")
    return None


def get_usd_rates() -> Dict[str, float]:
    """
    Return current USD→X rates for all supported currencies.
    Resolution: Redis → Frankfurter API → hardcoded fallback.
    """
    try:
        from app.Db.redis_client import get_redis
        r = get_redis()
        if r:
            cached = r.get(_MULTI_RATES_KEY)
            if cached:
                return json.loads(cached)
    except Exception:
        pass

    rates = _fetch_live_rates()
    if rates:
        try:
            from app.Db.redis_client import get_redis
            r = get_redis()
            if r:
                r.setex(_MULTI_RATES_KEY, _REDIS_TTL, json.dumps(rates))
                if "INR" in rates:
                    r.setex(REDIS_KEY, _REDIS_TTL, str(rates["INR"]))
        except Exception:
            pass
        return rates

    log.warning("[fx] Using hardcoded fallback rates")
    return dict(_FALLBACK_RATES)


def warm_fx_cache() -> Dict[str, float]:
    """Called by Celery Beat to pre-populate Redis. Returns warmed rates."""
    rates = _fetch_live_rates()
    if not rates:
        log.error("[fx] warm_fx_cache: live fetch failed, Redis not updated")
        return {}
    try:
        from app.Db.redis_client import get_redis
        r = get_redis()
        if r:
            r.setex(_MULTI_RATES_KEY, _REDIS_TTL, json.dumps(rates))
            if "INR" in rates:
                r.setex(REDIS_KEY, _REDIS_TTL, str(rates["INR"]))
    except Exception as exc:
        log.error(f"[fx] warm_fx_cache: Redis write failed: {exc}")
    return rates


def get_usd_to_inr() -> float:
    """Return the current USD→INR rate."""
    return get_usd_rates().get("INR", FALLBACK_RATE)


def usd_to_inr(amount_usd: float) -> float:
    """Convert a USD amount to INR using the current rate."""
    return amount_usd * get_usd_to_inr()


def inr_to_usd(amount_inr: float) -> float:
    """Convert an INR amount to USD using the current rate."""
    return amount_inr / get_usd_to_inr()
