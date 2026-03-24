import csv
import random
from datetime import datetime, timedelta

def generate_synthetic_shipments(num_rows=5000):
    filename = 'synthetic_shipments.csv'
    headers = ["PO#", "Ship From", "Destination", "Status", "Total Amount", "Expected Arrival", "Carrier Reference", "Internal Notes"]
    nodes = ["Shanghai Port", "Los Angeles Port", "Rotterdam", "Dallas DC", "Berlin Factory", "Tokyo Port"]
    statuses = ["IN_TRANSIT", "AT_PORT", "DELAYED", "CUSTOMS_HOLD", "DELIVERED"]

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for i in range(num_rows):
            po_num = f"PO-{random.randint(100000, 999999)}"
            origin = random.choice(nodes)
            dest = random.choice([n for n in nodes if n != origin])
            status = random.choices(statuses, weights=[0.5, 0.2, 0.1, 0.05, 0.15])[0]
            amount = round(random.uniform(5000, 250000), 2)
            days_offset = random.randint(-10, 30)
            arrival = (datetime.utcnow() + timedelta(days=days_offset)).strftime("%Y-%m-%d %H:%M:%S")
            carrier_ref = f"CARR-{random.randint(1000, 9999)}"
            notes = "Handle with care" if random.random() > 0.8 else ""
            writer.writerow([po_num, origin, dest, status, amount, arrival, carrier_ref, notes])
    print(f"✅ Generated {filename}")

def generate_synthetic_inventory(num_rows=1000):
    filename = 'synthetic_inventory.csv'
    headers = ["Warehouse ID", "Item Number", "QOH", "Incoming", "Safety Limit", "Bin Location"]
    nodes = ["Dallas DC", "Berlin Factory", "Tokyo Port"]
    
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for i in range(num_rows):
            node = random.choice(nodes)
            sku = f"SKU-{random.randint(100, 999)}"
            qoh = random.randint(10, 10000)
            incoming = random.randint(0, 500)
            safety = random.randint(100, 500)
            bin_loc = f"BIN-{random.randint(1,40)}"
            writer.writerow([node, sku, qoh, incoming, safety, bin_loc])
    print(f"✅ Generated {filename}")

def generate_synthetic_suppliers(num_rows=50):
    filename = 'synthetic_suppliers.csv'
    headers = ["Vendor ID", "Company Name", "D&B Score", "OTIF", "Country Risk"]
    
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for i in range(num_rows):
            vendor = f"VEND-{random.randint(1000, 9999)}"
            name = f"Supplier Global {i}"
            score = round(random.uniform(2.0, 9.9), 1)
            otif = round(random.uniform(60.0, 99.9), 1)
            risk = round(random.uniform(1.0, 5.0), 1)
            writer.writerow([vendor, name, score, otif, risk])
    print(f"✅ Generated {filename}")

if __name__ == "__main__":
    generate_synthetic_shipments()
    generate_synthetic_inventory()
    generate_synthetic_suppliers()
