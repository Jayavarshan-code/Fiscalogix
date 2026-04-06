class SLAPenaltyModel:
    """
    Models strict On-Time In-Full (OTIF) contractual penalties imposed by enterprise buyers.
    Penalty rate is sourced from the NLP Contract Extractor when available.

    WHY THE OLD CAP WAS FLAWED:
    Previously, `max_penalty_cap = 0.15` (15%) was hardcoded for ALL contracts.
    This is dangerously wrong for enterprise buyers like FMCG giants (Walmart, Reliance Retail)
    who include "Full Rejection" clauses — where a 1-day delay results in the ENTIRE
    cargo being rejected and 100% of the invoice being voided.
    Capping these at 15% would make Fiscalogix recommend "minor delay" when the actual
    outcome is a total loss of the shipment value. This is a catastrophic planning error.

    FIX: The `contract_type` field (extracted by the NLP ETL pipeline from the PDF) now
    determines the penalty cap:
    - "full_rejection": cap = 100% (cargo rejected, full loss)
    - "strict":         cap = 30% (aggressive penalty schedule)
    - "standard":       cap = 15% (default OTIF industry standard)
    - "lenient":        cap = 5%  (negotiated soft SLA)
    """

    CONTRACT_TYPE_CAPS = {
        "full_rejection": 1.00,   # Entire cargo voided — Walmart-style OTIF enforcement
        "strict":         0.30,   # Aggressive SLA, common in pharma/auto supply
        "standard":       0.15,   # Default OTIF (most enterprise and 3PL contracts)
        "lenient":        0.05,   # Negotiated grace-window SLA
    }

    def compute(self, row, predicted_delay):
        """
        Calculates the financial fine deducted from the invoice if the shipment fails its SLA.
        Priority for penalty rate:
          1. NLP-extracted rate from uploaded contract PDF
          2. Credit-tier heuristic fallback (3% priority / 1.5% standard)
        Cap is determined by the contract_type field (also NLP-extracted).
        """
        if predicted_delay <= 0:
            return 0.0

        order_value = row.get("order_value", 0.0)

        # Priority 1: NLP-extracted daily penalty rate from the ETL pipeline
        nlp_rate = row.get("nlp_extracted_penalty_rate", None)
        if nlp_rate is not None and nlp_rate > 0:
            daily_penalty_rate = float(nlp_rate)
        else:
            # Priority 2: Credit-tier heuristic fallback
            credit_days = row.get("credit_days", 30)
            daily_penalty_rate = 0.03 if credit_days <= 30 else 0.015

        # Determine penalty cap from contract type (NLP-extracted or default)
        contract_type = str(row.get("contract_type", "standard")).lower().strip()
        max_penalty_cap = self.CONTRACT_TYPE_CAPS.get(contract_type, self.CONTRACT_TYPE_CAPS["standard"])

        total_penalty_pct = min(predicted_delay * daily_penalty_rate, max_penalty_cap)
        financial_penalty = order_value * total_penalty_pct

        return round(financial_penalty, 2)

    def compute_batch(self, rows_list, delays_array):
        return [self.compute(row, delays_array[i]) for i, row in enumerate(rows_list)]
