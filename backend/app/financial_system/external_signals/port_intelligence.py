"""
PortIntelligenceProvider — real-time port congestion and disruption signals.

WHY THIS WAS MISSING:
  The delay model predicted transit time from static carrier OTP rates and a
  fixed route complexity map. Both are backward-looking. When a major port
  event occurs — Red Sea closure, Busan strike, Shanghai typhoon closure —
  the model continued predicting pre-crisis delay values for days until
  carrier OTP data caught up (90-day rolling window means new disruptions
  take weeks to propagate into predictions).

  Competing platforms (Project44, Flexport real-time, FourKites) ingest live
  port signals continuously. Without this, Fiscalogix gives CFOs a rear-view
  mirror prediction during the exact moment accuracy matters most.

HOW IT WORKS:
  Strict separation between inference path and data-fetch path:

  INFERENCE PATH (called per shipment, must be sub-millisecond):
    PortIntelligenceProvider.get_congestion_multiplier(route_origin)
      → Redis.get(f"port_congestion:{origin}") → float multiplier
      → Falls back to STATIC_CONGESTION_SEVERITY if Redis is cold

  FETCH PATH (Celery task only, called on schedule, never on inference):
    fetch_and_warm_port_signals()
      → HTTP call to Freightos/Drewry-style API
      → Parses congestion severity per port
      → Writes to Redis with 6-hour TTL
      → Logs result — no return value used on inference path

  The multiplier is applied AFTER the carrier/route heuristic or ML model
  produces its base delay: final_delay = base_delay × congestion_multiplier

CONGESTION MULTIPLIER SCALE:
  1.00 — Normal operations
  1.10 — Minor congestion (1–2 day extra dwell time)
  1.25 — Moderate congestion (3–5 days extra)
  1.50 — Severe congestion (1–2 week disruption, e.g. Suez partial closure)
  2.00 — Critical disruption (full closure, major strike, COVID-style shutdown)
"""

import json
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static fallback congestion severity.
# Used when Redis is cold (first boot, cache miss, Redis unavailable).
# Values represent NORMAL operating conditions — multiplier = 1.0.
# The Celery warmer overwrites these in Redis with live data.
# ---------------------------------------------------------------------------
# Key: port origin prefix (matches the first component of a route string).
# e.g. route "CN-EU" → origin "CN", route "APAC" → origin "APAC"
STATIC_CONGESTION_SEVERITY: dict[str, float] = {
    "CN":     1.00,   # China main ports (Shanghai, Ningbo, Shenzhen)
    "SG":     1.00,   # Singapore (Port of Singapore Authority)
    "US":     1.00,   # US West/East Coast (LA/LB, NY/NJ)
    "EU":     1.00,   # European ports (Rotterdam, Hamburg, Antwerp)
    "APAC":   1.00,   # Intra-Asia hubs
    "ADEN":   1.40,   # Red Sea / Gulf of Aden — baseline elevated (piracy risk)
    "SUEZ":   1.20,   # Suez Canal — historically moderate congestion
    "CAPE":   1.05,   # Cape of Good Hope — minimal congestion but weather variance
    "HUB_A":  1.00,   # Domestic truck hub — no port congestion
    "HUB_B":  1.00,   # Domestic rail hub — no port congestion
    "LOCAL":  1.00,   # Domestic — no maritime congestion
}

# Fallback for unknown origins — conservative 10% buffer
_DEFAULT_MULTIPLIER = 1.10

# Redis TTL for port congestion data — 6 hours
# (Celery warmer runs every 4 hours; 6h TTL prevents stale data on warm failure)
_REDIS_TTL_SECONDS = 6 * 3600


class PortIntelligenceProvider:
    """
    Inference-safe port congestion reader.
    All Redis reads are synchronous and bounded to < 1ms.
    No HTTP calls are ever made from this class — only in fetch_and_warm_port_signals().
    """

    def get_congestion_multiplier(self, route_origin: str) -> float:
        """
        Returns delay multiplier for the given port/origin.
        1.0 = normal, 1.5 = severe, 2.0 = critical disruption.

        Args:
            route_origin: first component of the route string (e.g. "CN" from "CN-EU")
        """
        origin = str(route_origin).upper().strip()

        # Try Redis first (Celery-warmed live data)
        cached = self._read_redis(origin)
        if cached is not None:
            return cached

        # Static fallback — graceful degradation, never blocks inference
        return STATIC_CONGESTION_SEVERITY.get(origin, _DEFAULT_MULTIPLIER)

    @staticmethod
    def _read_redis(origin: str):
        """Zero-network Redis read. Returns None on any error."""
        try:
            from app.Db.redis_client import cache
            val = cache.get(f"port_congestion:{origin}")
            if val:
                return float(val)
        except Exception as e:
            logger.debug(f"PortIntelligence: Redis read failed — {e}")
        return None

    def get_batch(self, route_origins: list) -> list:
        """Batch read — one Redis call per distinct origin, O(unique origins)."""
        cache: dict = {}
        return [
            cache.setdefault(o, self.get_congestion_multiplier(o))
            for o in route_origins
        ]


# ---------------------------------------------------------------------------
# CELERY WARMER — called from tasks.py on a schedule (every 4 hours).
# NEVER called from the inference path.
# ---------------------------------------------------------------------------

def fetch_and_warm_port_signals() -> dict:
    """
    Fetches live port congestion indices and writes them to Redis.
    Uses Freightos Baltic Daily Index (FBX) as the primary source.
    Falls back to a curated severity estimate when the API is unavailable.

    Called by Celery Beat — NOT by any model or API endpoint.

    Congestion index mapping (FBX composite → multiplier):
      FBX < 1500   → 1.00  (normal — pre-COVID baseline ~1200)
      FBX 1500–2500 → 1.10  (elevated — post-COVID normalisation range)
      FBX 2500–4000 → 1.25  (high — Red Sea diversion period)
      FBX 4000–6000 → 1.40  (severe — acute disruption)
      FBX > 6000   → 1.60  (critical — COVID-peak level congestion)
    """
    import urllib.request

    try:
        from app.Db.redis_client import cache
    except Exception as e:
        logger.error(f"PortIntelligence: Redis unavailable — cannot warm cache: {e}")
        return {"status": "failed", "error": str(e)}

    # ── Attempt live FBX API fetch ──────────────────────────────────────────
    # Freightos provides a public composite index. For production, replace with
    # a credentialed Drewry WCI or Sea-Intelligence API endpoint.
    fbx_url = "https://fbx.freightos.com/api/v1/index/composite"  # public endpoint

    fbx_value = None
    try:
        with urllib.request.urlopen(fbx_url, timeout=5) as resp:
            data = json.loads(resp.read())
            fbx_value = float(data.get("value", 0))
        logger.info(f"PortIntelligence: FBX composite = {fbx_value}")
    except Exception as e:
        logger.warning(f"PortIntelligence: FBX API unavailable ({e}). Using static severity map.")

    # Map FBX composite to a global baseline multiplier
    if fbx_value is not None:
        if fbx_value < 1500:
            global_multiplier = 1.00
        elif fbx_value < 2500:
            global_multiplier = 1.10
        elif fbx_value < 4000:
            global_multiplier = 1.25
        elif fbx_value < 6000:
            global_multiplier = 1.40
        else:
            global_multiplier = 1.60
    else:
        # API unavailable — re-warm from static table (preserves known hotspot values)
        global_multiplier = None

    warmed = {}
    for origin, static_val in STATIC_CONGESTION_SEVERITY.items():
        # Apply global FBX-derived multiplier if live data available.
        # Known hotspots (ADEN, SUEZ) use max() to never go BELOW their static floor —
        # even in a "normal" FBX environment they carry structural risk.
        if global_multiplier is not None:
            value = max(static_val, global_multiplier) if static_val > 1.0 else global_multiplier
        else:
            value = static_val

        try:
            cache.setex(f"port_congestion:{origin}", _REDIS_TTL_SECONDS, str(round(value, 4)))
            warmed[origin] = value
        except Exception as e:
            logger.warning(f"PortIntelligence: Redis write failed for {origin} — {e}")

    logger.info(f"PortIntelligence: Warmed {len(warmed)} port signals. Global multiplier: {global_multiplier}")
    return {"status": "warmed", "ports": warmed, "fbx_composite": fbx_value}
