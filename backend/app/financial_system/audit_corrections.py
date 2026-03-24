from sqlalchemy import Column, String, Float, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class AuditCorrection(Base):
    """
    Active Learning Table.
    Stores human-verified labels for low-confidence ML predictions.
    Used as the 'Gold Standard' dataset for future retraining loops.
    """
    __tablename__ = "audit_corrections"
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(String, index=True) # e.g. Shipment ID
    entity_type = Column(String) # e.g. "RiskPrediction"
    
    original_prediction = Column(Float)
    human_label = Column(Float) # 1.0 for Risk, 0.0 for Safe
    
    corrector_id = Column(String) # The Executive who corrected it
    correction_reason = Column(String)
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Metadata for retraining
    features_at_time = Column(JSON) # Snapshot of features when prediction was made
