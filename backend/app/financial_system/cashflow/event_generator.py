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
            
            # P3-3 FIX: Derive AP outflow date from actual supplier payment terms.
            # WHAT WAS WRONG: hardcoded day-5 clustered ALL supplier cost payments
            # on the same near-future date regardless of contract terms. This created
            # a phantom cash deficit spike 5 days out even when real terms are Net-30
            # or Net-60, making the timeline misleading for cashflow planning.
            # FIX: read supplier_payment_terms from the row (populated from ERP/contract
            # data). Default to 30 days (Net-30) — industry standard for B2B logistics.
            supplier_terms = int(row.get("supplier_payment_terms", 30))
            outflow_date = today + timedelta(days=max(1, supplier_terms))
            
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
