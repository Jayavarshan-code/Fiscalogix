from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.Db.connections import get_db, engine
from app.financial_system.ai_mapper import AIFieldMapper
from app.tasks import task_process_bulk_csv
import pandas as pd
import io
import os
import uuid

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion Pipeline"])

@router.post("/analyze_csv")
async def analyze_csv(file: UploadFile = File(...)):
    """
    Step 1: Analyzes the CSV headers, automatically classifies the Data Domain,
    and provides the column mapping.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    content = await file.read()
    df_head = pd.read_csv(io.BytesIO(content), nrows=0)
    
    raw_headers = list(df_head.columns)
    detected_schema, mapping = AIFieldMapper.classify_and_map(raw_headers)
    
    return {
        "filename": file.filename,
        "detected_domain": detected_schema,
        "raw_headers": raw_headers,
        "ai_mapping_suggestions": mapping
    }

@router.post("/process_csv", status_code=202)
async def process_csv(file: UploadFile = File(...)):
    """
    Step 2 (Enterprise Standard): Accepts file, saves securely to tmp volume, 
    and emits event to Celery Task Queue. Returns 202 instantly so frontend unblocks.
    """
    # Create secure staging directory
    temp_dir = os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate unique UUID for the blob to prevent concurrent race conditions
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(temp_dir, unique_filename)
    
    # Write file securely via streaming
    with open(filepath, "wb") as buffer:
        while content := await file.read(1024 * 1024): # 1MB chunks
            buffer.write(content)
            
    # Emit Asynchronous Job to Celery Worker Queue
    job = task_process_bulk_csv.delay(filepath)
    
    return {
        "status": "processing",
        "message": "File accepted for background batch processing.",
        "job_id": job.id
    }
