from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.Db.connections import get_db, engine
from app.financial_system.ai_mapper import AIFieldMapper
from app.financial_system.dependencies import get_current_user
from app.tasks import task_process_bulk_csv
import pandas as pd
import io
import os
import uuid

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion Pipeline"])

# --- Security Constants ---
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB hard limit
ALLOWED_CSV_MIMES = {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"}
ALLOWED_PDF_MIMES = {"application/pdf"}

def _validate_file_size(content: bytes, filename: str):
    """Raises 413 if the uploaded file exceeds the size limit."""
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File '{filename}' exceeds the 50MB upload limit. Please chunk your data."
        )

@router.post("/analyze_csv")
async def analyze_csv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)  # 🔐 JWT-Protected
):
    """
    Step 1: Analyzes the CSV headers, automatically classifies the Data Domain,
    and provides the column mapping.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    _validate_file_size(content, file.filename)

    df_head = pd.read_csv(io.BytesIO(content), nrows=0)
    raw_headers = list(df_head.columns)
    detected_schema, mapping = AIFieldMapper.classify_and_map(raw_headers)

    return {
        "filename": file.filename,
        "detected_domain": detected_schema,
        "raw_headers": raw_headers,
        "ai_mapping_suggestions": mapping
    }

@router.post("/upload", status_code=202)
async def upload_files(
    csv_file: UploadFile = File(None),
    pdf_file: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)  # 🔐 JWT-Protected
):
    """
    Async Real ETL Pipeline, authenticated and hardened.
    Validates file types + size before dispatching to Celery.
    """
    tenant_id = current_user.get("tenant_id", "default_tenant")
    temp_dir = os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(temp_dir, exist_ok=True)

    csv_path, pdf_path = None, None
    heuristic_mapping = {}

    if csv_file:
        # Validate extension
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only .csv files are accepted for data ingestion.")

        csv_content = await csv_file.read()
        _validate_file_size(csv_content, csv_file.filename)

        csv_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{csv_file.filename}")
        with open(csv_path, "wb") as buffer:
            buffer.write(csv_content)

        # Fast Heuristic Mapping for UI Step 2
        try:
            df_head = pd.read_csv(csv_path, nrows=0)
            raw_headers = list(df_head.columns)
            detected_schema, heuristic_mapping = AIFieldMapper.classify_and_map(raw_headers)
        except Exception:
            pass

    if pdf_file:
        # Validate extension
        if not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only .pdf files are accepted for contract ingestion.")

        pdf_content = await pdf_file.read()
        _validate_file_size(pdf_content, pdf_file.filename)

        pdf_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{pdf_file.filename}")
        with open(pdf_path, "wb") as buffer:
            buffer.write(pdf_content)

    # Dispatch to Celery – fail loudly if Redis is unavailable
    try:
        from app.tasks import task_process_etl_pipeline
        job = task_process_etl_pipeline.delay(csv_path, pdf_path, tenant_id)
        job_id = job.id
    except Exception as e:
        # Clean up saved files if Celery fails
        for path in [csv_path, pdf_path]:
            if path and os.path.exists(path):
                os.remove(path)
        raise HTTPException(
            status_code=503,
            detail=f"ETL queue unavailable. Please ensure Redis is running. Details: {str(e)}"
        )

    return {
        "status": "processing",
        "message": "Files accepted. ETL pipeline is running in the background.",
        "job_id": job_id,
        "tenant_id": tenant_id,
        "heuristic_mapping": heuristic_mapping
    }


from app.celery_app import celery_app
from celery.result import AsyncResult

@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)  # 🔐 JWT-Protected
):
    """
    Polling endpoint for the Ingestion Studio to check ETL status.
    """
    task_result = AsyncResult(job_id, app=celery_app)
    result = task_result.result if task_result.ready() else None

    return {
        "status": task_result.state,  # PENDING, STARTED, SUCCESS, FAILURE
        "result": result
    }
