from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.Db.connections import get_db, engine
from sqlalchemy import text
import uuid
import random
import time

router = APIRouter(prefix="/sandbox/sap/v1", tags=["SAP Enterprise Sandbox"])


def init_sandbox_table() -> None:
    """Create the sandbox ERP table if it does not already exist.

    Called once during application startup via the lifespan context manager
    in main.py — never at module import time, so the app can start even when
    the database is not yet reachable during the import phase.
    """
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sandbox_erp_sales_orders (
                document_number VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                action_type VARCHAR NOT NULL,
                payload JSON,
                status VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

@router.post("/sales_orders/{action}")
async def execute_mock_sap_action(action: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Enterprise Sandbox Endpoint acting exactly like SAP OData API.
    Handles network simulation, probabilistic failure (Chaos Monkey), and payload storage.
    """
    import json
    
    # 1. Authorize Token (Mock)
    api_key = payload.get("auth_token")
    if not api_key or api_key != "MOCK_OAUTH_TOKEN_FISCALOGIX":
        raise HTTPException(status_code=401, detail="Invalid SAP OData OAuth Token")
    
    # 2. Chaos Monkey - 5% of requests randomly fail to test Fiscalogix resilience
    if random.random() < 0.05:
        # Simulate network latency before rejecting
        time.sleep(1)
        raise HTTPException(status_code=409, detail="SAP Error 409: Delivery already in process. Record locked.")
    
    # 3. Simulate heavy ERP transaction latency
    time.sleep(0.5) 
    
    tenant_id = payload.get("tenant_id", "default_tenant")
    doc_number = f"SAP-DOC-{uuid.uuid4().hex[:8].upper()}"
    
    # 4. Write to Sandbox Table
    try:
        db.execute(
            text("""
                INSERT INTO sandbox_erp_sales_orders 
                (document_number, tenant_id, action_type, payload, status)
                VALUES (:doc_number, :tenant_id, :action_type, :payload, 'SUCCESS')
            """),
            {
                "doc_number": doc_number,
                "tenant_id": tenant_id,
                "action_type": action,
                "payload": json.dumps(payload.get("parameters", {}))
            }
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database write failure: {str(e)}")

    # 5. Return standards-compliant SAP JSON response
    return {
        "d": {
            "status": "success",
            "erp_system": "SAP S/4Hana (Sandbox)",
            "document_number": doc_number,
            "action_type": action,
            "__metadata": {
                "uri": f"http://localhost:8000/sandbox/sap/v1/sales_orders('{doc_number}')",
                "type": "SAP.SalesDocument"
            }
        }
    }
