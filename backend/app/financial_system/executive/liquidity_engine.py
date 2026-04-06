import statistics

class LiquidityScoreEngine:
    def compute(self, current_cash, timeline, shocks, enriched_records):
        """
        Produces a global Executive Liquidity Score (0-100) representing true corporate financial health.
        """
        if not enriched_records or not timeline:
            return 0
            
        # 1. Cash Health (Raw Cash vs Short-term Hard Obligations)
        total_outflows = sum(r.get("total_cost", 0) for r in enriched_records)
        cash_health = min(1.0, current_cash / total_outflows) if total_outflows > 0 else 1.0
        
        # 2. Shock Severity (Inverse relationship scaling to massive multi-day shocks)
        # P2-E FIX: use .get() — some shock sources only emit "severity"; "severity_score"
        # is preferred (already normalised) but fall back gracefully to avoid KeyError.
        #
        # P3-6 FIX: original denominator 10.0 was an absolute constant that didn't scale.
        # WHAT WAS WRONG: severity_score = (|cash|/1K) × streak × velocity_ratio.
        # A $50K deficit on day 3 with moderate velocity produces severity_score ≈ 900.
        # total_severity / 10 = 90 → shock_health = max(0, -89) = 0.0.
        # For any real portfolio, shock_health was permanently 0.0 regardless of severity —
        # making it useless as a differentiating signal in the liquidity score.
        # FIX: normalize denominator by portfolio size (# records) so the scale is
        # relative to the number of shipments being tracked, not an absolute dollar figure.
        # Use max(1, n_records) to avoid div/0 on empty portfolios.
        n_records = max(1, len(enriched_records))
        total_severity = sum(s.get("severity_score", s.get("severity", 0)) for s in shocks)
        shock_health = max(0.0, 1.0 - (total_severity / (10.0 * n_records)))
        
        # 3. REVM Health (Strict Ratio of positive value-accreting movements)
        positive_revms = sum(1 for r in enriched_records if r["revm"] > 0)
        revm_health = positive_revms / len(enriched_records)
        
        # 4. Stability (Statistical Volatility / Variance isolated within the Time-Series Cash Timeline)
        daily_nets = [t["daily_net"] for t in timeline]
        if len(daily_nets) > 1:
            stdev = statistics.stdev(daily_nets)
            mean_net = abs(statistics.mean(daily_nets)) or 1.0
            # Coefficient of variation (CV) historically used as inverse financial stability indicator
            cv = stdev / mean_net 
            stability = max(0.0, 1.0 - (cv * 0.1))
        else:
            stability = 0.9 # Default stability 
            
        # Global Multivariate Weighting Formula matching Executive expectations
        liquidity_score = (
            (0.35 * cash_health) + 
            (0.25 * shock_health) + 
            (0.30 * revm_health) + 
            (0.10 * stability)
        ) * 100.0
        
        return round(liquidity_score)
