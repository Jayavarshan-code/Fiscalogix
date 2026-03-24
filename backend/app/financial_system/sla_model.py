class SLAPenaltyModel:
    """
    Models strict On-Time In-Full (OTIF) contractual penalties imposed by enterprise buyers.
    """
    def compute(self, row, predicted_delay):
        """
        Calculates the financial fine deducted from the invoice if the shipment fails its SLA.
        Standard enterprise logic: 3% penalty per day late, capped at 15%.
        """
        if predicted_delay <= 0:
            return 0.0
            
        order_value = row.get("order_value", 0.0)
        
        # Determine strictness of customer SLA based on credit terms
        # If they pay in 15 days, they are a strict priority customer (higher penalties)
        credit_days = row.get("credit_days", 30)
        daily_penalty_rate = 0.03 if credit_days <= 30 else 0.015
        
        # Max out the penalty so an order doesn't become totally worthless (unless goods spoil)
        max_penalty_cap = 0.15 
        
        total_penalty_pct = min(predicted_delay * daily_penalty_rate, max_penalty_cap)
        financial_penalty = order_value * total_penalty_pct
        
        return round(financial_penalty, 2)
        
    def compute_batch(self, rows_list, delays_array):
        return [self.compute(row, delays_array[i]) for i, row in enumerate(rows_list)]
