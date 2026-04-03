from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.ml.cashflow_predictor import LiquiditySurvivalModel

class PredictiveCashflowEngine:
    """
    Core Financial Aggregator for Enterprise Cashflow.
    Overrides ERP 'Expected Dates' with 'Probabilistic Actuals'.
    """
    
    @staticmethod
    def simulate_trajectory(db: Session, tenant_id: str) -> Dict[str, Any]:
        """
        Cross-references shipments against customer AR behavioral data to 
        forecast the 30/60/90 day liquidity trajectory.
        """
        # 1. Fetch unarrived shipments and join with their theoretical customer
        # Normally would be an explicit ForeignKey, but we mock the join logic for the demo scope
        query = text("""
            SELECT 
                f.po_number, f.total_value_usd, f.expected_payment_date,
                COALESCE(c.credit_days, 30) as credit_days,
                COALESCE(c.payment_delay_days, 15.0) as historic_delay,
                COALESCE(c.industry_risk_score, 0.1) as risk_score
            FROM dw_shipment_facts f
            LEFT JOIN dw_customer_dimensions c ON c.tenant_id = f.tenant_id
            WHERE f.tenant_id = :tenant_id AND f.current_status != 'DELIVERED'
            LIMIT 50
        """)
        
        result = db.execute(query, {"tenant_id": tenant_id}).fetchall()
        
        cashflow_30d = 0.0
        cashflow_60d = 0.0
        cashflow_90d = 0.0
        bad_debt_provision = 0.0
        
        for row in result:
            val = float(row[1] or 0.0)
            c_days = int(row[3] or 30)
            h_delay = float(row[4] or 0.0)
            r_score = float(row[5] or 0.0)
            
            # Predict the probabilistic segments
            dist = LiquiditySurvivalModel.predict_payment_date_offsets(c_days, h_delay, r_score)
            
            cashflow_30d += val * dist["distribution_30d"]
            cashflow_60d += val * dist["distribution_60d"]
            cashflow_90d += val * dist["distribution_90d"]
            bad_debt_provision += val * dist["distribution_bad_debt"]
            
        # Convert into a time-series payload for the frontend graphs
        # We ensure standard business formatting
        trajectory_array = [
            0, # Day 0 (Current)
            round(cashflow_30d, 2),
            round(cashflow_60d, 2),
            round(cashflow_90d, 2)
        ]
        
        return {
            "tenant_id": tenant_id,
            "trajectory": trajectory_array,
            "bad_debt_provision": round(bad_debt_provision, 2),
            "total_ar_pipeline": round(cashflow_30d + cashflow_60d + cashflow_90d + bad_debt_provision, 2)
        }
