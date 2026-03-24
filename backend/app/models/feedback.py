from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class DecisionLog(Base):
    """
    Step 1: Capture Every Decision
    Stores the 'Predicted' state and features at the time of decision.
    """
    __tablename__ = 'decision_log'
    
    decision_id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    shipment_id = Column(String, index=True)
    route_selected = Column(String)
    
    # Predicted Metrics (The 'Target')
    predicted_delay = Column(Float)
    predicted_cost = Column(Float)
    predicted_efi = Column(Float)
    confidence_score = Column(Float)
    
    # Input Features (For Retraining)
    input_features = Column(JSON) 
    risk_posture = Column(String) # CONSERVATIVE, BALANCED, etc.

class ActualOutcome(Base):
    """
    Step 2: Capture Actual Outcomes
    Stores what really happened in the physical world.
    """
    __tablename__ = 'actual_outcome'
    
    outcome_id = Column(String, primary_key=True)
    decision_id = Column(String, ForeignKey('decision_log.decision_id'), unique=True)
    
    actual_delay = Column(Float)
    actual_cost = Column(Float)
    actual_revenue = Column(Float)
    actual_loss = Column(Float)
    actual_efi = Column(Float)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

class LearningMetric(Base):
    """
    Step 3: Compute Errors
    Stores the 'Delta' between prediction and reality.
    """
    __tablename__ = 'learning_metrics'
    
    id = Column(String, primary_key=True)
    decision_id = Column(String, ForeignKey('decision_log.decision_id'))
    
    # Accuracy Metrics
    delay_error = Column(Float)
    cost_error = Column(Float)
    efi_error = Column(Float)
    
    # Percentages
    delay_accuracy = Column(Float) # 1 - |err|/actual
    cost_accuracy = Column(Float)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
