from fastapi import FastAPI
from app.routes.twin import router as twin_router
from app.routes.expansion import router as expansion_router
from app.routes.confidence_studio import router as confidence_router
from app.routes.parser_pipeline import router as pipeline_router
from app.routes.execution import router as execution_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.ingestion import router as ingestion_router
from app.routes.data_grid import router as grid_router
from app.routes.optimization import router as opt_router
from app.connectors.sandbox_router import router as sandbox_router

# --- Enterprise v1 Hub (API-First Architecture) ---
from app.api.v1.endpoints.predict import router as v1_predict
from app.api.v1.endpoints.optimize import router as v1_optimize
from app.api.v1.endpoints.mapping import router as v1_mapping
from app.api.v1.endpoints.documents import router as v1_documents
from app.api.v1.endpoints.realtime import router as v1_realtime

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Fiscalogix Financial Engine - Enterprise Hub")

# --- CORS Configuration (Essential for Vercel <-> Koyeb Bridge) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Replace with your specific Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# UI Routes
app.include_router(twin_router)
app.include_router(expansion_router)
app.include_router(confidence_router)
app.include_router(pipeline_router)
app.include_router(execution_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ingestion_router)
app.include_router(grid_router)
app.include_router(opt_router)
app.include_router(sandbox_router)

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

if __name__ == "__main__":
    import uvicorn
    import os
    # Dynamically bind to the port provided by Render/Koyeb
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)