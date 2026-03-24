import os
from sqlalchemy import create_engine, text, Column, Integer, String, ForeignKey, JSON, DateTime, Float, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "password123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "fiscalogix")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

Base = declarative_base()

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(String(50), nullable=False) # SYSTEM or actual user
    action_type = Column(String(50), nullable=False) # e.g. REROUTE
    target_entity_id = Column(String(100), nullable=False) # e.g. Shipment ID
    previous_state = Column(JSON)
    new_state = Column(JSON)
    confidence_score = Column(Float)
    erp_receipt = Column(JSON)

class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    permissions = Column(JSON) # e.g. {"can_execute": true}

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    parent_role_id = Column(Integer, ForeignKey('roles.id'), nullable=True)

class PermissionSet(Base):
    __tablename__ = 'permission_sets'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    permissions = Column(JSON)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    profile_id = Column(Integer, ForeignKey('profiles.id'))
    role_id = Column(Integer, ForeignKey('roles.id'))
    
class UserPermissionSet(Base):
    __tablename__ = 'user_permission_sets'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    permission_set_id = Column(Integer, ForeignKey('permission_sets.id'), primary_key=True)

# The instruction provided an incomplete and syntactically incorrect class definition for SKU.
# I will assume the intent was to add the AuditLog class and keep the existing initialize_db function
# for table creation, and not to introduce ORM-based table creation for all tables yet.
# The `class SKU(Base):(SQLALCHEMY_DATABASE_URL)` part was malformed and seems to be a copy-paste error.
# I will only add the AuditLog class and the necessary imports and Base definition.

def initialize_db():
    print(f"Connecting to Postgres at {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS sku (
                    sku_id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) DEFAULT 'default_tenant',
                    holding_cost_per_day DOUBLE PRECISION,
                    unit_cost DOUBLE PRECISION
                );
            '''))
            
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    user_id VARCHAR(50) NOT NULL,
                    action_type VARCHAR(50) NOT NULL,
                    target_entity_id VARCHAR(100) NOT NULL,
                    previous_state JSON,
                    new_state JSON,
                    confidence_score DOUBLE PRECISION,
                    erp_receipt JSON
                );
            '''))
            
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) DEFAULT 'default_tenant',
                    credit_days INTEGER DEFAULT 0,
                    payment_delay_days INTEGER DEFAULT 0
                );
            '''))
            
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) DEFAULT 'default_tenant',
                    sku_id INTEGER,
                    customer_id INTEGER,
                    order_value DOUBLE PRECISION,
                    FOREIGN KEY (sku_id) REFERENCES sku (sku_id),
                    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
                );
            '''))
            
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS shipments (
                    shipment_id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) DEFAULT 'default_tenant',
                    order_id INTEGER,
                    shipment_cost DOUBLE PRECISION,
                    delay_days INTEGER,
                    FOREIGN KEY (order_id) REFERENCES orders (order_id)
                );
            '''))
            
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS financial_parameters (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) DEFAULT 'default_tenant',
                    wacc DOUBLE PRECISION,
                    penalty_rate DOUBLE PRECISION
                );
            '''))
            
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS inventory (
                    inventory_id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) DEFAULT 'default_tenant',
                    sku_id INTEGER,
                    warehouse_id INTEGER,
                    quantity INTEGER,
                    FOREIGN KEY (sku_id) REFERENCES sku (sku_id)
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS dw_shipment_facts (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) NOT NULL,
                    source_system VARCHAR(50),
                    raw_source_uuid VARCHAR(100),
                    po_number VARCHAR(100),
                    origin_node VARCHAR(100),
                    destination_node VARCHAR(100),
                    current_status VARCHAR(50),
                    total_value_usd DOUBLE PRECISION,
                    margin_usd DOUBLE PRECISION,
                    expected_payment_date TIMESTAMP,
                    expected_arrival_utc TIMESTAMP,
                    actual_arrival_utc TIMESTAMP,
                    delay_days_calculated INTEGER DEFAULT 0,
                    ml_confidence_score DOUBLE PRECISION,
                    ml_risk_detected BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS dw_node_dimensions (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) NOT NULL,
                    node_id VARCHAR(100) UNIQUE,
                    node_type VARCHAR(50),
                    country VARCHAR(100),
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    congestion_index DOUBLE PRECISION DEFAULT 0.0
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS dw_inventory_facts (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) NOT NULL,
                    node_id VARCHAR(100),
                    sku_id VARCHAR(100),
                    quantity_on_hand INTEGER,
                    quantity_in_transit INTEGER,
                    safety_stock_level INTEGER,
                    days_of_supply DOUBLE PRECISION,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS dw_lane_dimensions (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) NOT NULL,
                    origin_node VARCHAR(100),
                    destination_node VARCHAR(100),
                    mode VARCHAR(20),
                    avg_lead_time_days DOUBLE PRECISION,
                    std_dev_lead_time DOUBLE PRECISION,
                    cost_per_unit_usd DOUBLE PRECISION
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS dw_supplier_dimensions (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) NOT NULL,
                    supplier_id VARCHAR(100) UNIQUE,
                    supplier_name VARCHAR(200),
                    financial_health_score DOUBLE PRECISION,
                    on_time_delivery_rate DOUBLE PRECISION,
                    geopolitical_risk_index DOUBLE PRECISION
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS dw_product_dimensions (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) NOT NULL,
                    sku_id VARCHAR(100) UNIQUE,
                    category VARCHAR(100),
                    unit_cost_usd DOUBLE PRECISION,
                    holding_cost_daily DOUBLE PRECISION,
                    stockout_penalty_daily DOUBLE PRECISION
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS profiles (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    permissions JSON
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    parent_role_id INTEGER REFERENCES roles(id)
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS permission_sets (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    permissions JSON
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(50) NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    profile_id INTEGER REFERENCES profiles(id),
                    role_id INTEGER REFERENCES roles(id)
                );
            '''))

            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS user_permission_sets (
                    user_id INTEGER REFERENCES users(id),
                    permission_set_id INTEGER REFERENCES permission_sets(id),
                    PRIMARY KEY (user_id, permission_set_id)
                );
            '''))
            
            # Seed Mock RBAC Data for Testing
            conn.execute(text('''
                INSERT INTO profiles (name, permissions)
                VALUES ('System Admin', '{"can_view": true, "can_execute": true}')
                ON CONFLICT (name) DO NOTHING;
            '''))
            
            conn.execute(text('''
                INSERT INTO profiles (name, permissions)
                VALUES ('Supply Chain Analyst', '{"can_view": true, "can_execute": false}')
                ON CONFLICT (name) DO NOTHING;
            '''))
            
            
            # Setup Initial Passwords using our Auth utilities
            from app.financial_system.auth import get_password_hash
            hashed_admin = get_password_hash("admin123")
            hashed_analyst = get_password_hash("analyst123")
            
            conn.execute(text(f'''
                INSERT INTO users (tenant_id, username, hashed_password, profile_id)
                SELECT 'default_tenant', 'admin@fiscalogix.com', '{hashed_admin}', id FROM profiles WHERE name = 'System Admin'
                ON CONFLICT (username) DO NOTHING;
            '''))
            
            conn.execute(text(f'''
                INSERT INTO users (tenant_id, username, hashed_password, profile_id)
                SELECT 'default_tenant', 'analyst@fiscalogix.com', '{hashed_analyst}', id FROM profiles WHERE name = 'Supply Chain Analyst'
                ON CONFLICT (username) DO NOTHING;
            '''))

    print("✅ Database tables and mock RBAC users successfully created in PostgreSQL!")

if __name__ == "__main__":
    initialize_db()
