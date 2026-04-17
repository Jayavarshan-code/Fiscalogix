class DecisionEngine:
    """
    Translates ReVM intelligence into deterministic Supply Chain actions using
    magnitude-aware multi-tier decision logic.

    WHY THE HARDCODED IF/ELIF WAS FLAWED:
    The previous version used two binary thresholds:
      - if revm < 0 → CANCEL/INTERVENE
      - elif risk_prob > 0.7 → FLAG FOR REVIEW
    This creates TWO critical failures:
    
    1. Binary cliff edge: A shipment with revm = -$1 and one with revm = -$500,000
       both receive exactly "CANCEL/DELAY SHIPMENT". No magnitude awareness.
       A CFO cannot act on this — they need to know the SEVERITY.
    
    2. Missing middle tier: There is no "Watch this closely" state. A shipment
       with revm = +$200 and risk = 65% (close to both thresholds) gets APPROVE.
       In reality, this needs a MONITOR recommendation so the logistics team
       can keep tabs on it without full intervention.
    
    3. Hardcoded `0.7` risk threshold with no contextual adjustment: A risk score
       of 0.7 on a $500 domestic shipment is very different from 0.7 on a $2M
       transoceanic container. The threshold should scale with exposure.

    FIX: 5-tier magnitude-aware decision taxonomy:
    - APPROVE EXECUTION        → Structurally healthy
    - MONITOR CLOSELY          → Marginal; watch for degradation
    - ESCALATE TO MANAGEMENT   → Significant risk, not yet terminal
    - INTERVENE IMMEDIATELY    → High magnitude negative ReVM
    - CANCEL / DO NOT SHIP     → Terminal — confirmed capital destruction
    Risk threshold now scales with order_value exposure.
    """

    # ReVM severity thresholds as % of order_value (magnitude-aware)
    MINOR_LOSS_PCT   = -0.02   # < 2% of order value — marginal
    MODERATE_LOSS_PCT = -0.10  # 2–10% of order value — significant
    SEVERE_LOSS_PCT   = -0.25  # > 25% of order value — severe

    def compute(self, row):
        revm        = float(row.get("revm")        or 0)
        risk_prob   = float(row.get("risk_score")  or 0)
        confidence  = float(row.get("risk_confidence") or 0.5)
        order_value = max(float(row.get("order_value") or 1), 1)  # prevent div/0

        # Normalize ReVM loss to percentage of order value for magnitude awareness
        revm_pct = revm / order_value

        # Scale risk trigger threshold based on exposure:
        # Large shipments ($500K+) need earlier intervention than small ones ($5K).
        # Threshold ranges from 0.65 (large exposure) to 0.80 (small exposure).
        exposure_factor = min(order_value / 100_000, 1.0)           # caps at 1.0
        dynamic_risk_threshold = 0.80 - (0.15 * exposure_factor)    # 0.65 – 0.80

        # -------------------------------------------------------
        # Build XAI driver list — What caused this outcome?
        # -------------------------------------------------------
        drivers = []
        time_cost   = row.get("time_cost", 0)
        future_cost = row.get("future_cost", 0)
        delay       = row.get("predicted_delay", 0)
        profit      = max(row.get("contribution_profit", 1), 1)

        if time_cost > (profit * 0.35):
            drivers.append(f"Capital opportunity cost burn: ${round(time_cost, 2)}")
        if future_cost > (profit * 0.25):
            drivers.append(f"Projected customer churn cost: ${round(future_cost, 2)}")
        if delay > 4.0:
            drivers.append(f"Delay infraction: {round(delay, 1)} days over SLA tolerance")
        if risk_prob > dynamic_risk_threshold:
            drivers.append(f"Risk probability {round(risk_prob*100, 1)}% exceeds {round(dynamic_risk_threshold*100, 1)}% exposure-adjusted threshold")

        # -------------------------------------------------------
        # 5-Tier Decision Taxonomy
        # -------------------------------------------------------
        if revm_pct < self.SEVERE_LOSS_PCT:
            action = "CANCEL / DO NOT SHIP"
            reason = f"Terminal capital destruction: ReVM is {round(revm_pct*100, 1)}% of order value"
            drivers.append("Severe structural loss — shipment will destroy, not generate, margin")

        elif revm_pct < self.MODERATE_LOSS_PCT:
            action = "INTERVENE IMMEDIATELY"
            reason = f"Significant ReVM erosion: {round(revm_pct*100, 1)}% of order value lost"
            drivers.append("Active financial damage — route revision or SLA negotiation required now")

        elif revm_pct < self.MINOR_LOSS_PCT or risk_prob > dynamic_risk_threshold:
            action = "ESCALATE TO MANAGEMENT"
            reason = f"Marginal ReVM or elevated risk ({round(risk_prob*100, 1)}%) requires C-suite visibility"
            drivers.append("Approaching loss threshold — pre-emptive executive review warranted")

        elif delay > 3.0 or risk_prob > (dynamic_risk_threshold * 0.80):
            action = "MONITOR CLOSELY"
            reason = "Sub-threshold risk with active operational warning signals"
            drivers.append("Borderline — flag for operations team daily review")

        else:
            action = "APPROVE EXECUTION"
            reason = "Structurally positive ReVM yield — shipment is financially sound"

        if not drivers:
            drivers.append("Standard optimal operational matrices — no anomalies detected")

        # Confidence decays slightly for negative outcomes (model uncertainty increases)
        adjusted_confidence = round(confidence * (0.88 if revm < 0 else 0.98), 2)

        return {
            "action":     action,
            "reason":     reason,
            "drivers":    drivers,
            "confidence": adjusted_confidence,
            "revm_pct":   round(revm_pct * 100, 2),   # Surface magnitude for UI
            "tier":       self._severity_tier(revm_pct, risk_prob, dynamic_risk_threshold)
        }

    def _severity_tier(self, revm_pct, risk_prob, threshold):
        """Returns a numeric tier (1–5) for UI colour-coding and sorting."""
        if revm_pct < self.SEVERE_LOSS_PCT:
            return 5   # 🔴 Critical
        if revm_pct < self.MODERATE_LOSS_PCT:
            return 4   # 🟠 High
        if revm_pct < self.MINOR_LOSS_PCT or risk_prob > threshold:
            return 3   # 🟡 Medium
        if risk_prob > threshold * 0.80:
            return 2   # 🔵 Low-Medium
        return 1       # 🟢 Nominal
