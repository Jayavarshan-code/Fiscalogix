import random
from sqlalchemy import create_engine, text
import os

DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "password123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "fiscalogix")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def seed_db():
    print(f"Connecting to Postgres at {DB_HOST}:{DB_PORT}/{DB_NAME} to seed data...")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        with conn.begin():
            # 1. Financial Parameters
            conn.execute(text("INSERT INTO financial_parameters (wacc, penalty_rate) VALUES (0.08, 0.05);"))
            
            # 2. SKU
            for i in range(1, 51):
                unit_cost = round(random.uniform(10.0, 500.0), 2)
                holding_cost = round(unit_cost * 0.005, 4) # 0.5% holding cost per day
                conn.execute(
                    text("INSERT INTO sku (sku_id, holding_cost_per_day, unit_cost) VALUES (:id, :hc, :uc)"),
                    {"id": i, "hc": holding_cost, "uc": unit_cost}
                )
                
            # 3. Customers
            for i in range(1, 21):
                credit_days = random.choice([0, 15, 30, 45, 60, 90])
                payment_delay_days = random.randint(0, 15) if credit_days > 0 else 0
                conn.execute(
                    text("INSERT INTO customers (customer_id, credit_days, payment_delay_days) VALUES (:id, :cd, :pdd)"),
                    {"id": i, "cd": credit_days, "pdd": payment_delay_days}
                )
                
            # 4. Inventory
            for i in range(1, 101):
                sku_id = random.randint(1, 50)
                warehouse_id = random.randint(1, 5)
                quantity = random.randint(50, 1000)
                conn.execute(
                    text("INSERT INTO inventory (inventory_id, sku_id, warehouse_id, quantity) VALUES (:id, :sku, :wh, :qty)"),
                    {"id": i, "sku": sku_id, "wh": warehouse_id, "qty": quantity}
                )
                
            # 5. Orders
            for i in range(1, 201): # 200 Mock Orders
                sku_id = random.randint(1, 50)
                customer_id = random.randint(1, 20)
                qty = random.randint(1, 100)
                # fetching roughly estimated order value based on a base scale
                order_value = round(qty * random.uniform(15.0, 800.0), 2)
                conn.execute(
                    text("INSERT INTO orders (order_id, sku_id, customer_id, order_value) VALUES (:id, :sku, :cust, :val)"),
                    {"id": i, "sku": sku_id, "cust": customer_id, "val": order_value}
                )
                
            # 6. Shipments
            for i in range(1, 201): # 1 shipment per order for simplicity
                order_id = i
                shipment_cost = round(random.uniform(500.0, 5000.0), 2)
                
                # simulate some delays
                delay_days = 0 
                if random.random() < 0.2:
                    delay_days = random.randint(1, 14)

                conn.execute(
                    text("INSERT INTO shipments (shipment_id, order_id, shipment_cost, delay_days) VALUES (:id, :oid, :cost, :delay)"),
                    {"id": i, "oid": order_id, "cost": shipment_cost, "delay": delay_days}
                )

    print("✅ Synethic 'Actual' Operations data successfully loaded into PostgreSQL!")

if __name__ == "__main__":
    seed_db()
