from app.celery_app import celery_app
from app.financial_system.optimizations.network_routing import NetworkRoutingEngine
from app.financial_system.optimizations.multi_echelon_inventory import MEIOEngine
from app.financial_system.optimizations.monte_carlo_risk import MonteCarloRiskEngine
from app.financial_system.optimizations.step_cost_routing import StepCostRoutingEngine
from app.financial_system.ai_mapper import AIFieldMapper
from app.Db.connections import engine
import pandas as pd
import os

# ─────────────────────────────────────────────────────────────────────────────
# FX CACHE WARMING TASK (Fix A — FX API Bottleneck)
# Runs on a periodic schedule (every 55 minutes via Celery Beat).
# This is the ONLY place a live HTTP call to open.er-api.com is made.
# The inference path (FXRiskModel.compute_batch) reads ONLY from Redis.
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(name="warm_fx_cache")
def task_warm_fx_cache():
    """
    Periodic FX cache warmer. Pre-populates Redis with live volatility rates
    for all known trade routes so the inference path never makes network calls.
    Schedule: every 55 minutes via celery_app beat_schedule.
    """
    from app.financial_system.fx_model import fetch_and_warm_fx_cache
    return fetch_and_warm_fx_cache()


# ─────────────────────────────────────────────────────────────────────────────
# WACC CACHE WARMING TASK (Gap 6 — Dynamic WACC Engine)
# Runs every 6 hours via Celery Beat.
# Fetches 10-year US Treasury yield from FRED and adjusts all Damodaran
# industry WACC benchmarks by the delta from the 4.0% calibration baseline.
# The inference path (TimeValueModel) reads ONLY from Redis (or falls back
# to raw Damodaran if Redis is unavailable).
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(name="warm_wacc_cache")
def task_warm_wacc_cache():
    """
    Periodic WACC cache warmer.
    Fetches current 10-year US Treasury yield from FRED and uses it to
    compute a market adjustment over the Damodaran 4.0% RFR baseline.
    Pre-populates Redis with adjusted WACCs for all tracked industry verticals.
    Schedule: every 6 hours via celery_app beat_schedule.
    """
    from app.financial_system.wacc_engine import fetch_and_warm_wacc_cache
    return fetch_and_warm_wacc_cache()

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

@celery_app.task(name="retrain_ml_models")
def task_retrain_ml_models():
    """
    Weekly ML model retraining.
    Loads real data from dw_shipment_facts when >= 500 rows exist;
    falls back to synthetic otherwise. Scheduled every Sunday 02:00 UTC.
    Persists a MLModelVersion row after every run for governance tracking.
    """
    from app.financial_system.ml_pipeline.train_models import train_all
    import datetime

    result = train_all()

    # Persist governance record — deactivate previous active version first
    try:
        from setup_db import MLModelVersion
        from app.Db.connections import SessionLocal
        db = SessionLocal()
        try:
            version_tag = f"v-{datetime.datetime.utcnow().strftime('%Y-%m-%d')}"
            # Deactivate all previous active versions
            db.query(MLModelVersion).filter_by(is_active=True).update({"is_active": False})
            db.add(MLModelVersion(
                tenant_id="global",
                model_name="all",
                version=version_tag,
                is_active=True,
                training_rows=result.get("training_rows", 0),
                data_source=result.get("data_source", "synthetic"),
                delay_rmse=result.get("delay_rmse"),
                risk_accuracy=result.get("risk_accuracy"),
                demand_rmse=result.get("demand_rmse"),
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            import logging
            logging.getLogger(__name__).error(
                f"task_retrain_ml_models: failed to persist MLModelVersion — {e}", exc_info=True
            )
        finally:
            db.close()
    except ImportError:
        pass

    return result


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

@celery_app.task(name="process_etl_pipeline")
def task_process_etl_pipeline(csv_filepath: str, pdf_filepath: str, tenant_id: str):
    """
    High-Performance Asynchronous ETL Pipeline.
    Extracts real SLA penalties from PDFs using regex NLP rules,
    then streams the CSV into PostgreSQL in memory-safe chunks.
    """
    from app.ml.sla_extractor import SLAContractExtractor
    
    try:
        # Step 1: Real PDF Text Extraction + NLP Parsing
        penalty_rate = 0.05  # Safe default (5% per day) if no contract is uploaded
        penalty_summary = "No contract uploaded; using baseline 5% per day."
        
        if pdf_filepath and os.path.exists(pdf_filepath):
            try:
                import pdfplumber
                with pdfplumber.open(pdf_filepath) as pdf:
                    raw_text = " ".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
                
                if raw_text.strip():
                    nlp_result = SLAContractExtractor.extract(raw_text)
                    
                    if nlp_result["force_majeure_applies"]:
                        penalty_summary = "FORCE MAJEURE applies — penalty waived per contract terms."
                        penalty_rate = 0.0
                    elif nlp_result["penalty_rate"] is not None:
                        penalty_rate = nlp_result["penalty_rate"]
                        penalty_summary = f"Extracted percentage penalty: {penalty_rate * 100:.2f}% per day."
                    elif nlp_result["flat_fee_per_day"] is not None:
                        penalty_summary = f"Flat fee penalty: ${nlp_result['flat_fee_per_day']:,.0f} per day."
                    else:
                        penalty_summary = "No structured penalty clause found; using 5% default."
                else:
                    penalty_summary = "PDF text was empty or unreadable; using 5% default."
            except ImportError:
                penalty_summary = "pdfplumber not installed. Install with: pip install pdfplumber"
            except Exception as pdf_err:
                penalty_summary = f"PDF parsing error: {str(pdf_err)}"

        # Step 2: High-Performance Database Push
        total_rows = 0
        if csv_filepath and os.path.exists(csv_filepath):
            df_head = pd.read_csv(csv_filepath, nrows=10)
            detected_schema, mapping = AIFieldMapper.classify_and_map(list(df_head.columns))
            
            if detected_schema != "UNKNOWN":
                rename_map = {k: v for k, v in mapping.items() if v != "UNMAPPED_DISCARD"}
                target_cols = AIFieldMapper.SCHEMAS[detected_schema]
                
                # Stream CSV in chunks
                for chunk in pd.read_csv(csv_filepath, chunksize=10000):
                    chunk_mapped = chunk.rename(columns=rename_map)
                    chunk_final = chunk_mapped[[col for col in target_cols if col in chunk_mapped.columns]].copy()
                    
                    chunk_final['tenant_id'] = tenant_id
                    if detected_schema == "dw_shipment_facts":
                        chunk_final['source_system'] = "ASYNC-PIPELINE"
                    
                    # Stamp the NLP-extracted context across all parsed rows
                    # This bridges the text-based PDF with the rows of the CSV
                    chunk_final['nlp_extracted_penalty_rate'] = penalty_rate
                    
                    chunk_final.to_sql(detected_schema, engine, if_exists='append', index=False)
                    total_rows += len(chunk_final)

        # Compute real financial impact from the rows just ingested
        financial_impact = 0.0
        try:
            import sqlalchemy
            with engine.connect() as conn:
                res = conn.execute(
                    sqlalchemy.text(
                        "SELECT COALESCE(SUM(ABS(margin_usd)), 0) as at_risk, "
                        "COALESCE(SUM(total_cost_usd), 0) as total_cost "
                        "FROM dw_shipment_facts WHERE tenant_id = :tid "
                        "AND source_system = 'ASYNC-PIPELINE'"
                    ),
                    {"tid": tenant_id},
                )
                row = res.fetchone()
                financial_impact = float(row[0]) if row and row[0] else 0.0
        except Exception:
            pass  # Non-critical — don't fail the task if this query fails

        return {
            "status": "success",
            "rows_ingested": total_rows,
            "nlp_extracted_penalty": penalty_summary,
            "calculated_rate": penalty_rate,
            "financial_impact": round(financial_impact, 2),
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    finally:
        if csv_filepath and os.path.exists(csv_filepath):
            os.remove(csv_filepath)
        if pdf_filepath and os.path.exists(pdf_filepath):
            os.remove(pdf_filepath)


# ─────────────────────────────────────────────────────────────────────────────
# RAG KNOWLEDGE BASE REFRESH TASK
# Runs nightly at 01:00 UTC via Celery Beat.
# Re-embeds operational data (carrier performance, shipment history, decisions)
# so LLM narratives are grounded in the most recent 90 days of real data.
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(name="refresh_rag_knowledge_base")
def task_refresh_rag_knowledge_base(tenant_id: str = "default_tenant"):
    """
    Nightly RAG knowledge base refresh.
    Re-ingests operational tables into embedded knowledge chunks.
    """
    try:
        from app.services.rag.ingestion import RAGIngestionPipeline
        pipeline = RAGIngestionPipeline()
        result = pipeline.run_full(tenant_id=tenant_id)
        return {"status": "success", "chunks_by_source": result}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
