import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.rate_limiter import limiter

from app.routes.twin import router as twin_router
from app.routes.expansion import router as expansion_router
from app.routes.confidence_studio import router as confidence_router
from app.routes.execution import router as execution_router
from app.routes.auth import router as auth_router
from app.routes.register import router as register_router
from app.routes.admin import router as admin_router
from app.routes.ingestion import router as ingestion_router
from app.routes.data_grid import router as grid_router
from app.routes.optimization import router as opt_router
from app.routes.india import router as india_router
from app.routes.reports import router as reports_router
from app.routes.alerts import router as alerts_router
from app.routes.sla import router as sla_router
from app.connectors.sandbox_router import router as sandbox_router

# --- Enterprise v1 Hub (API-First Architecture) ---
from app.api.v1.endpoints.predict import router as v1_predict
from app.api.v1.endpoints.optimize import router as v1_optimize
from app.api.v1.endpoints.mapping import router as v1_mapping
from app.api.v1.endpoints.documents import router as v1_documents
from app.api.v1.endpoints.realtime import router as v1_realtime

logger = logging.getLogger(__name__)

_MODELS_DIR = Path(__file__).parent / "financial_system" / "ml_pipeline" / "models"
_REQUIRED_MODELS = ["delay_model.pkl", "risk_pipeline.pkl", "demand_model.pkl"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Startup: train ML models if pkl files are missing (first boot or clean clone).
    Uses real data from dw_shipment_facts when >= 500 rows exist; synthetic otherwise.
    Training runs in a thread executor so the event loop stays unblocked.
    Subsequent boots skip training — models load from disk in <1s.
    """
    missing = [m for m in _REQUIRED_MODELS if not (_MODELS_DIR / m).exists()]
    if missing:
        logger.info(
            f"[startup] ML model files missing: {missing}. "
            "Running first-boot training (~10s on synthetic data, longer on real data)..."
        )
        import asyncio
        from app.financial_system.ml_pipeline.train_models import train_all

        def background_train():
            try:
                result = train_all()
                logger.info(
                    f"[startup] Models trained — "
                    f"delay_rmse={result.get('delay_rmse', '?'):.2f}d  "
                    f"risk_acc={result.get('risk_accuracy', '?'):.1%}  "
                    f"source={result.get('data_source', '?')}"
                )
            except Exception as e:
                logger.error(
                    f"[startup] Model training failed ({type(e).__name__}: {e}). "
                    "Inference will use heuristic fallbacks until resolved."
                )

        loop = asyncio.get_event_loop()
        # Fire and forget instead of blocking so Uvicorn can open its port before Render times it out
        loop.run_in_executor(None, background_train)
    else:
        logger.info("[startup] All ML model files present — skipping training.")

    # FIX: Initialize Database schemas on startup to ensure carrier_performance is created on cloud platforms
    try:
        from setup_db import initialize_db
        logger.info("[startup] Initializing database schemas...")
        initialize_db()
    except Exception as e:
        logger.error(f"[startup] Database initialization failed: {e}")

    yield


# --- CORS Configuration ---
# Replaced allow_origins=["*"] with an env-var-controlled allowlist.
# Set ALLOWED_ORIGINS to your Vercel/production URL on deployment.
_origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app = FastAPI(
    title="Fiscalogix Financial Engine - Enterprise Hub",
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Global default: 60 req/min per IP.  Per-endpoint overrides in route files.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-ID"],
)

# UI Routes
app.include_router(twin_router)
app.include_router(expansion_router)
app.include_router(confidence_router)
app.include_router(execution_router)
app.include_router(auth_router)
app.include_router(register_router)
app.include_router(admin_router)
app.include_router(ingestion_router)
app.include_router(grid_router)
app.include_router(opt_router)
app.include_router(sandbox_router)
app.include_router(india_router)
app.include_router(reports_router)
app.include_router(alerts_router)
app.include_router(sla_router)

# Enterprise API Layer (v1)
app.include_router(v1_predict, prefix="/api/v1/predict", tags=["Enterprise Prediction"])
app.include_router(v1_optimize, prefix="/api/v1/optimize", tags=["Enterprise Optimization"])
app.include_router(v1_mapping, prefix="/api/v1/mapping", tags=["Enterprise Mapping"])
app.include_router(v1_documents, prefix="/api/v1/documents", tags=["Document Intelligence"])
app.include_router(v1_realtime, tags=["Enterprise Real-Time"])


@app.get("/health")
def health_check():
    """Liveness probe for Render/Koyeb deployment."""
    return {"status": "healthy", "service": "Fiscalogix Brain"}


@app.get("/fx-rate", tags=["Utilities"])
@limiter.limit("10/minute")
def fx_rate(request: Request):
    """
    Returns the current USD→INR exchange rate.
    Served from Redis cache (refreshed daily). Falls back to live API,
    then hardcoded 84.5 if both are unavailable.
    Strict rate limit: calls ExchangeRate-API which has a monthly quota.
    """
    from app.utils.fx import get_usd_to_inr
    rate = get_usd_to_inr()
    return {"base": "USD", "target": "INR", "rate": rate}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
