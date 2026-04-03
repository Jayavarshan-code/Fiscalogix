import json
import random
from datetime import datetime, timedelta

def generate_realistic_data(rows=1000):
    data = []
    ports = ["Mundra", "Shanghai", "Singapore", "Jebel Ali", "Rotterdam"]
    hs_codes = ["8414.59", "3004.90", "8517.13", "8471.30"]
    
    for i in range(rows):
        # Inject an anomaly every 50 rows
        is_anomaly = (i % 50 == 0)
        
        shipment = {
            "shipment_id": f"SHIP-{1000+i}",
            "value_usd": random.randint(100000, 5000000),
            "origin": random.choice(ports),
            "destination": random.choice(ports),
            "lat": random.uniform(-90, 90),
            "lon": random.uniform(-180, 180),
            "speed_knots": random.uniform(2, 25) if not is_anomaly else random.uniform(0, 2),
            "hs_code": random.choice(hs_codes),
            "ocr_text": f"Bill of Lading #BL-{i} | Consignee: {random.choice(ports)}",
            "congestion_status": random.choice([True, False]),
            "license_expiry": (datetime.now() + timedelta(days=random.randint(-30, 365))).strftime("%Y-%m-%d"),
            "is_anomaly": is_anomaly
        }
        data.append(shipment)
        
    return data

if __name__ == "__main__":
    load_test_data = generate_realistic_data(1000)
    with open("c:/Users/varshan/fiscalogix/scripts/test_load_1000.json", "w") as f:
        json.dump(load_test_data, f, indent=2)
    print(f"Generated 1000 rows of test data in c:/Users/varshan/fiscalogix/scripts/test_load_1000.json")
