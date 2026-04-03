import csv
import random
import uuid
from datetime import datetime, timedelta

NUM_ROWS = 30000
FILENAME = "fiscalogix_30k_test_dump.csv"

# Reference data banks
ORIGINS = ["Shanghai, CN", "Shenzhen, CN", "Singapore, SG", "Rotterdam, NL", "Hamburg, DE", "Los Angeles, US", "Mumbai, IN"]
DESTINATIONS = ["New York, US", "Long Beach, US", "Antwerp, BE", "Dubai, AE", "Felixstowe, UK", "Colombo, LK"]
INCOTERMS = ["FOB", "CIF", "EXW", "DDP", "FCA"]
CARRIERS = ["Maersk", "MSC", "CMA CGM", "Hapag-Lloyd", "Evergreen", "ONE"]
STATUSES = ["Delivered", "In Transit", "Port Congestion", "Customs Hold", "Blank Sail"]
CLAUSES = ["None", "Clause 4.1: Demurrage Breach", "Clause 7.2: Delay Penalty", "Clause 12: Force Majeure", "Clause 3.3: SLA Miss"]

def random_date(start, end):
    return start + timedelta(
        seconds=random.randint(0, int((end - start).total_seconds()))
    )

print(f"Synthesizing {NUM_ROWS} records of 13-Pillar Supply Chain Data...")

start_date = datetime(2025, 1, 1)
end_date = datetime(2026, 3, 31)

with open(FILENAME, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # Headers aligned with the 13 Pillars
    writer.writerow([
        "shipment_id", "po_number", "bol_number", "contract_id",
        "origin", "destination", "carrier", "incoterm",
        "dispatch_date", "planned_arrival", "actual_arrival",
        "planned_transit_days", "actual_transit_days", "delay_days",
        "invoice_value_usd", "freight_cost_usd", "demurrage_incurred_usd",
        "sla_breach", "penalty_clause_triggered", "status"
    ])
    
    for i in range(NUM_ROWS):
        shipment_id = f"LGX-{100000 + i}"
        po_number = f"PO-{random.randint(1000, 99999)}"
        bol_number = f"BOL-{str(uuid.uuid4())[:8].upper()}"
        contract_id = f"MSA-{random.randint(100, 500)}"
        
        origin = random.choice(ORIGINS)
        destination = random.choice(DESTINATIONS)
        carrier = random.choice(CARRIERS)
        incoterm = random.choice(INCOTERMS)
        
        # Timeline generation
        dispatch = random_date(start_date, end_date)
        planned_transit = random.randint(14, 45)
        planned_arrival = dispatch + timedelta(days=planned_transit)
        
        # Inject realistic delays (let 20% of shipments experience severe delays)
        is_delayed = random.random() < 0.20
        delay = random.randint(3, 25) if is_delayed else random.randint(-2, 2)
        
        actual_transit = planned_transit + delay
        actual_arrival = dispatch + timedelta(days=actual_transit) if actual_transit > 0 else planned_arrival
        
        delay_days = max(0, actual_transit - planned_transit)
        
        # Financials
        invoice_value = round(random.uniform(50000, 2500000), 2)
        freight_cost = round(invoice_value * random.uniform(0.04, 0.12), 2)
        
        # Demurrage/Detention logic (highly likely if delayed at port)
        demurrage = 0.0
        sla_breach = "FALSE"
        penalty_clause = "None"
        status = random.choice(STATUSES)
        
        if delay_days > 3:
            sla_breach = "TRUE"
            if status == "Delivered":
                status = random.choice(["Port Congestion", "Customs Hold"]) # retroactively mark reason
            demurrage = round(delay_days * random.uniform(500, 2500), 2)
            penalty_clause = random.choice([c for c in CLAUSES if c != "None"])
        else:
            if status in ["Port Congestion", "Customs Hold"]:
                status = "Delivered" # Fix logic for non-delayed
                
        # Handle Force Majeure overrides
        if penalty_clause == "Clause 12: Force Majeure":
            sla_breach = "FALSE (Excused)"
            
        writer.writerow([
            shipment_id, po_number, bol_number, contract_id,
            origin, destination, carrier, incoterm,
            dispatch.strftime("%Y-%m-%d"), 
            planned_arrival.strftime("%Y-%m-%d"), 
            actual_arrival.strftime("%Y-%m-%d"),
            planned_transit, actual_transit, delay_days,
            invoice_value, freight_cost, demurrage,
            sla_breach, penalty_clause, status
        ])

print(f"Success. Dump generated at: {FILENAME}")
