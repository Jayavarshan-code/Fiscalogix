"""
TariffDutyModel — import duty and customs tariff cost on cross-border shipments.

WHY THIS WAS MISSING:
  The main ReVM pipeline had no tariff component. For cross-border routes,
  import duties are often the LARGEST single cost — yet ReVM showed them as
  zero, making CN→US or EU→US shipments appear far more profitable than reality.

  Example: $500K electronics shipment, US-CN route (25% Section 301 tariff):
    tariff_cost = $500,000 × 0.25 = $125,000
    Without this: ReVM overstated by $125,000 — larger than time, FX, and SLA combined.

  The EFIEngine already modelled duty/tariff in its scenario analysis but was
  never wired into the operational ReVM path (orchestrator.py).

HOW IT WORKS:
  Three-layer rate resolution (highest specificity wins):
    1. HS code override      — product-specific tariff rate (most accurate)
    2. Route-based ad-valorem — average tariff for the trade corridor
    3. Redis-cached live rate — Celery-warmed from customs API (future-ready)

  tariff_cost = order_value × effective_rate × (1 − duty_drawback_rate)

  Duty drawback: goods re-exported after manufacturing or processing get a
  partial refund (up to 99% in the US CBP drawback programme). The drawback_rate
  field allows the model to net this benefit against gross tariff cost.

RATE SOURCES:
  - US Section 301 (USTR): 25% on List 3/4 CN goods (electronics, machinery)
  - EU MFN (DG TAXUD): 3.5% average on US imports (varies widely by HS chapter)
  - ASEAN FTA: 0–5% intra-APAC (preferential rates under RCEP)
  - Domestic / LOCAL: 0% (no customs crossing)
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Route-based ad-valorem tariff rates (average effective rate per corridor).
# These are conservative midpoints — actual rates depend on HS chapter and
# declared value. HS code overrides take priority when available.
# ---------------------------------------------------------------------------
# Sources:
#   US-CN: USTR Section 301 List 3/4 (25%), List 1/2 (15%) → blended ~22%
#   CN-US: China retaliatory tariffs on US goods → blended ~18%
#   EU-US: EU MFN average (WTO bound rate) → ~3.5%
#   US-EU: US MFN average → ~2.5%
#   APAC:  RCEP preferential (intra-Asia) → ~4%
#   LOCAL: Domestic movement → 0%
ROUTE_TARIFF_RATES = {
    "US-CN":  0.22,   # USTR Section 301 blended effective rate
    "CN-US":  0.18,   # China retaliatory blended rate
    "EU-US":  0.035,  # EU MFN average
    "US-EU":  0.025,  # US MFN average
    "APAC":   0.04,   # RCEP / intra-Asia preferential average
    "CN-EU":  0.04,   # EU GSP / standard rate on Chinese goods
    "EU-CN":  0.06,   # China standard MFN for EU exports
    "LOCAL":  0.00,   # Domestic — no tariff
}

# ---------------------------------------------------------------------------
# HS code chapter overrides — product-specific tariff rates.
# Key: HS chapter prefix (2 digits) as string.
# When the shipment carries an hs_code field, this takes priority over the
# route average. Only the most common logistics categories are listed.
# ---------------------------------------------------------------------------
HS_CHAPTER_RATES = {
    # Electronics / machinery (Section 301 priority targets)
    "84": 0.25,   # Chapter 84: Nuclear reactors, boilers, machinery
    "85": 0.25,   # Chapter 85: Electrical machinery, electronics
    # Automotive
    "87": 0.27,   # Chapter 87: Vehicles (US Section 232 steel/auto tariffs)
    # Steel and aluminium
    "72": 0.25,   # Chapter 72: Iron and steel (Section 232)
    "73": 0.25,   # Chapter 73: Steel articles
    "76": 0.10,   # Chapter 76: Aluminium (232, lower than steel)
    # Pharmaceuticals (typically zero-rated under WTO pharma agreement)
    "30": 0.00,   # Chapter 30: Pharmaceutical products
    # Textiles / apparel
    "61": 0.12,   # Chapter 61: Knitted apparel
    "62": 0.12,   # Chapter 62: Woven apparel
    # Food / FMCG (highly variable — use route default for safety)
    "09": 0.05,   # Chapter 9: Coffee, tea, spices
    "16": 0.06,   # Chapter 16: Preparations of meat/fish
}


class TariffDutyModel:
    """
    Computes import duty cost for a shipment crossing a customs border.

    For domestic (LOCAL) routes, returns 0 immediately — no computation needed.

    Rate resolution order:
      1. hs_code field on the row → HS chapter override (most accurate)
      2. Route tariff rate from ROUTE_TARIFF_RATES
      3. Redis-cached live rate (future: Celery-warmed from customs APIs)

    Duty drawback applied when drawback_rate > 0 (re-export programmes).
    """

    def compute(self, row) -> float:
        route = str(row.get("route", "LOCAL")).upper().strip()

        # Fast path: domestic shipments have zero tariff
        if route == "LOCAL" or not self._is_cross_border(route):
            return 0.0

        order_value = float(row.get("order_value", 0.0))
        if order_value <= 0:
            return 0.0

        # --- Rate resolution ---
        effective_rate = self._resolve_rate(row, route)

        # Duty drawback: partial refund for re-exported or processed goods.
        # US CBP 19 U.S.C. §1313 allows up to 99% drawback on re-exports.
        # Default 0 (no drawback assumed unless declared in the shipment record).
        drawback_rate = float(row.get("duty_drawback_rate", 0.0))
        drawback_rate = min(max(drawback_rate, 0.0), 0.99)  # clamp 0–99%

        net_rate = effective_rate * (1.0 - drawback_rate)
        tariff_cost = order_value * net_rate

        return round(tariff_cost, 2)

    def _is_cross_border(self, route: str) -> bool:
        """Returns True if the route crosses a customs border."""
        # LOCAL and domestic-only prefixes are tariff-free
        domestic_prefixes = {"LOCAL", "DOMESTIC", "HUB_", "RETAILER_"}
        for prefix in domestic_prefixes:
            if route.startswith(prefix):
                return False
        # Routes with a hyphen (e.g. "US-CN", "CN-EU") are cross-border
        return "-" in route or route in ROUTE_TARIFF_RATES

    def _resolve_rate(self, row, route: str) -> float:
        """
        Resolves the best available tariff rate for this shipment.
        Priority: HS code chapter > Redis live rate > route average.
        """
        # Priority 1: HS code product-specific rate
        hs_code = str(row.get("hs_code", "")).strip()
        if hs_code and len(hs_code) >= 2:
            chapter = hs_code[:2]
            if chapter in HS_CHAPTER_RATES:
                return HS_CHAPTER_RATES[chapter]

        # Priority 2: Redis-cached live rate (Celery-warmed, future integration)
        cached = self._read_cached_rate(route)
        if cached is not None:
            return cached

        # Priority 3: Static route average
        # Normalise route variants: "CN-EU" and "CN_EU" both resolve correctly
        route_key = route.replace("_", "-")
        return ROUTE_TARIFF_RATES.get(route_key, 0.0)

    @staticmethod
    def _read_cached_rate(route: str):
        """Redis-only read — zero network I/O, sub-millisecond. Returns None on miss."""
        try:
            from app.Db.redis_client import cache
            cached = cache.get(f"tariff_rate:{route}")
            if cached:
                return float(cached)
        except Exception as e:
            logger.debug(f"TariffDutyModel: Redis unavailable — {e}")
        return None

    def compute_batch(self, rows_list: list) -> list:
        return [self.compute(row) for row in rows_list]
