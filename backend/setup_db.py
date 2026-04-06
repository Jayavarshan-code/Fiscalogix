import os
import datetime
from sqlalchemy import (
    create_engine, text, Column, Integer, String, ForeignKey,
    JSON, DateTime, Float, Boolean, UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship

# ---------------------------------------------------------------------------
# DATABASE CONFIGURATION
# FIX H: Moved connection string components to env vars with safe local fallbacks.
# NOTE: Never commit real credentials to source control. Use .env + python-dotenv.
# ---------------------------------------------------------------------------
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "password123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "fiscalogix")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ---------------------------------------------------------------------------
# FIX A: Single Authoritative Base
# WHAT WAS WRONG: 6 separate files (setup_db.py, feedback.py, dw_schema.py,
# external_events.py, audit_corrections.py, connections.py) each declared their
# own `Base = declarative_base()`. SQLAlchemy requires all models to share
# ONE base for Base.metadata.create_all() to work correctly.
# With 6 isolated Bases, only models from the base passed to create_all()
# would be created — all other tables were silently missing.
# FIX: All models are now consolidated into this single file with one Base.
# ---------------------------------------------------------------------------
Base = declarative_base()


# ============================================================================
# SECTION 0: TENANT TABLE  (must come first — every other table FKs to it)
# Gap: tenant_id was a raw String(50) in 20+ tables with no parent record.
# Without this table you cannot store company name, subscription tier, feature
# flags, or billing info — all required before onboarding a second customer.
# ============================================================================

class Tenant(Base):
    __tablename__ = 'tenants'
    id                = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id         = Column(String(50), unique=True, nullable=False, index=True)
    company_name      = Column(String(200), nullable=False)
    subscription_tier = Column(String(30), default='starter')
    # starter | growth | enterprise — controls feature flag access
    is_active         = Column(Boolean, default=True)
    billing_email     = Column(String(255))
    feature_flags     = Column(JSON, default=dict)
    # e.g. {"gnn_contagion": false, "live_ais": false, "multi_erp": true}
    onboarded_at      = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at        = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                               onupdate=datetime.datetime.utcnow)


# ============================================================================
# SECTION 1: RBAC / AUTH TABLES
# Gap: three overlapping permission mechanisms (Profile.permissions,
# PermissionSet, Role) with none actually enforced.
# Fix: Role is now the single source of truth for permissions.
#      Profile is a display-name label only (kept for JWT profile_name).
#      PermissionSet and UserPermissionSet removed.
# ============================================================================

class Profile(Base):
    """Display-name label carried in the JWT payload. No permissions here."""
    __tablename__ = 'profiles'
    id    = Column(Integer, primary_key=True)
    name  = Column(String(100), unique=True, nullable=False)
    users = relationship("User", back_populates="profile")


class Role(Base):
    """
    Single source of truth for access control.
    permissions JSON keys consumed by get_current_user() dependency:
      is_admin, can_view_dashboard, can_view_matrix, can_view_revm,
      can_view_liquidity, can_view_recovery, can_view_governance,
      can_view_warehouse, can_execute_actions
    parent_role_id supports role hierarchy (e.g. Executive inherits Analyst).
    """
    __tablename__ = 'roles'
    id             = Column(Integer, primary_key=True)
    name           = Column(String(100), unique=True, nullable=False)
    permissions    = Column(JSON, nullable=False, default=dict)
    parent_role_id = Column(Integer, ForeignKey('roles.id'), nullable=True)


class User(Base):
    __tablename__ = 'users'
    id              = Column(Integer, primary_key=True)
    tenant_id       = Column(String(50), nullable=False, index=True)
    username        = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    profile_id      = Column(Integer, ForeignKey('profiles.id'))
    role_id         = Column(Integer, ForeignKey('roles.id'), nullable=False)
    is_active       = Column(Boolean, default=True)
    last_login_at   = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    profile         = relationship("Profile", back_populates="users")
    role            = relationship("Role")


# ============================================================================
# SECTION 2: OPERATIONAL OLTP TABLES
# ============================================================================

class SKU(Base):
    """
    FIX M1: Added cargo_type, industry_vertical — required by time_model.py
    and demand_model.py for holding rate and seasonality lookups.
    Without these, all financial engine lookups silently default to 'general_cargo'.
    """
    __tablename__ = 'sku'
    sku_id               = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id            = Column(String(50), default='default_tenant', nullable=False, index=True)
    sku_code             = Column(String(100), index=True)          # human-readable identifier e.g. "ELEC-001"
    description          = Column(String(500))
    unit_cost            = Column(Float)
    unit_value           = Column(Float)
    holding_cost_per_day = Column(Float)
    cargo_type           = Column(String(50), default='general_cargo')   # FIX M1: time_model.py
    industry_vertical    = Column(String(50), default='default')          # demand_model.py seasonality
    is_critical          = Column(Boolean, default=False)
    created_at           = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at           = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Customer(Base):
    """
    FIX M1: Added customer_tier — required by future_model.py CLV multiplier.
    FIX I : Added customer_name — the table was anonymous, making audit logs meaningless.
    """
    __tablename__ = 'customers'
    customer_id        = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id          = Column(String(50), default='default_tenant', nullable=False, index=True)
    customer_name      = Column(String(200))                       # FIX I
    customer_tier      = Column(String(30), default='standard')    # FIX M1: future_model.py CLV
    industry_vertical  = Column(String(50), default='default')     # demand_model.py seasonality
    country_code       = Column(String(3))                         # ISO 3166-1 alpha-3 (FX model routing)
    email              = Column(String(255))
    credit_days        = Column(Integer, default=0)
    payment_delay_days = Column(Integer, default=0)
    created_at         = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at         = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Supplier(Base):
    __tablename__ = 'suppliers'
    supplier_id            = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id              = Column(String(50), nullable=False, index=True)
    supplier_name          = Column(String(200))
    country_code           = Column(String(3))
    carrier_preference     = Column(String(100))
    financial_health_score = Column(Float, default=0.7)
    on_time_delivery_rate  = Column(Float, default=0.85)
    geopolitical_risk_index= Column(Float, default=0.2)
    contract_expiry_date   = Column(DateTime(timezone=True))
    created_at             = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at             = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                                    onupdate=datetime.datetime.utcnow)
    __table_args__ = (Index('idx_suppliers_tenant', 'tenant_id'),)


class Warehouse(Base):
    """
    Gap: Inventory.warehouse_id was an orphan Integer with no FK target.
    MEIO engine needs warehouse capacity, location, and H3 index for
    spatial risk overlay. Now Inventory.warehouse_id FKs here.
    """
    __tablename__ = 'warehouses'
    warehouse_id  = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id     = Column(String(50), nullable=False, index=True)
    warehouse_name= Column(String(200), nullable=False)
    country_code  = Column(String(3))
    city          = Column(String(100))
    latitude      = Column(Float)
    longitude     = Column(Float)
    h3_index      = Column(String(15), index=True)      # spatial risk overlay
    capacity_units = Column(Integer, default=0)         # max storable units
    cost_per_unit_per_day = Column(Float, default=0.0)  # MEIO holding cost input
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    __table_args__ = (Index('idx_warehouse_tenant', 'tenant_id'),)


class CarrierPerformance(Base):
    """
    Gap: delay_model.py used a static CARRIER_RELIABILITY_REGISTRY dict that
    was never updated from real outcomes. This table persists measured OTP rates
    per carrier per route per time window, so the weekly retraining task can
    build features from actual performance rather than hardcoded assumptions.
    WIRED TO:
    - delay_model.py — reads latest window to override static dict at inference
    - tasks.py (retrain_ml_models) — aggregates outcomes into new rows
    """
    __tablename__ = 'carrier_performance'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id       = Column(String(50), nullable=False, index=True)
    carrier_name    = Column(String(100), nullable=False)
    route           = Column(String(50), nullable=True)   # None = all routes
    on_time_rate    = Column(Float, nullable=False)        # 0.0–1.0
    avg_delay_days  = Column(Float, default=0.0)
    sample_count    = Column(Integer, default=0)           # shipments measured
    measured_from   = Column(DateTime(timezone=True), nullable=False)
    measured_to     = Column(DateTime(timezone=True), nullable=False)
    created_at      = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    __table_args__ = (
        Index('idx_carrier_perf_tenant_carrier', 'tenant_id', 'carrier_name'),
    )


class Order(Base):
    __tablename__ = 'orders'
    order_id            = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id           = Column(String(50), nullable=False, index=True)
    # sku_id kept nullable for backwards compatibility with existing single-SKU imports.
    # New orders should use OrderLineItem instead; sku_id will be deprecated.
    sku_id              = Column(Integer, ForeignKey('sku.sku_id'), nullable=True)
    customer_id         = Column(Integer, ForeignKey('customers.customer_id'))
    supplier_id         = Column(Integer, ForeignKey('suppliers.supplier_id'), nullable=True)
    order_value         = Column(Float)
    total_cost          = Column(Float)
    contribution_profit = Column(Float)
    currency            = Column(String(3), default='USD')
    order_month         = Column(Integer)
    created_at          = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at          = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                                 onupdate=datetime.datetime.utcnow)
    line_items          = relationship("OrderLineItem", back_populates="order",
                                       cascade="all, delete-orphan")


class OrderLineItem(Base):
    """
    Gap: Order had a single sku_id FK, so a PO with 5 products required 5 orders.
    Real enterprise POs have multiple line items per order number.
    This table replaces the single-SKU pattern for new data while Order.sku_id
    is kept nullable for backwards compatibility.
    WIRED TO: order value roll-up, MEIO inventory demand planning.
    """
    __tablename__ = 'order_line_items'
    line_item_id  = Column(Integer, primary_key=True, autoincrement=True)
    order_id      = Column(Integer, ForeignKey('orders.order_id'), nullable=False)
    sku_id        = Column(Integer, ForeignKey('sku.sku_id'), nullable=False)
    quantity      = Column(Integer, nullable=False, default=1)
    unit_price    = Column(Float, nullable=False)
    line_total    = Column(Float, nullable=False)       # quantity × unit_price
    created_at    = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    order         = relationship("Order", back_populates="line_items")
    __table_args__ = (Index('idx_line_items_order', 'order_id'),)


class Shipment(Base):
    """
    FIX M1 (Critical): Added 8 missing columns that all financial ML engines require.
    Without these columns, carrier, route, cargo_type, contract_type etc. all
    default to generic fallbacks — making the entire financial intelligence layer inert.
    """
    __tablename__ = 'shipments'
    shipment_id               = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id                 = Column(String(50), nullable=False, index=True)
    order_id                  = Column(Integer, ForeignKey('orders.order_id'))
    # Gap: shipment had a raw penalty_rate float with no link back to which
    # contract produced it. sla_contract_id traces it to the source document.
    sla_contract_id           = Column(Integer, ForeignKey('sla_contracts.id'), nullable=True)
    shipment_cost             = Column(Float)
    total_cost                = Column(Float)
    shipment_value            = Column(Float)
    delay_days                = Column(Integer, default=0)
    nlp_extracted_penalty_rate = Column(Float, nullable=True)
    # --- FIX M1: Previously missing columns ---
    carrier                   = Column(String(100), default='unknown')  # delay_model.py
    route                     = Column(String(50), default='domestic')  # fx_model.py + delay_model.py
    origin_node               = Column(String(100))                     # route optimizer
    destination_node          = Column(String(100))                     # route optimizer
    industry_vertical         = Column(String(50), default='default')   # demand_model.py seasonality
    contract_type             = Column(String(30), default='standard')  # sla_model.py penalty cap
    expected_arrival_utc      = Column(DateTime(timezone=True))
    actual_arrival_utc        = Column(DateTime(timezone=True))
    created_at                = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at                = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index('idx_shipments_tenant_delay', 'tenant_id', 'delay_days'),
        Index('idx_shipments_order', 'order_id'),
    )


class FinancialParameter(Base):
    """
    FIX C: Added UNIQUE constraint on tenant_id.
    WHAT WAS WRONG: The CROSS JOIN on financial_parameters returns a Cartesian product.
    If this table has more than 1 row per tenant (e.g., from double-seeding),
    every order is duplicated N times. Adding the UNIQUE constraint prevents
    duplicate rows, making the CROSS JOIN safe.
    NOTE: Long-term fix is to replace CROSS JOIN with an explicit JOIN on tenant_id.
    """
    __tablename__ = 'financial_parameters'
    id                    = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id             = Column(String(50), nullable=False, unique=True)  # FIX C: UNIQUE
    wacc                  = Column(Float, default=0.08)
    penalty_rate          = Column(Float, default=0.05)
    tax_rate              = Column(Float, default=0.18)          # GST / VAT rate for duty calculations
    carbon_cost_per_kg    = Column(Float, default=0.0)           # carbon pricing; Pillar 7 extension
    safety_stock_days     = Column(Integer, default=14)          # days of safety stock to maintain
    reorder_point_days    = Column(Integer, default=21)          # trigger reorder at this many days of supply
    updated_at            = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Inventory(Base):
    __tablename__ = 'inventory'
    inventory_id      = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id         = Column(String(50), default='default_tenant', nullable=False, index=True)
    sku_id            = Column(Integer, ForeignKey('sku.sku_id'))
    # Gap: was an orphan Integer with no FK. Now links to Warehouse for
    # capacity constraints and spatial risk overlay in the MEIO engine.
    warehouse_id      = Column(Integer, ForeignKey('warehouses.warehouse_id'), nullable=True)
    quantity          = Column(Integer, default=0)
    reorder_point     = Column(Integer, default=0)
    safety_stock      = Column(Integer, default=0)
    lead_time_days    = Column(Integer, default=14)
    unit_of_measure   = Column(String(20), default='UNITS')
    last_counted_at   = Column(DateTime(timezone=True))
    updated_at        = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                               onupdate=datetime.datetime.utcnow)
    __table_args__    = (Index('idx_inventory_tenant_sku', 'tenant_id', 'sku_id'),)


class SLAContract(Base):
    """
    NEW TABLE: Persists SLA contract data extracted from uploaded PDFs.
    WHY IT WAS MISSING: The NLP extractor (SLAContractExtractor) extracted
    penalty clauses from uploaded PDFs but NEVER persisted them. Every server
    restart lost all extraction results. The ETL pipeline re-stamped rows with
    penalty_rate but had no memory of which contract it came from.
    WIRED TO:
    - tasks.py (task_process_etl_pipeline) — persists after extraction
    - sla_model.py — looks up contract_type if customer_id is provided
    """
    __tablename__ = 'sla_contracts'
    contract_id        = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id          = Column(String(50), nullable=False, index=True)
    customer_id        = Column(Integer, ForeignKey('customers.customer_id'), nullable=True)
    contract_ref       = Column(String(100))            # e.g. "MSA-2024-RELIANCE-001"
    contract_type      = Column(String(30), default='standard')  # maps to CONTRACT_TYPE_CAPS
    penalty_rate       = Column(Float)                  # % per day
    flat_fee_per_day   = Column(Float)                  # $ flat fee
    max_penalty_cap    = Column(Float, default=0.15)    # fraction of invoice
    force_majeure      = Column(Boolean, default=False)
    effective_date     = Column(DateTime(timezone=True))
    expiry_date        = Column(DateTime(timezone=True))
    raw_pdf_path       = Column(String(500))
    extracted_at       = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    __table_args__ = (Index('idx_sla_tenant_customer', 'tenant_id', 'customer_id'),)


class RevmSnapshot(Base):
    """
    NEW TABLE: Persists ReVM output after every orchestrator run.
    WHY IT WAS MISSING: The ReVM was always computed on-the-fly with no history.
    There was no way to show a CFO how their portfolio's risk-adjusted margin
    trended over 6 months — which is the CORE investor pitch story.
    WIRED TO:
    - orchestrator.py — RevmSnapshotLogger.save_batch() called after Phase 2
    - Dashboard analytics queries for time-series charting
    """
    __tablename__ = 'revm_snapshots'
    snapshot_id      = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id        = Column(String(50), nullable=False, index=True)
    shipment_id      = Column(Integer, index=True)
    run_timestamp    = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, index=True)
    # Core ReVM components
    revm             = Column(Float)
    contribution_profit = Column(Float)
    risk_penalty     = Column(Float)
    time_cost        = Column(Float)
    future_cost      = Column(Float)
    fx_cost          = Column(Float)
    sla_penalty      = Column(Float)
    # Intelligence outputs
    risk_score       = Column(Float)
    confidence_score = Column(Float)
    predicted_delay  = Column(Float)
    decision_action  = Column(String(50))
    decision_tier    = Column(Integer)
    __table_args__ = (
        Index('idx_revm_tenant_time', 'tenant_id', 'run_timestamp'),
    )


class PortRegistry(Base):
    """
    NEW TABLE: Port demurrage rates and geospatial data.
    WHY IT WAS MISSING: reroute_optimizer.py had port penalties hardcoded as
    a Python dict (`self.port_penalties = {"USMIA": ...}`). This meant:
    1. Rates were invisible to CFOs and couldn't be updated without a code deploy.
    2. They couldn't be displayed on dashboards.
    3. New ports required a developer, not a config change.
    WIRED TO: reroute_optimizer.py — replaces hardcoded dict with DB lookup.
    """
    __tablename__ = 'port_registry'
    port_id            = Column(String(10), primary_key=True)  # 'USMIA', 'SGSIN'
    port_name          = Column(String(200), nullable=False)
    country_code       = Column(String(3))
    latitude           = Column(Float)
    longitude          = Column(Float)
    h3_index           = Column(String(15), index=True)
    demurrage_per_day  = Column(Float)                         # USD
    storage_per_day    = Column(Float, default=0.0)
    peak_risk_months   = Column(JSON, default=list)            # e.g. [11, 12, 1]
    is_active          = Column(Boolean, default=True)


# ============================================================================
# SECTION 3: AUDIT & COMPLIANCE TABLES
# ============================================================================

class AuditLog(Base):
    """
    FIX D (M4 continuation): audit_logger.py's log_execution() now has a
    matching method in the rewritten AuditLogger class.
    This table definition is the single canonical version.
    """
    __tablename__ = 'audit_logs'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id        = Column(String(50), nullable=False, index=True)
    timestamp        = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    user_id          = Column(String(50), nullable=False)
    action_type      = Column(String(50), nullable=False)
    target_entity_id = Column(String(100), nullable=False, index=True)
    previous_state   = Column(JSON)
    new_state        = Column(JSON)
    confidence_score = Column(Float)
    erp_receipt      = Column(JSON)

    __table_args__ = (
        Index('idx_audit_tenant_action', 'tenant_id', 'action_type'),
    )


class AuditCorrection(Base):
    """
    Active Learning Table. Human-verified labels for low-confidence predictions.
    FIX A: Merged from audit_corrections.py (was isolated with its own Base).
    FIX I: Added tenant_id for multi-tenant isolation.
    """
    __tablename__ = 'audit_corrections'
    id                   = Column(Integer, primary_key=True)
    tenant_id            = Column(String(50), nullable=False, index=True)   # FIX I
    entity_id            = Column(String(100), index=True)
    entity_type          = Column(String(50))
    original_prediction  = Column(Float)
    human_label          = Column(Float)
    corrector_id         = Column(String(50))
    correction_reason    = Column(String(500))
    timestamp            = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    features_at_time     = Column(JSON)


# ============================================================================
# SECTION 4: ML FEEDBACK LOOP TABLES
# ============================================================================

class MLModelVersion(Base):
    """
    Gap: model health was tracked only in memory via register_model_status().
    Nothing was persisted — no record of when models were retrained, on what
    data volume, or what validation metrics looked like at training time.
    Required for SOC2 AI governance and for the 'self-governing' pitch story.
    WIRED TO: tasks.py (retrain_ml_models) — writes a row after every retrain.
    """
    __tablename__ = 'ml_model_versions'
    id             = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id      = Column(String(50), nullable=False, index=True, default='global')
    model_name     = Column(String(100), nullable=False)   # 'delay' | 'risk' | 'demand'
    version        = Column(String(50), nullable=False)    # e.g. 'v3-2026-04-06'
    is_active      = Column(Boolean, default=True)         # only one active per model_name
    trained_at     = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    training_rows  = Column(Integer, default=0)
    data_source    = Column(String(20), default='synthetic')  # 'real' | 'synthetic'
    # Validation metrics at training time
    delay_rmse     = Column(Float, nullable=True)
    risk_accuracy  = Column(Float, nullable=True)
    demand_rmse    = Column(Float, nullable=True)
    notes          = Column(String(500), nullable=True)
    __table_args__ = (
        Index('idx_model_versions_name_active', 'model_name', 'is_active'),
    )


class DecisionLog(Base):
    """
    FIX A: Merged from models/feedback.py (was isolated with its own Base).
    FIX I: Added tenant_id for multi-tenant isolation.
    Gap: shipment_id was String(50) but Shipment.shipment_id is Integer — FK join impossible.
    """
    __tablename__ = 'decision_log'
    decision_id     = Column(String(50), primary_key=True)
    tenant_id       = Column(String(50), nullable=False, index=True)
    timestamp       = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    # Gap fixed: was String(50), now Integer FK matching Shipment.shipment_id
    shipment_id     = Column(Integer, ForeignKey('shipments.shipment_id'), nullable=True, index=True)
    route_selected  = Column(String(100))
    predicted_delay = Column(Float)
    predicted_cost  = Column(Float)
    predicted_efi   = Column(Float)
    confidence_score= Column(Float)
    input_features  = Column(JSON)
    risk_posture    = Column(String(30))


class ActualOutcome(Base):
    """FIX A: Merged from models/feedback.py. FIX: Added tenant_id for multi-tenant isolation."""
    __tablename__ = 'actual_outcome'
    outcome_id     = Column(String(50), primary_key=True)
    tenant_id      = Column(String(50), nullable=False, index=True)  # was missing — breaks multi-tenant queries
    decision_id    = Column(String(50), ForeignKey('decision_log.decision_id'), unique=True)
    actual_delay   = Column(Float)
    actual_cost    = Column(Float)
    actual_revenue = Column(Float)
    actual_loss    = Column(Float)
    actual_efi     = Column(Float)
    timestamp      = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


class LearningMetric(Base):
    """FIX A: Merged from models/feedback.py. FIX: Added tenant_id for multi-tenant isolation."""
    __tablename__ = 'learning_metrics'
    id             = Column(String(50), primary_key=True)
    tenant_id      = Column(String(50), nullable=False, index=True)  # was missing — breaks multi-tenant queries
    decision_id    = Column(String(50), ForeignKey('decision_log.decision_id'))
    delay_error    = Column(Float)
    cost_error     = Column(Float)
    efi_error      = Column(Float)
    delay_accuracy = Column(Float)
    cost_accuracy  = Column(Float)
    timestamp      = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    __table_args__ = (Index('idx_learning_tenant_decision', 'tenant_id', 'decision_id'),)


# ============================================================================
# SECTION 5: EXTERNAL EVENTS TABLE
# ============================================================================

class ExternalSpatialEvent(Base):
    """
    FIX A: Merged from models/external_events.py (was isolated with its own Base).
    Stores raw, sovereign external data (Weather, Geopolitics, Port Congestion).
    FIX: Added tenant_id, severity_category, and compound active-events index.
    """
    __tablename__ = 'external_spatial_events'
    id                = Column(Integer, primary_key=True, index=True)
    tenant_id         = Column(String(50), nullable=False, index=True, default='global')
    # 'global' = platform-wide event (e.g. Red Sea crisis); tenant-specific = custom alert
    h3_index          = Column(String(15), nullable=False)
    event_type        = Column(String(50), nullable=False)          # WEATHER | PORT_CONGESTION | GEOPOLITICAL | STRIKE
    source_api        = Column(String(50), nullable=False)
    severity_score    = Column(Float, nullable=False)               # 0.0–1.0
    severity_category = Column(String(10), nullable=False, default='LOW')
    # Computed from severity_score: LOW(<0.3) | MEDIUM(<0.6) | HIGH(<0.85) | CRITICAL(>=0.85)
    # Stored to allow fast DB-level filtering without recalculating on every query
    description       = Column(String(255))
    raw_payload       = Column(JSON)
    is_active         = Column(Boolean, default=True)
    detected_at       = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    expires_at        = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # The hot path: reroute_optimizer fetches active events by H3 zone
        Index('idx_spatial_events_active_h3', 'h3_index', 'is_active'),
        # Dashboard alerts: active high-severity events for a tenant
        Index('idx_spatial_events_tenant_severity', 'tenant_id', 'severity_category', 'is_active'),
    )


# ============================================================================
# SECTION 6: DATA WAREHOUSE (DW) TABLES
# ============================================================================

class DWShipmentFact(Base):
    """
    FIX M1 + FIX A: Merged from dw_schema.py. Added all 8 columns needed by engines.
    """
    __tablename__ = 'dw_shipment_facts'
    id                  = Column(Integer, primary_key=True)
    tenant_id           = Column(String(50), nullable=False, index=True)
    source_system       = Column(String(50))
    raw_source_uuid     = Column(String(100), index=True)
    po_number           = Column(String(100))
    origin_node         = Column(String(100), index=True)
    destination_node    = Column(String(100), index=True)
    current_status      = Column(String(50))
    total_value_usd     = Column(Float)
    margin_usd          = Column(Float)
    expected_payment_date = Column(DateTime(timezone=True))
    expected_arrival_utc  = Column(DateTime(timezone=True))
    actual_arrival_utc    = Column(DateTime(timezone=True), nullable=True)
    delay_days_calculated = Column(Integer, default=0)
    ml_confidence_score   = Column(Float)
    ml_risk_detected      = Column(Boolean, default=False)
    # FIX M1: Missing engine-critical fields added
    carrier                    = Column(String(100), default='unknown')
    route                      = Column(String(50), default='domestic')
    cargo_type                 = Column(String(50), default='general_cargo')
    industry_vertical          = Column(String(50), default='default')
    customer_tier              = Column(String(30), default='standard')
    contract_type              = Column(String(30), default='standard')
    # FIX: train_models.py SQL queries these two columns but they were missing.
    # Without them the DB training path always fails → always trains on synthetic data.
    total_cost_usd             = Column(Float)       # landed cost; used as ML feature
    credit_days                = Column(Integer, default=30)  # payment terms; used as ML feature
    # FIX: ETL pipeline (tasks.py) stamps this column but it wasn't in the schema —
    # so the value was silently dropped on every to_sql() call.
    nlp_extracted_penalty_rate = Column(Float, nullable=True)
    created_at                 = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    __table_args__ = (
        Index('idx_dw_shipment_tenant_status', 'tenant_id', 'current_status'),
        Index('idx_dw_shipment_tenant_created', 'tenant_id', 'created_at'),  # trend queries
    )


class DWNodeDimension(Base):
    __tablename__ = 'dw_node_dimensions'
    id               = Column(Integer, primary_key=True)
    tenant_id        = Column(String(50), nullable=False, index=True)
    node_id          = Column(String(100), unique=True, index=True)
    node_type        = Column(String(50))
    country          = Column(String(100))
    latitude         = Column(Float)
    longitude        = Column(Float)
    h3_index         = Column(String(15), index=True)   # links nodes to ExternalSpatialEvent lookups
    congestion_index = Column(Float, default=0.0)


class DWInventoryFact(Base):
    __tablename__ = 'dw_inventory_facts'
    id                  = Column(Integer, primary_key=True)
    tenant_id           = Column(String(50), nullable=False, index=True)
    node_id             = Column(String(100), index=True)
    sku_id              = Column(String(100), index=True)
    quantity_on_hand    = Column(Integer)
    quantity_in_transit = Column(Integer)
    safety_stock_level  = Column(Integer)
    days_of_supply      = Column(Float)
    last_updated        = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


class DWLaneDimension(Base):
    __tablename__ = 'dw_lane_dimensions'
    id                  = Column(Integer, primary_key=True)
    tenant_id           = Column(String(50), nullable=False, index=True)
    origin_node         = Column(String(100))
    destination_node    = Column(String(100))
    mode                = Column(String(20))                    # Ocean | Air | Rail | Truck
    avg_lead_time_days  = Column(Float)
    std_dev_lead_time   = Column(Float)
    cost_per_unit_usd   = Column(Float)
    __table_args__      = (
        # Route lookup is always (origin, destination) — compound index is critical
        Index('idx_lane_route', 'origin_node', 'destination_node'),
    )


class DWSupplierDimension(Base):
    __tablename__ = 'dw_supplier_dimensions'
    id                     = Column(Integer, primary_key=True)
    tenant_id              = Column(String(50), nullable=False, index=True)
    # FIX: was String(100) but Supplier.supplier_id is Integer — type mismatch caused silent ETL failures
    supplier_id            = Column(Integer, ForeignKey('suppliers.supplier_id'), unique=True)
    supplier_name          = Column(String(200))
    financial_health_score = Column(Float)
    on_time_delivery_rate  = Column(Float)
    geopolitical_risk_index= Column(Float)


class DWProductDimension(Base):
    __tablename__ = 'dw_product_dimensions'
    id                     = Column(Integer, primary_key=True)
    tenant_id              = Column(String(50), nullable=False)
    sku_id                 = Column(String(100), unique=True)
    category               = Column(String(100))
    unit_cost_usd          = Column(Float)
    holding_cost_daily     = Column(Float)
    stockout_penalty_daily = Column(Float)


class DWCustomerDimension(Base):
    __tablename__ = 'dw_customer_dimensions'
    id                  = Column(Integer, primary_key=True)
    tenant_id           = Column(String(50), nullable=False, index=True)
    # FIX: was String(100) but Customer.customer_id is Integer — type mismatch caused silent ETL failures
    customer_id         = Column(Integer, ForeignKey('customers.customer_id'), unique=True)
    customer_name       = Column(String(200))
    credit_days         = Column(Integer, default=30)
    payment_delay_days  = Column(Float, default=0.0)
    industry_risk_score = Column(Float, default=0.0)


# ============================================================================
# SECTION 7: RAG KNOWLEDGE STORE
# Stores embedded text chunks from carrier records, SLA contracts, shipment
# history, and decision logs. Used by the RAG retriever to ground LLM
# narratives in real, tenant-specific data instead of generic responses.
#
# pgvector extension must be enabled in PostgreSQL:
#   CREATE EXTENSION IF NOT EXISTS vector;
# ============================================================================

class KnowledgeChunk(Base):
    """
    A single embedded text chunk for the RAG knowledge base.
    Each row = one piece of grounding context (a carrier record, SLA clause,
    route performance summary, or historical decision outcome).
    """
    __tablename__ = "knowledge_chunks"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id   = Column(String(50), nullable=False, index=True)

    # What kind of data this chunk came from
    source_type = Column(String(50), nullable=False)
    # carrier_performance | sla_contract | shipment_history
    # route_performance   | decision_outcome | supplier_profile

    # FK back to the originating row (for staleness detection and refresh)
    source_id   = Column(String(100), nullable=True)

    # The plain-text chunk the LLM will read as context
    content     = Column(String, nullable=False)

    # 384-dim vector from sentence-transformers/all-MiniLM-L6-v2
    # Stored as JSON array — pgvector VECTOR type is used at query time via raw SQL
    # (avoids hard dependency on pgvector SQLAlchemy type at schema definition time)
    embedding_json = Column(String, nullable=True)   # JSON-serialized list[float]

    created_at  = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.datetime.utcnow,
                         onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_knowledge_chunks_tenant_source", "tenant_id", "source_type"),
    )


# ============================================================================
# SECTION 8: INITIALIZATION
# FIX A + FIX C + FIX E (SERIAL collision): Single create_all, no raw DDL.
# FIX F (seed): Fixed missing 'Supply Chain Analyst' profile name,
#               fixed financial_parameters missing tenant_id,
#               removed explicit PK inserts on SERIAL columns.
# ============================================================================

def _ensure_pgvector(engine):
    """Enable pgvector extension if available — safe no-op if not installed."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception:
        pass  # pgvector not installed on this DB — embedding search falls back to in-memory cosine


def initialize_db():
    import logging
    log = logging.getLogger(__name__)
    log.info(f"Connecting to Postgres at {DB_HOST}:{DB_PORT}/{DB_NAME}...")

    # FIX K: Connection pool config (prevents exhaustion on cloud)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_pre_ping=True
    )

    _ensure_pgvector(engine)

    # FIX A: Single create_all on the unified Base — creates ALL tables
    Base.metadata.create_all(engine)
    log.info("All tables created/verified via SQLAlchemy ORM.")

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        from app.financial_system.auth import get_password_hash

        # ── Seed default Tenant ─────────────────────────────────────────────
        existing_tenant = db.query(Tenant).filter_by(tenant_id="default_tenant").first()
        if not existing_tenant:
            db.add(Tenant(
                tenant_id="default_tenant",
                company_name="Fiscalogix Demo",
                subscription_tier="enterprise",
                billing_email="admin@fiscalogix.com",
                feature_flags={
                    "gnn_contagion": False,
                    "live_ais": False,
                    "multi_erp": False,
                    "carbon_model": False,
                },
            ))
            db.commit()

        # ── Seed Roles (single source of truth for permissions) ─────────────
        roles_to_seed = [
            {
                "name": "system_admin",
                "permissions": {
                    "is_admin": True, "can_view_all": True,
                    "can_view_dashboard": True, "can_view_matrix": True,
                    "can_view_revm": True, "can_view_liquidity": True,
                    "can_view_recovery": True, "can_view_governance": True,
                    "can_view_warehouse": True, "can_execute_actions": True,
                },
            },
            {
                "name": "executive",
                "permissions": {
                    "can_view_dashboard": True, "can_view_liquidity": True,
                    "can_view_recovery": True, "can_execute_actions": True,
                },
            },
            {
                "name": "financial_analyst",
                "permissions": {
                    "can_view_dashboard": True, "can_view_revm": True,
                    "can_view_recovery": True,
                },
            },
            {
                "name": "supply_chain_analyst",
                "permissions": {
                    "can_view_dashboard": True, "can_view_matrix": True,
                    "can_view_revm": True,
                },
            },
            {
                "name": "auditor",
                "permissions": {
                    "can_view_governance": True, "can_view_warehouse": True,
                    "can_view_dashboard": True,
                },
            },
        ]
        for r in roles_to_seed:
            if not db.query(Role).filter_by(name=r["name"]).first():
                db.add(Role(name=r["name"], permissions=r["permissions"]))
        db.commit()

        # ── Seed display-name Profiles (JWT profile_name label only) ────────
        profiles_to_seed = [
            "System Admin", "Executive", "Financial Analyst",
            "Supply Chain Analyst", "Supply Chain Ops", "Auditor",
        ]
        for name in profiles_to_seed:
            if not db.query(Profile).filter_by(name=name).first():
                db.add(Profile(name=name))
        db.commit()

        # ── Seed default financial parameters ───────────────────────────────
        if not db.query(FinancialParameter).filter_by(tenant_id="default_tenant").first():
            db.add(FinancialParameter(tenant_id="default_tenant", wacc=0.08, penalty_rate=0.05))
            db.commit()

        # ── Seed test users ─────────────────────────────────────────────────
        admin_role   = db.query(Role).filter_by(name="system_admin").first()
        analyst_role = db.query(Role).filter_by(name="supply_chain_analyst").first()
        admin_profile   = db.query(Profile).filter_by(name="System Admin").first()
        analyst_profile = db.query(Profile).filter_by(name="Supply Chain Analyst").first()

        test_users = [
            {"username": "admin@fiscalogix.com",   "password": "admin123",   "role": admin_role,   "profile": admin_profile},
            {"username": "analyst@fiscalogix.com", "password": "analyst123", "role": analyst_role, "profile": analyst_profile},
        ]
        for u in test_users:
            if not db.query(User).filter_by(username=u["username"]).first() and u["role"]:
                db.add(User(
                    tenant_id="default_tenant",
                    username=u["username"],
                    hashed_password=get_password_hash(u["password"]),
                    role_id=u["role"].id,
                    profile_id=u["profile"].id if u["profile"] else None,
                ))
        db.commit()

        # ── Seed demo Warehouse ─────────────────────────────────────────────
        if not db.query(Warehouse).filter_by(tenant_id="default_tenant").first():
            db.add(Warehouse(
                tenant_id="default_tenant",
                warehouse_name="Mumbai Central DC",
                country_code="IND",
                city="Mumbai",
                latitude=19.0760,
                longitude=72.8777,
                h3_index="86634723fffffff",
                capacity_units=50000,
                cost_per_unit_per_day=2.5,
            ))
            db.commit()

        # ── Seed Port Registry (12 major world ports with real demurrage data) ──
        # FIX: seed dicts previously used "lat"/"lon" keys but PortRegistry model
        # defines "latitude"/"longitude". SQLAlchemy raises TypeError on unknown kwargs,
        # so all 12 ports were failing to seed their coordinates.
        ports_to_seed = [
            {"port_id": "USMIA", "port_name": "Port of Miami",       "country_code": "USA", "latitude": 25.7742,  "longitude": -80.1889,  "h3_index": "8844c1a3fffffff", "demurrage_per_day": 50000, "storage_per_day": 200, "peak_risk_months": [11, 12, 1]},
            {"port_id": "USSAV", "port_name": "Port of Savannah",    "country_code": "USA", "latitude": 32.0835,  "longitude": -81.0998,  "h3_index": "8844c0a3fffffff", "demurrage_per_day": 25000, "storage_per_day": 150, "peak_risk_months": [8, 9]},
            {"port_id": "USHOU", "port_name": "Port of Houston",     "country_code": "USA", "latitude": 29.7604,  "longitude": -95.3698,  "h3_index": "8844c503fffffff", "demurrage_per_day": 40000, "storage_per_day": 175, "peak_risk_months": [9, 10]},
            {"port_id": "USLOS", "port_name": "Port of Los Angeles", "country_code": "USA", "latitude": 33.7296,  "longitude": -118.2656, "h3_index": "8844e66bfffffff", "demurrage_per_day": 65000, "storage_per_day": 300, "peak_risk_months": [11, 12]},
            {"port_id": "SGSIN", "port_name": "Port of Singapore",   "country_code": "SGP", "latitude": 1.2897,   "longitude": 103.8501,  "h3_index": "8865b12bfffffff", "demurrage_per_day": 45000, "storage_per_day": 220, "peak_risk_months": []},
            {"port_id": "CNSHA", "port_name": "Port of Shanghai",    "country_code": "CHN", "latitude": 31.2304,  "longitude": 121.4737,  "h3_index": "8860c507fffffff", "demurrage_per_day": 30000, "storage_per_day": 130, "peak_risk_months": [1, 2]},
            {"port_id": "AEDXB", "port_name": "Port of Jebel Ali",  "country_code": "ARE", "latitude": 24.9858,  "longitude": 55.0272,   "h3_index": "88601a43fffffff", "demurrage_per_day": 35000, "storage_per_day": 160, "peak_risk_months": [6, 7, 8]},
            {"port_id": "DEHAM", "port_name": "Port of Hamburg",     "country_code": "DEU", "latitude": 53.5753,  "longitude": 10.0153,   "h3_index": "886196cbfffffff", "demurrage_per_day": 55000, "storage_per_day": 250, "peak_risk_months": [12, 1]},
            {"port_id": "NLRTM", "port_name": "Port of Rotterdam",   "country_code": "NLD", "latitude": 51.9244,  "longitude": 4.4777,    "h3_index": "8861a317fffffff", "demurrage_per_day": 60000, "storage_per_day": 280, "peak_risk_months": [12, 1]},
            {"port_id": "INMUN", "port_name": "Mumbai JNPT",         "country_code": "IND", "latitude": 18.9481,  "longitude": 72.9359,   "h3_index": "86634723fffffff",  "demurrage_per_day": 15000, "storage_per_day": 80,  "peak_risk_months": [6, 7, 8, 9]},
            {"port_id": "INCCU", "port_name": "Kolkata Port",        "country_code": "IND", "latitude": 22.5726,  "longitude": 88.3639,   "h3_index": "8663a3a3fffffff",  "demurrage_per_day": 10000, "storage_per_day": 60,  "peak_risk_months": [6, 7]},
            {"port_id": "JPYOK", "port_name": "Port of Yokohama",    "country_code": "JPN", "latitude": 35.4437,  "longitude": 139.6380,  "h3_index": "8860c463fffffff",  "demurrage_per_day": 42000, "storage_per_day": 190, "peak_risk_months": []},
        ]
        for p in ports_to_seed:
            exists = db.get(PortRegistry, p["port_id"])
            if not exists:
                db.add(PortRegistry(**p))
        db.commit()

        # ── Seed Demo Supplier ──────────────────────────────────────────────
        existing_sup = db.query(Supplier).filter_by(tenant_id="default_tenant").first()
        if not existing_sup:
            db.add(Supplier(
                tenant_id="default_tenant",
                supplier_name="Acme Global Logistics",
                country_code="SGP",
                carrier_preference="maersk",
                financial_health_score=0.82,
                on_time_delivery_rate=0.91,
                geopolitical_risk_index=0.15,
            ))
            db.commit()

        log.info("Database initialized and seeded successfully.")


    except Exception as e:
        db.rollback()
        log.error(f"Seed failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    initialize_db()
