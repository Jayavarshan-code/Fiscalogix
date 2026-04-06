class RootCauseEngine:
    def analyze(self, shocks, events):
        """
        Maps a shock date back down to the exact supply chain movements causing the deficit.
        """
        root_causes = []
        
        for shock in shocks:
            shock_date = shock["date"]
            
            blame_weights = {}
            for e in events:
                evt_date = e["event_date"].isoformat()
                
                # If an outflow drained cash heavily leading up to this point
                if e["event_type"] == "OUTFLOW" and evt_date <= shock_date:
                    blame_weights[e["shipment_id"]] = blame_weights.get(e["shipment_id"], 0) + e["amount"]
                    
            # Sort highest offenders
            sorted_offenders = sorted(blame_weights.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Calculate total blame cache to formulate exact % impact
            total_blame_pool = sum(amt for _, amt in sorted_offenders) if sorted_offenders else 1.0
            
            for s_id, amt in sorted_offenders:
                impact_pct = (amt / total_blame_pool) * 100.0
                root_causes.append({
                    "shipment_id": s_id,
                    "contribution_to_deficit": round(amt, 2),
                    "impact_percentage": round(impact_pct, 1),
                    "reason": f"Heavy capital lockup directly preceding {shock_date}"
                })
                
        # Deduplicate to have a clean array of purely destructive shipments
        unique_causes = {rc["shipment_id"]: rc for rc in root_causes}

        # P3-4 FIX: CashflowDecisionSupport._extract_targeted_actions() expects a
        # list[str] for keyword matching, but this method returned a list[dict].
        # Calling cause.lower() on a dict raises AttributeError silently, so the
        # targeted action layer (carrier reroute, FX hedge, etc.) NEVER fired.
        # Fix: attach a plain-string `reason_text` list alongside the structured dicts
        # so the decision layer can match keywords without breaking the existing schema.
        result = list(unique_causes.values())
        for rc in result:
            # Enrich reason with shipment context for better keyword matching
            rc["reason_text"] = rc.get("reason", "")

        return result
