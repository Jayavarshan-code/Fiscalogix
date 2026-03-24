import asyncio
import os
import pandas as pd
from app.financial_system.extensions.gnn_mapper import GNNRiskMapper
from app.tasks import task_process_bulk_csv

def verify_phase_12():
    print("--- Phase 12 Verification ---")
    
    # 1. Verify Celery Bulk Streaming Logic
    print("1. Creating Mock 10k Row CSV for Bulk Ingestion Test...")
    df = pd.DataFrame([{
        "shipment_id": f"SHP_{i}",
        "po_number": f"PO_{i}",
        "origin_node": "Shanghai",
        "destination_node": "LA",
        "current_status": "transit",
        "total_value_usd": 50000.0,
        "expected_arrival_utc": "2026-05-01"
    } for i in range(10000)])
    
    test_file = "test_bulk_10k.csv"
    df.to_csv(test_file, index=False)
    
    print("Streaming file through chunked Celery Task...")
    result = task_process_bulk_csv(test_file)
    print(f"Celery Task Result: {result}")
    
    if result.get("domain") == "dw_shipment_facts" and result.get("rows_ingested") == 10000:
        print("✓ Celery Chunked CSV Streaming Verified.")
    else:
        print("X Celery Task Failed.")
        
    # 2. Verify Neo4j GNN Mapper Fallback Engine
    print("\n2. Initializing Neo4j GNN Risk Mapper...")
    mapper = GNNRiskMapper()
    
    mock_shipments = [
        {"shipment_id": "SHP_1", "route": "R_1", "carrier": "C_1", "risk_score": 0.8},
        {"shipment_id": "SHP_2", "route": "R_1", "carrier": "C_2", "risk_score": 0.1}
    ]
    
    print("Mapping and Propagating Risk via Neo4j Cypher bounds...")
    try:
        results = mapper.map_and_propagate(mock_shipments)
        print(f"Mapped PageRank Results: {results}")
        print("✓ Neo4j Cypher Injection Verified.")
    except Exception as e:
        print(f"X Neo4j Query Failed: {e}")
        
if __name__ == "__main__":
    verify_phase_12()
