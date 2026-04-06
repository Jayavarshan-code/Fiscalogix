"""
WACCEngine — Dynamic, market-aware WACC resolution for every shipment row.

Gap 6 Fix: Every shipment's time_cost and future_cost is multiplied by WACC.
A hardcoded 8% is frozen in 2019. In 2022-2023, the riskfree rate rose to 5.25%,
pushing real corporate WACC to 11-14%. Using 8% in that environment understates
capital cost by 37%, making delay-heavy shipments look far cheaper than they are.

Three-tier resolution (highest authority wins):
  Tier 1 — Per-tenant Redis override:  set by admins via POST /admin/wacc
  Tier 2 — Industry-vertical benchmark: Damodaran database, adjusted for
            current market rates (10-year UST pulled by Celery warmer)
  Tier 3 — Hardcoded 8% fallback:      always succeeds; never throws

Redis key schema:
  wacc:tenant:{tenant_id}          → decimal string, e.g. "0.112"
  wacc:market_adjustment           → float string, delta from baseline (e.g. "0.025")
  wacc:industry:{vertical}         → decimal string, pre-adjusted by warmer

Market adjustment logic (in fetch_and_warm_wacc Celery task):
  baseline_rfr = 4.0%  (10-year UST when Damodaran benchmarks were calibrated)
  current_rfr  = fetched live from US Treasury data feed
  adjustment   = current_rfr - baseline_rfr
  All industry benchmarks are shifted by this adjustment.
  If UST fetch fails → adjustment defaults to 0.0 (use raw Damodaran values).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Damodaran Industry WACC Benchmarks
# Source: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html
# Calibration baseline risk-free rate: 4.0% (Jan 2024 Damodaran dataset)
# Updated: 2024. Covers US-listed + global firms by SIC sector.
# ─────────────────────────────────────────────────────────────────────────────
_DAMODARAN_WACC = {
    # industry_vertical key → Damodaran WACC at 4% RFR baseline
    "pharmaceutical":  0.090,   # Biotech/Pharma: 9.0%  (high R&D, patent cliff risk)
    "fmcg":            0.068,   # Consumer Staples: 6.8% (stable cash flows, low beta)
    "automotive":      0.082,   # Auto & Parts: 8.2%     (cyclical, capital intensive)
    "electronics":     0.095,   # Technology Hardware: 9.5% (obsolescence risk)
    "textile":         0.078,   # Apparel/Retail: 7.8%  (fashion cycle risk)
    "industrial":      0.086,   # Industrials: 8.6%     (capex heavy, moderate beta)
    "chemical":        0.088,   # Chemicals: 8.8%       (commodity exposure)
    "logistics":       0.092,   # Transportation/Logistics: 9.2% (asset heavy)
    "default":         0.085,   # Broad market average  (Damodaran overall market)
}

# Baseline risk-free rate at which the Damodaran WACCs above were computed.
_DAMODARAN_BASELINE_RFR = 0.040  # 4.0%

# Hard fallback if Redis is unavailable AND industry vertical is unknown.
_FALLBACK_WACC = 0.085

# Redis key prefix and TTL
_REDIS_TENANT_KEY         = "wacc:tenant:{tenant_id}"
_REDIS_MARKET_ADJ_KEY     = "wacc:market_adjustment"
_REDIS_INDUSTRY_KEY_FMT   = "wacc:industry:{vertical}"
_REDIS_WACC_TTL_SECONDS   = 3600 * 6   # 6 hours — same cadence as Celery Beat task


class WACCEngine:
    """
    Resolves WACC for a single shipment row using 3-tier authority:

      Tier 1. Redis tenant override  →  most accurate (set by CFO/admin)
      Tier 2. Redis-warmed industry   →  market-adjusted Damodaran benchmark
      Tier 3. Module-level fallback   →  always 8.5% (never throws)

    Usage:
        engine = WACCEngine()
        wacc = engine.resolve(row, tenant_id="acme_corp")
    """

    def __init__(self):
        try:
            from app.Db.redis_client import cache
            self._cache = cache
        except Exception:
            self._cache = None
            logger.warning("WACCEngine: Redis unavailable — using Damodaran + fallback only.")

    # ── Public API ────────────────────────────────────────────────────────────

    def resolve(self, row: dict, tenant_id: str = "default_tenant") -> float:
        """
        Returns the correct WACC for this row, validated to [1%, 50%].

        Resolution order:
          1. Per-row explicit wacc field (ERP-sourced, most authoritative per shipment)
          2. Per-tenant Redis override   (admin-set, applies if no per-row value)
          3. Redis-warmed industry WACC  (Damodaran + market adjustment)
          4. Raw Damodaran benchmark     (static, no Redis needed)
          5. Hardcoded fallback 8.5%
        """
        # Step 0: Per-row explicit wacc (ERP export may include it)
        row_wacc = row.get("wacc")
        if row_wacc and isinstance(row_wacc, (int, float)) and row_wacc > 0:
            # Guard against ERP exporting as percentage (e.g. 8.5 instead of 0.085)
            if row_wacc > 1.0:
                row_wacc /= 100.0
            return self._clamp(row_wacc)

        # Step 1: Tenant Redis override
        tenant_override = self._get_tenant_override(tenant_id)
        if tenant_override is not None:
            return tenant_override

        # Step 2: Industry vertical from Redis (warmed + market-adjusted)
        vertical = str(row.get("industry_vertical", "default")).lower().strip()
        cached_industry = self._get_industry_wacc(vertical)
        if cached_industry is not None:
            return cached_industry

        # Step 3: Raw Damodaran (no Redis needed)
        damodaran = _DAMODARAN_WACC.get(vertical, _DAMODARAN_WACC["default"])

        # Apply market adjustment if we can read it from Redis
        adjustment = self._get_market_adjustment()
        final = damodaran + adjustment

        return self._clamp(final)

    def resolve_batch(self, records: list, tenant_id: str = "default_tenant") -> list:
        """
        Attaches 'resolved_wacc' to each record dict in-place and also returns
        the modified list. Efficient: resolves tenant override once for the batch.

        Side effect: writes row["wacc"] so all downstream engines see the
        market-aware WACC without any further changes to time_model or future_model.
        """
        # Resolve tenant override once for the whole batch
        tenant_override = self._get_tenant_override(tenant_id)
        adjustment = self._get_market_adjustment()

        for row in records:
            # Per-row explicit takes priority (ERP-sourced)
            row_wacc = row.get("wacc")
            if row_wacc and isinstance(row_wacc, (int, float)) and row_wacc > 0:
                if row_wacc > 1.0:
                    row_wacc /= 100.0
                row["wacc"] = self._clamp(row_wacc)
                continue

            if tenant_override is not None:
                row["wacc"] = tenant_override
                continue

            vertical = str(row.get("industry_vertical", "default")).lower().strip()
            cached_industry = self._get_industry_wacc(vertical)
            if cached_industry is not None:
                row["wacc"] = cached_industry
                continue

            damodaran = _DAMODARAN_WACC.get(vertical, _DAMODARAN_WACC["default"])
            row["wacc"] = self._clamp(damodaran + adjustment)

        return records

    # ── Admin helpers (called by POST /admin/wacc) ────────────────────────────

    def set_tenant_override(self, tenant_id: str, wacc: float) -> bool:
        """
        Persists a per-tenant WACC override to Redis.
        Called by the admin API. Returns True on success.
        """
        if self._cache is None:
            return False
        try:
            key = _REDIS_TENANT_KEY.format(tenant_id=tenant_id)
            clamped = self._clamp(wacc / 100.0 if wacc > 1.0 else wacc)
            self._cache.setex(key, _REDIS_WACC_TTL_SECONDS, str(clamped))
            logger.info(f"WACCEngine: tenant override set — {tenant_id}={clamped:.4f}")
            return True
        except Exception as e:
            logger.warning(f"WACCEngine.set_tenant_override failed: {e}")
            return False

    def clear_tenant_override(self, tenant_id: str) -> bool:
        """Removes a tenant override so the system falls back to industry benchmark."""
        if self._cache is None:
            return False
        try:
            key = _REDIS_TENANT_KEY.format(tenant_id=tenant_id)
            self._cache.delete(key)
            logger.info(f"WACCEngine: tenant override cleared — {tenant_id}")
            return True
        except Exception as e:
            logger.warning(f"WACCEngine.clear_tenant_override failed: {e}")
            return False

    def get_current_rates(self, tenant_id: str = "default_tenant") -> dict:
        """
        Returns a diagnostic snapshot of all WACC rates currently in effect.
        Used by GET /admin/wacc to surface current market state to the admin UI.
        """
        adjustment = self._get_market_adjustment()
        industry_rates = {}
        for vertical, base in _DAMODARAN_WACC.items():
            cached = self._get_industry_wacc(vertical)
            industry_rates[vertical] = {
                "damodaran_base":       round(base, 4),
                "market_adjustment":    round(adjustment, 4),
                "effective":            round(cached if cached is not None else self._clamp(base + adjustment), 4),
                "source":               "redis_warmed" if cached is not None else "damodaran_static"
            }
        return {
            "tenant_id":         tenant_id,
            "tenant_override":   self._get_tenant_override(tenant_id),
            "market_adjustment": round(adjustment, 4),
            "fallback_wacc":     _FALLBACK_WACC,
            "industry_rates":    industry_rates,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_tenant_override(self, tenant_id: str) -> Optional[float]:
        if self._cache is None:
            return None
        try:
            key = _REDIS_TENANT_KEY.format(tenant_id=tenant_id)
            val = self._cache.get(key)
            if val:
                return self._clamp(float(val))
        except Exception:
            pass
        return None

    def _get_industry_wacc(self, vertical: str) -> Optional[float]:
        if self._cache is None:
            return None
        try:
            key = _REDIS_INDUSTRY_KEY_FMT.format(vertical=vertical)
            val = self._cache.get(key)
            if val:
                return self._clamp(float(val))
        except Exception:
            pass
        return None

    def _get_market_adjustment(self) -> float:
        if self._cache is None:
            return 0.0
        try:
            val = self._cache.get(_REDIS_MARKET_ADJ_KEY)
            if val:
                return float(val)
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _clamp(wacc: float) -> float:
        """Clamps WACC to the economically sane range [1%, 50%]."""
        return round(min(max(wacc, 0.01), 0.50), 5)


# ─────────────────────────────────────────────────────────────────────────────
# Cache Warmer — called by Celery Beat task every 6 hours
# ─────────────────────────────────────────────────────────────────────────────

def fetch_and_warm_wacc_cache() -> dict:
    """
    Fetches the current 10-year US Treasury yield and uses it to compute a
    market adjustment over the Damodaran baseline RFR (4.0%).

    Adjustment = current_10yr_UST - 4.0%
    Example: if UST = 4.72%, adjustment = +0.72% applied to all industry WACCs.

    Writes to Redis:
      wacc:market_adjustment       → delta as float string
      wacc:industry:{vertical}     → pre-adjusted rate per industry

    Data source: FRED API (no API key needed for this endpoint).
    Fallback: 0.0 adjustment if fetch fails (uses raw Damodaran values).
    """
    try:
        from app.Db.redis_client import cache
    except Exception:
        return {"status": "failed", "error": "Redis unavailable"}

    current_rfr = _FALLBACK_WACC  # will be overwritten
    source = "fallback"

    # ── Fetch 10-year UST from FRED ───────────────────────────────────────────
    try:
        import urllib.request
        import json as _json

        # FRED series: DGS10 — 10-year Treasury Constant Maturity Rate
        fred_url = (
            "https://api.stlouisfed.org/fred/series/observations"
            "?series_id=DGS10&sort_order=desc&limit=1&file_type=json"
            "&api_key=FRED_PUBLIC_ANONYMOUS_READ"
        )
        # Fallback: US Treasury published XML (no key needed)
        treasury_url = (
            "https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve"
            "&field_tdr_date_value=2024&download=true"
        )

        # Try FRED first; it returns JSON with 'value' field
        try:
            req = urllib.request.Request(
                "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10",
                headers={"User-Agent": "Fiscalogix-WACC-Warmer/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                lines = resp.read().decode().strip().splitlines()
                # Last line: "YYYY-MM-DD,RATE"
                last_line = lines[-1]
                rate_str = last_line.split(",")[-1].strip()
                if rate_str and rate_str != ".":
                    current_rfr = float(rate_str) / 100.0  # FRED returns as percentage
                    source = "FRED DGS10"
        except Exception as fred_err:
            logger.debug(f"WACCEngine warmer: FRED fetch failed ({fred_err}), using fallback RFR.")
            current_rfr = _DAMODARAN_BASELINE_RFR  # no adjustment if we can't fetch

    except Exception as e:
        logger.warning(f"WACCEngine warmer: RFR fetch error — {e}")
        current_rfr = _DAMODARAN_BASELINE_RFR

    # ── Compute and cache market adjustment ───────────────────────────────────
    adjustment = current_rfr - _DAMODARAN_BASELINE_RFR

    try:
        cache.setex(_REDIS_MARKET_ADJ_KEY, _REDIS_WACC_TTL_SECONDS, str(adjustment))

        adjusted_rates = {}
        for vertical, base in _DAMODARAN_WACC.items():
            key = _REDIS_INDUSTRY_KEY_FMT.format(vertical=vertical)
            adjusted = WACCEngine._clamp(base + adjustment)
            cache.setex(key, _REDIS_WACC_TTL_SECONDS, str(adjusted))
            adjusted_rates[vertical] = adjusted

        logger.info(
            f"WACCEngine warmer: cached {len(adjusted_rates)} industry rates. "
            f"10yr UST={current_rfr:.3%} (source={source}), "
            f"adjustment={adjustment:+.3%} over {_DAMODARAN_BASELINE_RFR:.1%} baseline."
        )
        return {
            "status":         "success",
            "current_rfr":    round(current_rfr, 5),
            "rfr_source":     source,
            "adjustment":     round(adjustment, 5),
            "baseline_rfr":   _DAMODARAN_BASELINE_RFR,
            "rates_warmed":   adjusted_rates,
        }
    except Exception as e:
        logger.error(f"WACCEngine warmer: Redis write failed — {e}")
        return {"status": "failed", "error": str(e)}
