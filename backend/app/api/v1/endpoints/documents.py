from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from app.services.document_intelligence import DocumentIntelligenceService
from app.models.document_intelligence import ExtractedDocument, DocumentType
from app.financial_system.auth import get_current_user

router = APIRouter()
doc_service = DocumentIntelligenceService()

# In-memory store for the demo (production: PostgreSQL + Redis)
document_store: Dict[str, ExtractedDocument] = {}


@router.post("/upload", response_model=ExtractedDocument)
async def upload_document(
    file: UploadFile = File(...),
    shipment_id: Optional[int] = Query(None, description="Link extracted data back to a shipment"),
    current_user: dict = Depends(get_current_user),
):
    """
    Ingests and processes a logistics document.
    Pipeline: OCR → LLM classification → specialist extraction → guardrails → DB write-back → RAG.
    If shipment_id is provided, the extracted SLA penalty rate is written directly
    to Shipment.nlp_extracted_penalty_rate and feeds into the ReVM calculation.
    """
    try:
        content = await file.read()
        tenant_id = current_user.get("tenant_id", "default_tenant")
        extracted_doc = await doc_service.process_document(
            file_content=content,
            filename=file.filename,
            shipment_id=shipment_id,
            tenant_id=tenant_id,
        )
        document_store[extracted_doc.doc_id] = extracted_doc
        return extracted_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@router.get("/{doc_id}", response_model=ExtractedDocument)
async def get_document(
    doc_id: str,
    _current_user: dict = Depends(get_current_user),
):
    """Retrieves the AI-extracted data for a specific document."""
    if doc_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_store[doc_id]


@router.get("/alerts/all", response_model=List[str])
async def get_doc_alerts(_current_user: dict = Depends(get_current_user)):
    """Returns all time-sensitive alerts (permit expiries, high penalty rates, missing clauses)."""
    all_alerts = []
    for doc in document_store.values():
        alerts = doc_service.trigger_alerts(doc)
        all_alerts.extend(alerts)
    return all_alerts


@router.get("/agentic/disputes", response_model=List[Dict[str, Any]])
async def get_autonomous_disputes(_current_user: dict = Depends(get_current_user)):
    """
    Autonomously detects billing variances by cross-referencing invoices against contracts.
    Returns dispute records for any invoice that deviates >1% from agreed contract rates.
    """
    disputes = []
    invoices  = [d for d in document_store.values() if d.doc_type == DocumentType.INVOICE]
    contracts = [d for d in document_store.values() if d.doc_type == DocumentType.CONTRACT]

    for inv in invoices:
        for con in contracts:
            dispute = doc_service.generate_autonomous_dispute(inv, con)
            if dispute:
                disputes.append(dispute)
    return disputes


@router.get("/agentic/gaps", response_model=List[str])
async def get_coverage_gaps(_current_user: dict = Depends(get_current_user)):
    """
    Cross-document semantic gap analysis.
    Compares contracts against insurance policies to surface uncovered liability exposure.
    """
    gaps = []
    contracts  = [d for d in document_store.values() if d.doc_type == DocumentType.CONTRACT]
    insurances = [d for d in document_store.values() if d.doc_type == DocumentType.INSURANCE_POLICY]

    for con in contracts:
        for ins in insurances:
            found = doc_service.detect_semantic_gaps(con, ins)
            gaps.extend(found)
    return gaps
