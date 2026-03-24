from collections import defaultdict
from datetime import timedelta

class TimelineBuilder:
    def build(self, events, starting_cash=50000.0):
        """
        Arranges all cash events on a linear timeline to compute Cumulative Cash Balances and Rolling Stress Windows.
        """
        daily_flows = defaultdict(float)
        
        for e in events:
            if e["event_type"] == "INFLOW":
                daily_flows[e["event_date"]] += e["amount"]
            else:
                daily_flows[e["event_date"]] -= e["amount"]
                
        sorted_dates = sorted(daily_flows.keys())
        
        timeline = []
        current_cash = starting_cash
        
        peak_deficit = 0.0
        deficit_days = 0
        
        for d in sorted_dates:
            net = daily_flows[d]
            current_cash += net
            
            # Sub-calculations for 7-day and 30-day rolling windows
            rolling_7d = sum(daily_flows[past_d] for past_d in sorted_dates if d - timedelta(days=7) <= past_d <= d)
            rolling_30d = sum(daily_flows[past_d] for past_d in sorted_dates if d - timedelta(days=30) <= past_d <= d)
            
            if current_cash < 0:
                peak_deficit = min(peak_deficit, current_cash)
                deficit_days += 1
                
            timeline.append({
                "date": d,
                "daily_net": round(net, 2),
                "cumulative_cash": round(current_cash, 2),
                "rolling_7d_net": round(rolling_7d, 2),
                "rolling_30d_net": round(rolling_30d, 2)
            })
            
        metrics = {
            "peak_deficit": round(abs(peak_deficit), 2),
            "deficit_duration_days": deficit_days
        }
            
        return timeline, metrics
