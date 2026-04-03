from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class DWShipmentFact(Base):
    """
    ANALYTICS WAREHOUSE FACT TABLE
    Flattened to support:
    - NetworkX (origin, destination, nodes)
    - Prophet (cashflow_date, amount)
    - RandomForest (risk_score, delay_days)
    """
    __tablename__ = 'dw_shipment_facts'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    
    # Ingestion Tracking (AI Mapper Output)
    source_system = Column(String(50)) # e.g. 'BULK-CSV', 'SAP-API'
    raw_source_uuid = Column(String(100), index=True)
    
    # Core Shipment & Node Data (For NetworkX Graph Theory)
    po_number = Column(String(100))
    origin_node = Column(String(100), index=True)
    destination_node = Column(String(100), index=True)
    current_status = Column(String(50))
    
    # Financial Data (For Prophet Cashflow Engine)
    total_value_usd = Column(Float)
    margin_usd = Column(Float)
    expected_payment_date = Column(DateTime)
    
    # Timing & Risk (For RandomForest ML Engine)
    expected_arrival_utc = Column(DateTime)
    actual_arrival_utc = Column(DateTime, nullable=True)
    delay_days_calculated = Column(Integer, default=0)
    
    # AI System outputs (Feedback Loop)
    ml_confidence_score = Column(Float)
    ml_risk_detected = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class DWNodeDimension(Base):
    """
    ANALYTICS WAREHOUSE DIMENSION TABLE
    Supports mapping the physical graph constraint network.
    """
    __tablename__ = 'dw_node_dimensions'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    node_id = Column(String(100), unique=True, index=True)
    node_type = Column(String(50)) # 'PORT', 'SUPPLIER', 'DC', 'PLANT'
    country = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    congestion_index = Column(Float, default=0.0) # For real-time risk heatmaps

class DWInventoryFact(Base):
    """
    Tracks real-time and historical stock levels.
    """
    __tablename__ = 'dw_inventory_facts'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    node_id = Column(String(100), index=True)
    sku_id = Column(String(100), index=True)
    
    quantity_on_hand = Column(Integer)
    quantity_in_transit = Column(Integer)
    safety_stock_level = Column(Integer)
    days_of_supply = Column(Float) # Calculated metric for the Risk Engine
    
    last_updated = Column(DateTime, default=datetime.utcnow)

class DWLaneDimension(Base):
    """
    Performance data for specific transit 'edges' in the Graph.
    Used by the Optimizer to find cheaper/safer routes.
    """
    __tablename__ = 'dw_lane_dimensions'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    origin_node = Column(String(100), index=True)
    destination_node = Column(String(100), index=True)
    mode = Column(String(20)) # 'OCEAN', 'AIR', 'TRUCK'
    
    avg_lead_time_days = Column(Float)
    std_dev_lead_time = Column(Float) # For probability-based risk modeling
    cost_per_unit_usd = Column(Float)

class DWSupplierDimension(Base):
    """
    Risk scores for external vendors.
    """
    __tablename__ = 'dw_supplier_dimensions'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    supplier_id = Column(String(100), unique=True)
    supplier_name = Column(String(200))
    
    financial_health_score = Column(Float) # From D&B or similar
    on_time_delivery_rate = Column(Float)
    geopolitical_risk_index = Column(Float)

class DWProductDimension(Base):
    """
    SKU-level financial parameters.
    """
    __tablename__ = 'dw_product_dimensions'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    sku_id = Column(String(100), unique=True)
    
    category = Column(String(100))
    unit_cost_usd = Column(Float)
    holding_cost_daily = Column(Float)
    stockout_penalty_daily = Column(Float) # Critical for the Optimization engine

class DWCustomerDimension(Base):
    """
    AR parameters. Used by Cashflow Engine for probabilistic liquidity modeling.
    """
    __tablename__ = 'dw_customer_dimensions'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    customer_id = Column(String(100), unique=True)
    customer_name = Column(String(200))
    
    credit_days = Column(Integer, default=30)
    payment_delay_days = Column(Float, default=0.0) # E.g., average 14 days late
    industry_risk_score = Column(Float, default=0.0)
