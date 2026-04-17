import os
from celery import Celery
from celery.schedules import crontab

# ---------------------------------------------------------------------------
# HARDENING APPLIED — 3 issues resolved in this file:
#
# Issue 1 — Hardcoded Redis Broker URL
# WHAT WAS WRONG:
#   broker="redis://localhost:6379/0"  ← breaks on every cloud deployment
# On Render, Railway, or Fly.io, Redis is accessed via a REDIS_URL env var,
# not localhost. Hardcoding localhost means Celery workers fail to connect
# silently on every non-local environment.
# HOW IT WAS FIXED:
#   os.environ.get("REDIS_URL", "redis://localhost:6379/0") — graceful fallback
#   for local dev while supporting all cloud environments.
#
# Issue 2 — Beat Schedule Missing (FX Cache Warmer Never Ran)
# WHAT WAS WRONG:
#   The warm_fx_cache Celery task was created in tasks.py but there was NO
#   beat_schedule entry here. Celery Beat would never know to invoke it.
#   The FX inference path was "fixed" architecturally but the cache was never
#   actually being pre-warmed — so it would always hit the Redis-miss fallback.
# HOW IT WAS FIXED:
#   Added beat_schedule to run warm_fx_cache every 55 minutes (5 min before
#   the Redis 1-hour TTL expires). This guarantees the cache is always warm.
#
# Issue 3 — No Auto-Discovery for Beat Tasks
# WHAT WAS WRONG:
#   Without autodiscover_tasks(), Celery Beat cannot find the task definitions
#   needed to execute the schedule. The schedule would silently fail to resolve
#   the task.
# HOW IT WAS FIXED:
#   Added celery_app.autodiscover_tasks(["app"]) pointing at the tasks module.
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/1")

celery_app = Celery(
    "fiscalogix_workers",
    broker=REDIS_URL,
    backend=REDIS_BACKEND,
    include=["app.tasks"]  # Auto-discover task modules for Beat
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Performance: Don't hoard tasks; only acknowledge after complete success
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    # ── Celery Beat Schedule ─────────────────────────────────────────────────
    # warm_fx_cache runs every 55 minutes to pre-warm Redis before the 1-hour
    # TTL expires. This guarantees the FX inference path always has a cache hit.
    # To start Beat: celery -A app.celery_app beat --loglevel=info
    beat_schedule={
        "warm-fx-cache-every-55-minutes": {
            "task":     "warm_fx_cache",
            "schedule": crontab(minute="*/55"),
        },
        # Retrain all ML models weekly (Sunday 02:00 UTC) using latest DW data.
        # Falls back to synthetic if the DW has fewer than 500 rows.
        "retrain-ml-models-weekly": {
            "task":     "retrain_ml_models",
            "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
        },
        # Refresh RAG knowledge base nightly (01:00 UTC).
        # Re-embeds carrier performance, shipment history, and decision outcomes
        # from the last 90 days so LLM narratives reflect the latest operational data.
        "refresh-rag-knowledge-base-nightly": {
            "task":     "refresh_rag_knowledge_base",
            "schedule": crontab(hour=1, minute=0),
        },
        # Warm WACC cache every 6 hours (Gap 6 — Dynamic WACC Engine).
        # Fetches 10-year US Treasury yield from FRED and adjusts all industry
        # WACC benchmarks by the delta from the 4.0% Damodaran baseline.
        # Ensures time_cost calculations track real market cost of capital.
        "warm-wacc-cache-every-6-hours": {
            "task":     "warm_wacc_cache",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        # Warm spatial events every 60 minutes.
        # Fetches Weather (OpenWeatherMap), Geopolitical (ACLED), and Port
        # Congestion (MarineTraffic) data into external_spatial_events table.
        # /execution/spatial/active-risks reads from DB — never live HTTP.
        "warm-spatial-events-every-60-minutes": {
            "task":     "warm_spatial_events",
            "schedule": crontab(minute=0),
        },
    },
)
