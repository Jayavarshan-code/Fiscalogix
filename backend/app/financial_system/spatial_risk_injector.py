"""
SpatialRiskInjector — scores how much active spatial events impact a given route.

Fixes the core linearity gap: the old risk and delay models computed scores
from shipment-level features only, completely blind to live external disruptions.
A port strike in Hamburg had zero effect on a CN-EU shipment's risk score.

Algorithm:
  1. Load active ExternalSpatialEvent rows (Redis-first, 5-min TTL, DB fallback).
  2. Convert route string to H3 cells at resolution 3 using known port anchors.
  3. For each event, coarsen its stored H3 to resolution 3.
  4. Compute grid distance (h3_distance) between route cell and event cell.
  5. severity contribution = event.severity × DECAY_PER_HOP^distance
  6. Return max contribution across all events and all route cells.
     Max (not sum) avoids double-counting co-located events.

H3 resolution 3 → ~12,000 km² per cell. Appropriate for port/region matching.
DECAY_PER_HOP = 0.55 → severity halves roughly every 2 hops (~500-800 km).
MAX_HOPS = 3 → events beyond ~1,500 km have zero contribution to the route.
"""

import json
import logging
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)

_H3_RES      = 3      # coarse resolution for route-event matching
_DECAY       = 0.55   # severity decay per k-ring hop
_MAX_HOPS    = 3      # events further than this contribute 0
_CACHE_KEY   = "spatial_injector:active_events"
_CACHE_TTL   = 300    # 5 minutes

# ── Route anchor points ───────────────────────────────────────────────────────
# Each entry maps a route code fragment (uppercase) to (lat, lon) of its
# primary maritime hub. A route like "CN-EU_SUEZ" is split into tokens
# ["CN", "EU", "SUEZ"] and each token that matches an anchor contributes
# an H3 cell to the route's coverage set.
ROUTE_ANCHORS: Dict[str, Tuple[float, float]] = {
    # East Asia
    "CN":      (31.23,  121.47),   # Shanghai
    "HK":      (22.30,  114.17),   # Hong Kong
    "JP":      (35.45,  139.76),   # Tokyo / Yokohama
    "KR":      (37.45,  126.64),   # Busan
    "SG":      (1.29,   103.85),   # Singapore
    "TH":      (13.75,  100.52),   # Laem Chabang (Bangkok)
    "VN":      (10.77,  106.70),   # Ho Chi Minh / Cat Lai
    # South Asia
    "IN":      (18.93,   72.84),   # Nhava Sheva / Mumbai
    # Middle East / Africa
    "UAE":     (25.27,   55.31),   # Jebel Ali / Dubai
    "SA":      (21.48,   39.16),   # Jeddah
    "EG":      (31.23,   29.95),   # Alexandria — Suez entry (Mediterranean side)
    "ZA":      (-33.9,   18.42),   # Cape Town — Cape of Good Hope bypass
    # Europe
    "EU":      (51.90,    4.48),   # Rotterdam (primary EU gateway)
    "DE":      (53.55,    9.99),   # Hamburg
    "UK":      (51.45,   -0.37),   # Tilbury / London Gateway
    "FR":      (43.30,    5.37),   # Marseille / Fos-sur-Mer
    "IT":      (40.83,   14.27),   # Gioia Tauro / Naples
    "NL":      (51.90,    4.48),   # Rotterdam
    "PL":      (54.41,   18.65),   # Gdansk
    "ES":      (36.54,   -6.29),   # Algeciras
    # Americas
    "US":      (33.74, -118.27),   # Los Angeles / Long Beach
    "USE":     (40.69,  -74.17),   # New York / Newark
    "MX":      (19.20,  -96.13),   # Veracruz
    "BR":      (-23.93, -46.33),   # Santos
    "CA":      (49.29, -123.11),   # Vancouver
    # Chokepoint waypoints — crucial for detecting Suez/Panama/Malacca risk
    "SUEZ":    (29.97,   32.55),   # Suez Canal entry
    "PANAMA":  (9.06,  -79.68),    # Panama Canal
    "MALACCA": (1.26,   103.58),   # Strait of Malacca
    "BOSPORUS":(41.12,   29.08),   # Bosphorus Strait
}


def _load_events() -> List[Dict]:
    """
    Returns active spatial events as a list of dicts.
    Tries Redis cache first (warm via warm_spatial_events Celery task),
    falls back to a live DB query on cache miss.
    """
    try:
        from app.Db.redis_client import cache
        raw = cache.get(_CACHE_KEY)
        if raw:
            return json.loads(raw)
    except Exception:
        pass

    events = []
    try:
        from app.Db.connections import SessionLocal
        from app.models.external_events import ExternalSpatialEvent
        db = SessionLocal()
        try:
            rows = (
                db.query(ExternalSpatialEvent)
                .filter(ExternalSpatialEvent.is_active == True)
                .all()
            )
            events = [
                {
                    "h3_index": r.h3_index,
                    "severity": float(r.severity_score),
                    "type":     r.event_type,
                }
                for r in rows
            ]
        finally:
            db.close()

        try:
            from app.Db.redis_client import cache
            cache.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(events))
        except Exception:
            pass

    except Exception as exc:
        log.debug("SpatialRiskInjector: DB load failed — %s", exc)

    return events


def _route_to_h3_cells(route: str) -> List[str]:
    """
    Decomposes a route string into a set of H3 cells at _H3_RES covering
    every identified origin, destination, and waypoint.
    """
    try:
        import h3 as h3lib
    except ImportError:
        log.warning("SpatialRiskInjector: h3 library not installed — spatial injection disabled.")
        return []

    cells = set()
    tokens = str(route).upper().replace("-", " ").replace("_", " ").split()
    for token in tokens:
        anchor = ROUTE_ANCHORS.get(token)
        if anchor:
            lat, lon = anchor
            cells.add(h3lib.geo_to_h3(lat, lon, _H3_RES))

    if not cells:
        log.debug("SpatialRiskInjector: no anchor matched for route '%s'", route)

    return list(cells)


def _to_res3(h3_index: str) -> str:
    """Coarsen any-resolution H3 index to _H3_RES for comparison."""
    try:
        import h3 as h3lib
        return h3lib.h3_to_parent(h3_index, _H3_RES)
    except Exception:
        return h3_index


def get_route_severity(route: str, cargo_type: str = "") -> float:
    """
    Public entry point. Returns a severity score [0.0, 1.0] representing
    how much active spatial disruptions affect the given route.

    A Germany port strike:
      - CN-EU_SUEZ route → DE anchor → close to Hamburg H3 → high severity
      - CN-US_PANAMA route → US/PANAMA anchors → far from DE → near-zero severity

    Returns 0.0 immediately if h3 unavailable, no active events, or unknown route.
    """
    try:
        import h3 as h3lib
    except ImportError:
        return 0.0

    events = _load_events()
    if not events:
        return 0.0

    route_cells = _route_to_h3_cells(route)
    if not route_cells:
        return 0.0

    max_severity = 0.0

    for event in events:
        raw_h3 = event.get("h3_index", "")
        if not raw_h3:
            continue

        event_cell   = _to_res3(raw_h3)
        raw_severity = float(event.get("severity", 0.0))

        for route_cell in route_cells:
            if route_cell == event_cell:
                contribution = raw_severity
            else:
                try:
                    dist = h3lib.h3_distance(route_cell, event_cell)
                except Exception:
                    # h3_distance raises for cells in different base pentagons
                    dist = _MAX_HOPS + 1

                if dist > _MAX_HOPS:
                    continue

                contribution = raw_severity * (_DECAY ** dist)

            if contribution > max_severity:
                max_severity = contribution

    return round(min(max_severity, 1.0), 4)


def invalidate_cache() -> None:
    """Force-expire the Redis cache. Called by warm_spatial_events task after DB write."""
    try:
        from app.Db.redis_client import cache
        cache.delete(_CACHE_KEY)
    except Exception:
        pass
