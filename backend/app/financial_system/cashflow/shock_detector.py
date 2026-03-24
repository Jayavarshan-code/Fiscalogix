class ShockDetector:
    def detect(self, timeline, liquidity_threshold=10000.0):
        """
        Scans the timeline for critical cashflow stress events using deficit, duration, and velocity modeling.
        """
        shocks = []
        prev_cash = None
        
        # Track continuous deficit duration
        deficit_streak = 0
        
        for day in timeline:
            cash = day["cumulative_cash"]
            velocity = 0.0
            
            if prev_cash is not None:
                velocity = prev_cash - cash
                
            if cash < 0:
                deficit_streak += 1
                # Severity Score = f(deficit_value, duration, velocity_drawdown)
                severity_score = (abs(cash) / 1000.0) * deficit_streak * (1.0 + max(0, velocity)/1000.0)
                shocks.append({
                    "date": day["date"].isoformat(),
                    "type": "CASH_DEFICIT",
                    "severity": round(abs(cash), 2),
                    "duration_days": deficit_streak,
                    "velocity": round(velocity, 2),
                    "severity_score": round(severity_score, 2)
                })
            else:
                deficit_streak = 0
                if cash < liquidity_threshold:
                    shocks.append({
                        "date": day["date"].isoformat(),
                        "type": "LOW_LIQUIDITY",
                        "severity": round(liquidity_threshold - cash, 2),
                        "duration_days": 1,
                        "velocity": round(velocity, 2),
                        "severity_score": round((liquidity_threshold - cash)/1000.0, 2)
                    })
                
            if prev_cash is not None and velocity > 15000: 
                shocks.append({
                    "date": day["date"].isoformat(),
                    "type": "SUDDEN_DROP",
                    "severity": round(velocity, 2),
                    "duration_days": 1,
                    "velocity": round(velocity, 2),
                    "severity_score": round(velocity / 1000.0 * 2.0, 2) # sudden drops act as 2x multiplier
                })
                    
            prev_cash = cash
            
        return shocks
