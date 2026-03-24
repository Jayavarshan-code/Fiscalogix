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

app = FastAPI(title="Fiscalogix Financial Engine - Extended API")
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