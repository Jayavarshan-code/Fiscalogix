"""
FX Rate Utility — USD ↔ INR conversion with Redis caching.

Resolution order (highest authority wins):
  1. Redis cache  (key: fx:USD_INR, refreshed daily by Celery)
  2. FreeCurrencyAPI public endpoint (no key required, ~1s)
  3. Hardcoded fallback  84.5  (never fails)

The rate is intentionally fetched once per day — this is a CFO dashboard,
not a forex terminal. Daily refresh is more than sufficient.
"""

import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

FALLBACK_RATE = 84.5          # USD → INR fallback
REDIS_KEY     = "fx:USD_INR"
REDIS_TTL     = 86_400        # 24 hours


def _fetch_live_rate() -> Optional[float]:
    """Fetch USD→INR from a public API. Returns None on any failure."""
    try:
        import urllib.request, json
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
            rate = float(data["rates"]["INR"])
            log.info(f"[fx] Fetched live rate: 1 USD = {rate:.2f} INR")
            return rate
    except Exception as exc:
        log.warning(f"[fx] Live rate fetch failed: {exc}")
        return None


def get_usd_to_inr() -> float:
    """
    Return the current USD→INR rate.
    Tries Redis first, then live API, then fallback.
    """
    # 1. Try Redis
    try:
        from app.Db.redis_client import get_redis
        r = get_redis()
        if r:
            cached = r.get(REDIS_KEY)
            if cached:
                return float(cached)
    except Exception:
        pass

    # 2. Try live API
    rate = _fetch_live_rate()

    # 3. Cache in Redis if we got a live rate
    if rate:
        try:
            from app.Db.redis_client import get_redis
            r = get_redis()
            if r:
                r.setex(REDIS_KEY, REDIS_TTL, str(rate))
        except Exception:
            pass
        return rate

    # 4. Hardcoded fallback — always succeeds
    log.warning(f"[fx] Using fallback rate: {FALLBACK_RATE}")
    return FALLBACK_RATE


def usd_to_inr(amount_usd: float) -> float:
    """Convert a USD amount to INR using the current rate."""
    return amount_usd * get_usd_to_inr()


def inr_to_usd(amount_inr: float) -> float:
    """Convert an INR amount to USD using the current rate."""
    return amount_inr / get_usd_to_inr()
