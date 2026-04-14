"""
Currency Utility — tenant-aware amount formatting with INR as primary currency.

Resolution order for tenant currency:
  1. Redis key  currency:{tenant_id}   (set via POST /admin/currency)
  2. Env var    DEFAULT_CURRENCY        (deployment-level default)
  3. "INR"                              (hard default — Indian freight market)

Supported currencies: INR, USD, EUR, GBP, SGD, AED
All amounts stored internally as USD; converted at display/report time.
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)

# Symbol and locale formatting per currency code
_CURRENCY_META = {
    "INR": {"symbol": "₹",  "divisor": 100_000, "unit": "L",   "large_unit": "Cr",  "large_divisor": 10_000_000},
    "USD": {"symbol": "$",  "divisor": 1_000,   "unit": "K",   "large_unit": "M",   "large_divisor": 1_000_000},
    "EUR": {"symbol": "€",  "divisor": 1_000,   "unit": "K",   "large_unit": "M",   "large_divisor": 1_000_000},
    "GBP": {"symbol": "£",  "divisor": 1_000,   "unit": "K",   "large_unit": "M",   "large_divisor": 1_000_000},
    "SGD": {"symbol": "S$", "divisor": 1_000,   "unit": "K",   "large_unit": "M",   "large_divisor": 1_000_000},
    "AED": {"symbol": "AED","divisor": 1_000,   "unit": "K",   "large_unit": "M",   "large_divisor": 1_000_000},
}
_DEFAULT_CURRENCY = "INR"


def get_tenant_currency(tenant_id: str) -> str:
    """
    Returns the display currency for a tenant.
    Checks Redis first, then env var, then defaults to INR.
    """
    import os
    try:
        from app.Db.redis_client import get_redis
        r = get_redis()
        if r:
            cached = r.get(f"currency:{tenant_id}")
            if cached:
                code = cached.decode() if isinstance(cached, bytes) else cached
                if code in _CURRENCY_META:
                    return code
    except Exception:
        pass
    env_default = os.environ.get("DEFAULT_CURRENCY", _DEFAULT_CURRENCY).upper()
    return env_default if env_default in _CURRENCY_META else _DEFAULT_CURRENCY


def set_tenant_currency(tenant_id: str, currency_code: str) -> bool:
    """Persists the tenant's display currency to Redis. Returns True on success."""
    code = currency_code.upper()
    if code not in _CURRENCY_META:
        return False
    try:
        from app.Db.redis_client import get_redis
        r = get_redis()
        if r:
            r.setex(f"currency:{tenant_id}", 86_400 * 30, code)
            return True
    except Exception as e:
        log.warning(f"[currency] Failed to persist currency for {tenant_id}: {e}")
    return False


def convert_from_usd(amount_usd: float, target_currency: str) -> float:
    """
    Converts a USD amount to the target currency.
    Uses the FX utility for live rates; falls back to hardcoded rates.
    """
    if target_currency == "USD":
        return amount_usd
    try:
        if target_currency == "INR":
            from app.utils.fx import get_usd_to_inr
            return amount_usd * get_usd_to_inr()
        # For other currencies use exchangerate-api fallback rates
        _FALLBACK_RATES = {"EUR": 0.92, "GBP": 0.79, "SGD": 1.34, "AED": 3.67}
        return amount_usd * _FALLBACK_RATES.get(target_currency, 1.0)
    except Exception:
        return amount_usd


def fmt(amount_usd: float, tenant_id: str, compact: bool = True) -> str:
    """
    Formats a USD amount into the tenant's display currency.

    compact=True  → ₹12.4L  or  $1.2M   (for narratives and dashboards)
    compact=False → ₹12,40,000           (for reports and tables)

    Examples (INR, rate=84):
        fmt(14_762, "t1")           → "₹12.4L"
        fmt(14_762, "t1", False)    → "₹12,40,008"
        fmt(1_200_000, "t1")        → "₹10.1Cr"
    """
    currency = get_tenant_currency(tenant_id)
    meta = _CURRENCY_META.get(currency, _CURRENCY_META["USD"])
    converted = convert_from_usd(amount_usd, currency)

    symbol = meta["symbol"]

    if compact:
        if abs(converted) >= meta["large_divisor"]:
            return f"{symbol}{converted / meta['large_divisor']:.1f}{meta['large_unit']}"
        if abs(converted) >= meta["divisor"]:
            return f"{symbol}{converted / meta['divisor']:.1f}{meta['unit']}"
        return f"{symbol}{converted:,.0f}"

    # Full format with Indian comma grouping for INR
    if currency == "INR":
        return f"₹{_inr_format(converted)}"
    return f"{symbol}{converted:,.2f}"


def _inr_format(amount: float) -> str:
    """Indian number formatting: 12,40,000 (lakh grouping)."""
    s = f"{abs(amount):.0f}"
    if len(s) <= 3:
        result = s
    else:
        result = s[-3:]
        s = s[:-3]
        while len(s) > 2:
            result = s[-2:] + "," + result
            s = s[:-2]
        if s:
            result = s + "," + result
    return ("-" if amount < 0 else "") + result


def symbol(tenant_id: str) -> str:
    """Returns just the currency symbol for the tenant."""
    currency = get_tenant_currency(tenant_id)
    return _CURRENCY_META.get(currency, _CURRENCY_META["USD"])["symbol"]
