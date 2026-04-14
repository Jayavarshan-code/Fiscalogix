"""
ConcentrationEngine — client and port concentration risk analysis.

Two analyses in one pass over enriched_records:

1. CLIENT CONCENTRATION
   Flags when a single client drives a dangerous share of revenue.
   Threshold: any client > 30% of total revenue triggers a WARNING.
               any client > 50%                triggers a CRITICAL alert.

2. PORT CONCENTRATION
   Flags when a high share of shipments flows through a single port.
   A port disruption (congestion, strike, cyclone) then hits the entire book.
   Threshold: any port > 50% of shipment volume triggers a WARNING.
               any port > 70%                    triggers a CRITICAL alert.

Both analyses produce:
  - Ranked breakdown (client/port → share %)
  - Scenario impact: "if this client delays 30 days, cash drops by X"
  - Plain-English recommendation
"""

from typing import Any, Dict, List


class ConcentrationEngine:

    # Client revenue share thresholds
    CLIENT_WARN     = 0.30   # 30 % → warning
    CLIENT_CRITICAL = 0.50   # 50 % → critical

    # Port shipment volume share thresholds
    PORT_WARN     = 0.50   # 50 % → warning
    PORT_CRITICAL = 0.70   # 70 % → critical

    def compute(self, enriched_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not enriched_records:
            return {
                "client_concentration": {"status": "ok", "breakdown": [], "alerts": []},
                "port_concentration":   {"status": "ok", "breakdown": [], "alerts": []},
            }

        return {
            "client_concentration": self._client_concentration(enriched_records),
            "port_concentration":   self._port_concentration(enriched_records),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Client concentration
    # ──────────────────────────────────────────────────────────────────────────

    def _client_concentration(
        self, records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        total_revenue = sum(r.get("order_value", 0) for r in records) or 1.0

        # Aggregate revenue per client
        client_rev: Dict[str, float] = {}
        client_credit: Dict[str, int] = {}   # track credit days per client for scenario
        for r in records:
            name = (
                r.get("client_name")
                or r.get("customer_name")
                or r.get("customer_id")
                or "Unknown"
            )
            name = str(name)
            client_rev[name]    = client_rev.get(name, 0.0) + float(r.get("order_value", 0))
            client_credit[name] = max(
                client_credit.get(name, 0), int(r.get("credit_days", 30))
            )

        breakdown = sorted(
            [
                {
                    "client":         name,
                    "revenue":        round(rev, 2),
                    "share_pct":      round(rev / total_revenue * 100, 1),
                    "credit_days":    client_credit.get(name, 30),
                    # Scenario: if this client delays 30 days beyond their terms,
                    # how much additional cash is locked up?
                    "delay_30d_impact": round(rev * 0.085 * 30 / 365, 2),
                }
                for name, rev in client_rev.items()
            ],
            key=lambda x: x["revenue"],
            reverse=True,
        )

        alerts = []
        status = "ok"
        for entry in breakdown:
            share = entry["share_pct"] / 100
            if share >= self.CLIENT_CRITICAL:
                status = "critical"
                alerts.append({
                    "severity": "critical",
                    "client":   entry["client"],
                    "message": (
                        f"{entry['client']} represents {entry['share_pct']}% of your revenue. "
                        f"A 30-day payment delay from them locks up an extra "
                        f"{_fmt(entry['delay_30d_impact'])} in working capital. "
                        f"Diversify: no single client should exceed 30% of revenue."
                    ),
                })
            elif share >= self.CLIENT_WARN:
                if status != "critical":
                    status = "warning"
                alerts.append({
                    "severity": "warning",
                    "client":   entry["client"],
                    "message": (
                        f"{entry['client']} is {entry['share_pct']}% of revenue — "
                        f"above the 30% safe concentration limit. "
                        f"Start building 2-3 additional accounts in this segment."
                    ),
                })

        return {
            "status":    status,
            "breakdown": breakdown[:10],   # top 10 clients
            "alerts":    alerts,
            "top_client_share_pct": breakdown[0]["share_pct"] if breakdown else 0,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Port concentration
    # ──────────────────────────────────────────────────────────────────────────

    def _port_concentration(
        self, records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        total_shipments = len(records) or 1

        # Count shipments per origin/destination port
        port_counts: Dict[str, int] = {}
        port_value:  Dict[str, float] = {}

        for r in records:
            for field in ("origin_node", "destination_node"):
                port = str(r.get(field) or "Unknown").strip()
                if port and port != "Unknown":
                    port_counts[port] = port_counts.get(port, 0) + 1
                    port_value[port]  = port_value.get(port, 0.0) + float(r.get("order_value", 0))

        breakdown = sorted(
            [
                {
                    "port":          port,
                    "shipment_count": count,
                    "share_pct":     round(count / total_shipments * 100, 1),
                    "total_value":   round(port_value.get(port, 0), 2),
                    # Scenario: 3-day port disruption cost (delay cost proxy)
                    "disruption_3d_cost": round(
                        port_value.get(port, 0) * 0.085 * 3 / 365, 2
                    ),
                }
                for port, count in port_counts.items()
            ],
            key=lambda x: x["shipment_count"],
            reverse=True,
        )

        alerts = []
        status = "ok"
        for entry in breakdown:
            share = entry["share_pct"] / 100
            if share >= self.PORT_CRITICAL:
                status = "critical"
                alerts.append({
                    "severity": "critical",
                    "port":     entry["port"],
                    "message": (
                        f"{entry['port']} handles {entry['share_pct']}% of your shipment volume "
                        f"({_fmt(entry['total_value'])} in freight value). "
                        f"A 3-day disruption here would cost ~{_fmt(entry['disruption_3d_cost'])}. "
                        f"Establish backup routing through an alternate port immediately."
                    ),
                })
            elif share >= self.PORT_WARN:
                if status != "critical":
                    status = "warning"
                alerts.append({
                    "severity": "warning",
                    "port":     entry["port"],
                    "message": (
                        f"{entry['port']} is {entry['share_pct']}% of your volume. "
                        f"Identify and pre-qualify a secondary port to reduce disruption exposure."
                    ),
                })

        return {
            "status":    status,
            "breakdown": breakdown[:10],
            "alerts":    alerts,
            "top_port_share_pct": breakdown[0]["share_pct"] if breakdown else 0,
        }


def _fmt(amount: float) -> str:
    if amount >= 10_000_000:
        return f"₹{amount / 10_000_000:.1f}Cr"
    if amount >= 100_000:
        return f"₹{amount / 100_000:.1f}L"
    return f"₹{amount:,.0f}"
