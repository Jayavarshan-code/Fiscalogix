from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.document_intelligence import DocumentIntelligenceService
from app.models.document_intelligence import ExtractedDocument
from typing import List, Dict, Any

router = APIRouter()
doc_service = DocumentIntelligenceService()

# In-memory store for the demo (In prod: PostgreSQL/Redis)
document_store: Dict[str, ExtractedDocument] = {}

@router.post("/upload", response_model=ExtractedDocument)
async def upload_document(file: UploadFile = File(...)):
    """
    Ingests and processes a logistics document using Pillar 9 AI.
    """
    try:
        content = await file.read()
        extracted_doc = await doc_service.process_document(content, file.filename)
        document_store[extracted_doc.doc_id] = extracted_doc
        return extracted_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")

@router.get("/{doc_id}", response_model=ExtractedDocument)
async def get_document(doc_id: str):
    """Retrieves the AI-extracted data for a specific document."""
    if doc_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_store[doc_id]

@router.get("/alerts/all", response_model=List[str])
async def get_doc_alerts():
    """Returns all alerts (Expiries, Penalties)."""
    all_alerts = []
    for doc in document_store.values():
        alerts = doc_service.trigger_alerts(doc)
        all_alerts.extend(alerts)
    return all_alerts

@router.get("/agentic/disputes", response_model=List[Dict[str, Any]])
async def get_autonomous_disputes():
    """
    MAX-STANDARD: Returns autonomously drafted disputes for billing variances.
    Analyses all Invoices against their respective MSAs.
    """
    disputes = []
    invoices = [d for d in document_store.values() if d.doc_type == DocumentType.INVOICE]
    contracts = [d for d in document_store.values() if d.doc_type == DocumentType.CONTRACT]
    
    for inv in invoices:
        for con in contracts:
            dispute = doc_service.generate_autonomous_dispute(inv, con)
            if dispute:
                disputes.append(dispute)
    return disputes
