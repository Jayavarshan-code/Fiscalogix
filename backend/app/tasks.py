from app.celery_app import celery_app
from app.financial_system.optimizations.network_routing import NetworkRoutingEngine
from app.financial_system.optimizations.multi_echelon_inventory import MEIOEngine
from app.financial_system.optimizations.monte_carlo_risk import MonteCarloRiskEngine
from app.financial_system.optimizations.step_cost_routing import StepCostRoutingEngine
from app.financial_system.ai_mapper import AIFieldMapper
from app.Db.connections import engine
import pandas as pd
import os

@celery_app.task(name="optimize_network_routing")
def task_optimize_network_routing(kwargs):
    """
    Background task to run PuLP MILP Global Routing
    """
    return NetworkRoutingEngine.optimize(**kwargs)

@celery_app.task(name="optimize_meio")
def task_optimize_meio(kwargs):
    """
    Background task to run MEIO Stochastic Equations
    """
    return MEIOEngine.optimize(**kwargs)

@celery_app.task(name="monte_carlo_risk")
def task_monte_carlo_risk(kwargs):
    """
    Background task to run 10,000 statistical permutations
    """
    return MonteCarloRiskEngine.simulate(**kwargs)

@celery_app.task(name="optimize_step_cost")
def task_optimize_step_cost(kwargs):
    """
    Background task to run Complex Tariff Big-M MILP Equations
    """
    return StepCostRoutingEngine.optimize(**kwargs)

@celery_app.task(name="process_bulk_csv")
def task_process_bulk_csv(filepath: str):
    """
    Enterprise Data Streaming Pipeline.
    Reads a massive CSV in small memory-safe chunks to prevent OOM crashes.
    """
    try:
        # Determine schema from the first chunk using AI Mapper
        df_head = pd.read_csv(filepath, nrows=10)
        detected_schema, mapping = AIFieldMapper.classify_and_map(list(df_head.columns))
        
        if detected_schema == "UNKNOWN":
            return {"status": "failed", "error": "AI could not classify domain."}
            
        rename_map = {k: v for k, v in mapping.items() if v != "UNMAPPED_DISCARD"}
        target_cols = AIFieldMapper.SCHEMAS[detected_schema]
        
        total_rows = 0
        # Stream file in memory-safe chunks (10,000 rows at a time instead of millions)
        for chunk in pd.read_csv(filepath, chunksize=10000):
            chunk_mapped = chunk.rename(columns=rename_map)
            chunk_final = chunk_mapped[[col for col in target_cols if col in chunk_mapped.columns]].copy()
            chunk_final['tenant_id'] = "default_tenant"
            
            if detected_schema == "dw_shipment_facts":
                chunk_final['source_system'] = "BULK-CSV"
                
            chunk_final.to_sql(detected_schema, engine, if_exists='append', index=False)
            total_rows += len(chunk_final)
            
        return {"status": "success", "domain": detected_schema, "rows_ingested": total_rows}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

