"""
Shared SlowAPI rate limiter instance.

Imported by main.py (wiring) and individual route files (per-endpoint overrides).
Limits are keyed by remote IP address.

Tiers:
  default          60 req/min  — all routes unless overridden
  heavy_compute    15 req/min  — /shipment/{id}/insights (MC + 5 scenarios inline)
  external_api     10 req/min  — /fx-rate (calls ExchangeRate-API; has quota)
  auth             20 req/min  — /auth/login (brute-force protection)
  ingestion         5 req/min  — CSV/ETL upload endpoints (large payloads)
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
)
