class SLAPenaltyModel:
    """
    Models strict On-Time In-Full (OTIF) contractual penalties imposed by enterprise buyers.
    Penalty rate is sourced from the NLP Contract Extractor when available.
    """
    def compute(self, row, predicted_delay):
        """
        Calculates the financial fine deducted from the invoice if the shipment fails its SLA.
        Priority:
          1. NLP-extracted penalty rate from uploaded contract PDF
          2. Credit-tier heuristic fallback (3% priority / 1.5% standard)
        Cap: 15% of order value max.
        """
        if predicted_delay <= 0:
            return 0.0

        order_value = row.get("order_value", 0.0)

        # Priority 1: Use the real NLP-extracted rate from the ETL pipeline
        nlp_rate = row.get("nlp_extracted_penalty_rate", None)
        if nlp_rate is not None and nlp_rate > 0:
            daily_penalty_rate = float(nlp_rate)
        else:
            # Priority 2: Credit-tier heuristic
            credit_days = row.get("credit_days", 30)
            daily_penalty_rate = 0.03 if credit_days <= 30 else 0.015

        # Cap at 15% of order value
        max_penalty_cap = 0.15
        total_penalty_pct = min(predicted_delay * daily_penalty_rate, max_penalty_cap)
        financial_penalty = order_value * total_penalty_pct

        return round(financial_penalty, 2)

    def compute_batch(self, rows_list, delays_array):
        return [self.compute(row, delays_array[i]) for i, row in enumerate(rows_list)]
