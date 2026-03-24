from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.Db.connections import get_db
from app.financial_system.dw_schema import DWShipmentFact

router = APIRouter(prefix="/datagrid", tags=["High Performance Data Grid"])

class ShipmentRow(BaseModel):
    id: str
    po_number: str
    route: str
    status: str
    total_value_usd: float
    margin_usd: float
    expected_arrival_utc: Optional[datetime]
    ml_confidence_score: float
    ml_risk_detected: bool

class PaginatedResponse(BaseModel):
    total_records: int
    current_page: int
    total_pages: int
    data: List[ShipmentRow]

@router.get("/shipments", response_model=PaginatedResponse)
def get_paginated_shipments(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500), # Cap at 500 to prevent DOS
    sort_by: str = Query("total_value_usd"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db)
):
    """
    High-performance endpoint that queries the Analytics Warehouse.
    Instead of sending 50,000 rows to the browser and crashing React,
    it returns paginated "chunks" just like Salesforce/SAP.
    """
    # 1. Base Query
    query = db.query(DWShipmentFact).filter(DWShipmentFact.tenant_id == "default_tenant")
    
    # 2. Get Total Count (for the UI pagination math)
    total_records = query.count()
    total_pages = (total_records + limit - 1) // limit
    
    # 3. Dynamic Sorting
    valid_sort_columns = ["po_number", "total_value_usd", "margin_usd", "ml_confidence_score"]
    if sort_by in valid_sort_columns:
        sort_column = getattr(DWShipmentFact, sort_by)
        if sort_dir.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        # Default sort
        query = query.order_by(desc(DWShipmentFact.total_value_usd))
        
    # 4. Limit and Offset (The core mechanism of pagination)
    offset = (page - 1) * limit
    shipments = query.offset(offset).limit(limit).all()
    
    # 5. Format for the React Data Grid
    formatted_data = []
    for s in shipments:
        # Synthesize missing data for the UI if it wasn't mapped by AI
        route_str = f"{s.origin_node or 'UNKNOWN'} -> {s.destination_node or 'UNKNOWN'}"
        margin = s.margin_usd if s.margin_usd else (s.total_value_usd * 0.15 if s.total_value_usd else 0)
        risk_score = s.ml_confidence_score if s.ml_confidence_score is not None else 0.5
        
        formatted_data.append({
            "id": s.raw_source_uuid or f"SYS-{s.id}",
            "po_number": s.po_number or "N/A",
            "route": route_str,
            "status": s.current_status or "UNKNOWN",
            "total_value_usd": s.total_value_usd or 0,
            "margin_usd": margin,
            "expected_arrival_utc": s.expected_arrival_utc,
            "ml_confidence_score": risk_score,
            "ml_risk_detected": s.ml_risk_detected or False
        })
        
    return {
        "total_records": total_records,
        "current_page": page,
        "total_pages": total_pages,
        "data": formatted_data
    }
