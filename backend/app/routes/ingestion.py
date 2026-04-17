from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from app.financial_system.ai_mapper import AIFieldMapper
from app.financial_system.dependencies import get_current_user
from app.rate_limiter import limiter
import pandas as pd
import io
import os
import uuid
import asyncio

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
@limiter.limit("5/minute")
async def analyze_csv(
    request: Request,
    file: UploadFile = File(...),
    _current_user: dict = Depends(get_current_user)
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
    current_user: dict = Depends(get_current_user)
):
    """
    Async Real ETL Pipeline, authenticated and hardened.
    Falls back to inline synchronous execution when Celery is unavailable.
    """
    tenant_id = current_user.get("tenant_id", "default_tenant")
    temp_dir = os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(temp_dir, exist_ok=True)

    csv_path, pdf_path = None, None
    heuristic_mapping = {}
    detected_domain = "Unknown"

    if csv_file:
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only .csv files are accepted for data ingestion.")

        csv_content = await csv_file.read()
        _validate_file_size(csv_content, csv_file.filename)

        csv_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{csv_file.filename}")
        with open(csv_path, "wb") as buffer:
            buffer.write(csv_content)

        try:
            df_head = pd.read_csv(csv_path, nrows=0)
            raw_headers = list(df_head.columns)
            detected_domain, heuristic_mapping = AIFieldMapper.classify_and_map(raw_headers)
        except Exception:
            pass

    if pdf_file:
        if not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only .pdf files are accepted for contract ingestion.")

        pdf_content = await pdf_file.read()
        _validate_file_size(pdf_content, pdf_file.filename)

        pdf_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{pdf_file.filename}")
        with open(pdf_path, "wb") as buffer:
            buffer.write(pdf_content)

    # Try Celery first; fall back to inline sync if broker is unavailable
    try:
        from app.tasks import task_process_etl_pipeline
        job = task_process_etl_pipeline.delay(csv_path, pdf_path, tenant_id)
        return {
            "status": "processing",
            "message": "Files accepted. ETL pipeline is running in the background.",
            "job_id": job.id,
            "tenant_id": tenant_id,
            "detected_domain": detected_domain,
            "heuristic_mapping": heuristic_mapping,
        }
    except Exception:
        # Celery unavailable — run synchronously in thread executor so we don't
        # block the event loop during file I/O and DB writes.
        loop = asyncio.get_event_loop()
        from app.tasks import task_process_etl_pipeline
        result = await loop.run_in_executor(
            None,
            task_process_etl_pipeline.run,
            csv_path, pdf_path, tenant_id,
        )
        return {
            "status": "completed",
            "message": "Files processed synchronously (queue service unavailable).",
            "job_id": None,
            "result": result,
            "tenant_id": tenant_id,
            "detected_domain": detected_domain,
            "heuristic_mapping": heuristic_mapping,
        }


@router.post("/freight_simple", status_code=202)
async def freight_simple_upload(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Simplified intake for small/mid freight companies.

    Accepts a CSV with as few as 7 columns — all other fields are defaulted
    so non-technical ops teams can onboard without reading documentation.

    Required columns (case-insensitive, common aliases accepted):
        shipment_id   | AWB No | Tracking No | Bill No
        client_name   | Consignee | Customer | Party
        freight_value | Freight Charges | Invoice Value | Order Value
        carrier       | Airline | Shipping Line | Transporter
        origin        | From | Origin Port | Source
        destination   | To | Destination Port | Consignee City
        expected_date | ETA | Expected Delivery | Due Date

    All other Fiscalogix fields (WACC, cargo_type, credit_days, etc.)
    are filled with safe industry defaults so the pipeline runs immediately.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    _validate_file_size(content, file.filename)
    tenant_id = current_user.get("tenant_id", "default_tenant")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    # ── Column alias resolution (case-insensitive) ─────────────────────────
    _ALIASES = {
        "shipment_id":    ["shipment_id", "awb no", "awb_no", "tracking no",
                           "tracking_no", "bill no", "bill_no", "id"],
        "client_name":    ["client_name", "consignee", "customer", "party",
                           "client", "buyer"],
        "freight_value":  ["freight_value", "freight charges", "freight_charges",
                           "invoice value", "invoice_value", "order value",
                           "order_value", "amount"],
        "carrier":        ["carrier", "airline", "shipping line", "shipping_line",
                           "transporter", "forwarder"],
        "origin":         ["origin", "from", "origin port", "origin_port",
                           "source", "shipper city", "shipper_city"],
        "destination":    ["destination", "to", "destination port",
                           "destination_port", "consignee city",
                           "consignee_city", "dest"],
        "expected_date":  ["expected_date", "eta", "expected delivery",
                           "expected_delivery", "due date", "due_date",
                           "delivery date", "delivery_date"],
    }

    col_lower = {c.lower().strip(): c for c in df.columns}
    resolved = {}
    missing = []

    for field, aliases in _ALIASES.items():
        matched = next((col_lower[a] for a in aliases if a in col_lower), None)
        if matched:
            resolved[field] = matched
        else:
            missing.append(field)

    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not find columns for: {missing}. "
                f"Your CSV has: {list(df.columns)}. "
                "Rename or add the missing columns and re-upload."
            ),
        )

    # ── Build normalised DataFrame with Fiscalogix defaults ───────────────
    import datetime
    today = datetime.date.today()

    normalised_rows = []
    for _, row in df.iterrows():
        raw_date = row[resolved["expected_date"]]
        try:
            eta = pd.to_datetime(raw_date).date()
            delay_days = max(0, (today - eta).days)
        except Exception:
            delay_days = 0

        normalised_rows.append({
            "shipment_id":      str(row[resolved["shipment_id"]]),
            "client_name":      str(row[resolved["client_name"]]),
            "order_value":      float(str(row[resolved["freight_value"]]).replace(",", "").replace("₹", "").replace("$", "") or 0),
            "carrier":          str(row[resolved["carrier"]]),
            "origin_node":      str(row[resolved["origin"]]),
            "destination_node": str(row[resolved["destination"]]),
            "route":            f"{str(row[resolved['origin']])[:2].upper()}-{str(row[resolved['destination']])[:2].upper()}",
            "delay_days":       delay_days,
            # Safe defaults for all derived fields
            "shipment_cost":    float(str(row[resolved["freight_value"]]).replace(",", "").replace("₹", "").replace("$", "") or 0) * 0.15,
            "total_cost":       float(str(row[resolved["freight_value"]]).replace(",", "").replace("₹", "").replace("$", "") or 0) * 0.15,
            "credit_days":      30,
            "payment_delay_days": 0,
            "supplier_payment_terms": 7,
            "cargo_type":       "general_cargo",
            "industry_vertical":"logistics",
            "contract_type":    "standard",
            "customer_tier":    "standard",
            "wacc":             0.085,
            "contribution_profit": float(str(row[resolved["freight_value"]]).replace(",", "").replace("₹", "").replace("$", "") or 0) * 0.12,
        })

    normalised_df = pd.DataFrame(normalised_rows)

    # Save to temp CSV and dispatch through normal ETL pipeline
    temp_dir = os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_freight_simple.csv")
    normalised_df.to_csv(temp_path, index=False)

    try:
        from app.tasks import task_process_etl_pipeline
        job = task_process_etl_pipeline.delay(temp_path, None, tenant_id)
        return {
            "status": "processing",
            "message": f"Loaded {len(normalised_rows)} shipments. Processing in background.",
            "job_id": job.id,
            "shipments_loaded": len(normalised_rows),
            "columns_detected": resolved,
            "defaults_applied": ["credit_days=30", "cargo_type=general_cargo",
                                  "carrier_payment_terms=7d", "wacc=8.5%"],
        }
    except Exception:
        loop = asyncio.get_event_loop()
        from app.tasks import task_process_etl_pipeline
        result = await loop.run_in_executor(None, task_process_etl_pipeline.run,
                                            temp_path, None, tenant_id)
        return {
            "status": "completed",
            "message": f"Loaded and processed {len(normalised_rows)} shipments.",
            "shipments_loaded": len(normalised_rows),
            "columns_detected": resolved,
            "result": result,
        }


@router.get("/freight_simple/template")
def freight_simple_template(_current_user: dict = Depends(get_current_user)):
    """
    Returns a pre-filled example CSV row so clients know exactly what to send.
    Download and fill in your own data — no other columns needed.
    """
    import datetime
    sample = {
        "AWB No": ["FZ-2024-001", "FZ-2024-002"],
        "Consignee": ["Acme Exports Pvt Ltd", "Global Traders"],
        "Freight Charges": [125000, 87500],
        "Carrier": ["Maersk", "MSC"],
        "Origin Port": ["Nhava Sheva", "Chennai"],
        "Destination Port": ["Jebel Ali", "Hamburg"],
        "Expected Delivery": [
            (datetime.date.today() + datetime.timedelta(days=14)).isoformat(),
            (datetime.date.today() + datetime.timedelta(days=21)).isoformat(),
        ],
    }
    df = pd.DataFrame(sample)
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="fiscalogix_freight_template.csv"'},
    )


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    _current_user: dict = Depends(get_current_user)
):
    """
    Polling endpoint for the Ingestion Studio to check ETL status.
    """
    from app.celery_app import celery_app  # noqa: PLC0415 — deferred to avoid IDE false-positive
    from celery.result import AsyncResult   # noqa: PLC0415
    task_result = AsyncResult(job_id, app=celery_app)
    result = task_result.result if task_result.ready() else None

    return {
        "status": task_result.state,  # PENDING, STARTED, SUCCESS, FAILURE
        "result": result
    }
