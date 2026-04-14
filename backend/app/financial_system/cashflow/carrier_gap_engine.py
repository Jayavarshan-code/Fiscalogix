"""
CarrierGapEngine — working capital gap between carrier payments and client collections.

The #1 cash crisis pattern in small/mid freight companies:

  Day 0:   Shipment booked.
  Day 7:   You pay the carrier (Maersk, MSC, airline).   ← OUTFLOW
  Day 35:  Goods delivered (7-day transit + delays).
  Day 65:  Client pays you (Net-30 from delivery).        ← INFLOW

  Gap = 58 days of cash tied up per shipment.
  At ₹10L per shipment × 20 shipments/month = ₹2Cr permanently in the air.

This engine makes that gap visible — per-shipment and portfolio-wide.
"""

from datetime import date, timedelta
from typing import Any, Dict, List


class CarrierGapEngine:
    """
    Computes the working capital gap timeline for a freight portfolio.

    Inputs (from enriched records):
        order_value             — client invoice amount
        shipment_cost / total_cost — what you owe the carrier
        supplier_payment_terms  — days until carrier must be paid (default 7)
        predicted_delay         — expected transit days
        credit_days             — client's payment terms from delivery
        payment_delay_days      — any additional client payment lag observed

    Outputs:
        working_capital_gap     — peak cash tied up simultaneously (negative = tied up)
        gap_days                — average days between carrier payment and client receipt
        peak_gap_date           — date when cash gap is widest
        per_shipment            — individual gap breakdown for top exposed shipments
        recommendation          — plain-English action
    """

    def compute(
        self,
        enriched_records: List[Dict[str, Any]],
        starting_cash: float = 0.0,
    ) -> Dict[str, Any]:
        if not enriched_records:
            return {
                "working_capital_gap": 0.0,
                "gap_days": 0,
                "peak_gap_date": None,
                "per_shipment": [],
                "recommendation": "No shipment data to analyse.",
            }

        today = date.today()
        per_shipment = []
        timeline: Dict[date, float] = {}  # date → cumulative cash position delta

        for row in enriched_records:
            order_val  = float(row.get("order_value", 0) or 0)
            carrier_cost = float(
                row.get("shipment_cost") or row.get("total_cost") or order_val * 0.15
            )

            carrier_terms   = int(row.get("supplier_payment_terms", 7))
            transit_days    = int(row.get("predicted_delay", row.get("delay_days", 14)))
            credit_days     = int(row.get("credit_days", 30))
            payment_lag     = int(row.get("payment_delay_days", 0))

            # When cash leaves (carrier payment due)
            outflow_date = today + timedelta(days=max(1, carrier_terms))
            # When cash arrives (delivery + client payment terms + any observed lag)
            inflow_date  = today + timedelta(days=transit_days + credit_days + payment_lag)

            gap_days_this = max(0, (inflow_date - outflow_date).days)
            gap_amount    = carrier_cost  # cash tied up from outflow until inflow

            per_shipment.append({
                "shipment_id":    row.get("shipment_id", "unknown"),
                "client":         row.get("client_name", row.get("customer_name", "—")),
                "carrier_payment_due": outflow_date.isoformat(),
                "client_payment_expected": inflow_date.isoformat(),
                "gap_days":       gap_days_this,
                "cash_tied_up":   round(gap_amount, 2),
                "order_value":    round(order_val, 2),
            })

            # Build cash position timeline
            for d, amt in [(outflow_date, -carrier_cost), (inflow_date, order_val)]:
                timeline[d] = timeline.get(d, 0.0) + amt

        # Compute running cash balance to find peak gap
        sorted_dates = sorted(timeline.keys())
        running = starting_cash
        peak_gap   = 0.0
        peak_date  = None
        for d in sorted_dates:
            running += timeline[d]
            if running < peak_gap:
                peak_gap  = running
                peak_date = d

        # Sort per-shipment by cash tied up descending
        per_shipment.sort(key=lambda x: x["cash_tied_up"], reverse=True)

        total_tied = sum(s["cash_tied_up"] for s in per_shipment)
        avg_gap    = (
            round(sum(s["gap_days"] for s in per_shipment) / len(per_shipment))
            if per_shipment else 0
        )

        # Plain-English recommendation
        if avg_gap > 45:
            rec = (
                f"Your average carrier-to-collection gap is {avg_gap} days. "
                f"This locks up {_fmt(total_tied)} in working capital. "
                f"Negotiate Net-15 or Net-30 client payment terms on your top 3 accounts "
                f"to reduce this gap by ~40%."
            )
        elif avg_gap > 20:
            rec = (
                f"Your {avg_gap}-day average gap ties up {_fmt(total_tied)}. "
                f"Consider a supply chain finance facility to bridge carrier payments "
                f"against confirmed receivables."
            )
        else:
            rec = (
                f"Working capital gap is {avg_gap} days — within healthy range. "
                f"Monitor the {len([s for s in per_shipment if s['gap_days'] > 30])} "
                f"shipments with gaps over 30 days."
            )

        return {
            "working_capital_gap":  round(peak_gap, 2),
            "total_cash_tied_up":   round(total_tied, 2),
            "gap_days":             avg_gap,
            "peak_gap_date":        peak_date.isoformat() if peak_date else None,
            "per_shipment":         per_shipment[:10],   # top 10 most exposed
            "recommendation":       rec,
        }


def _fmt(amount: float) -> str:
    """Quick formatting without tenant context — used in engine-level strings."""
    if amount >= 10_000_000:
        return f"₹{amount / 10_000_000:.1f}Cr"
    if amount >= 100_000:
        return f"₹{amount / 100_000:.1f}L"
    return f"₹{amount:,.0f}"
