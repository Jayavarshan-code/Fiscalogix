from datetime import datetime, timedelta

class CashEventGenerator:
    def compute(self, enriched_records):
        """
        Converts operational supply chain events into precise financial Cash Events (Inflows/Outflows)
        """
        events = []
        today = datetime.now().date()
        
        for row in enriched_records:
            shipment_id = row["shipment_id"]
            order_val = row["order_value"]
            total_cost = row["total_cost"]
            
            # Predict when cash officially enters the bank
            predicted_delay = row.get("predicted_delay", row.get("delay_days", 0))
            credit_days = row.get("credit_days", 0)
            payment_delay = row.get("payment_delay_days", 0)
            
            # Cash actually lands when: item is delivered (predicted_delay) + payment terms (credit_days + payment_delay)
            inflow_days = int(predicted_delay + credit_days + payment_delay)
            inflow_date = today + timedelta(days=inflow_days)
            
            # Cash outflow (Logistics, Warehouse, Inventory costs) mostly paid early
            outflow_date = today + timedelta(days=5) # Example standard Accounts Payable logic
            
            events.append({
                "shipment_id": shipment_id,
                "event_date": outflow_date,
                "event_type": "OUTFLOW",
                "amount": float(total_cost),
                "priority": "committed", # AP must be paid
                "description": f"Cost payout for shipment {shipment_id}"
            })
            
            events.append({
                "shipment_id": shipment_id,
                "event_date": inflow_date,
                "event_type": "INFLOW",
                "amount": float(order_val),
                "priority": "flexible", # AR timeline can slip
                "description": f"Revenue realized from shipment {shipment_id}"
            })
            
        return events
