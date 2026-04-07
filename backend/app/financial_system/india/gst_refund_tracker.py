"""
GSTRefundTracker — working capital cost of pending GST refunds and ITC locks.

THIS IS THE INDIA WEDGE FEATURE.

The pain point in plain English:
  Indian exporters and importers have money sitting in the GST system
  that legally belongs to them — but they can't use it. Every day it
  sits there costs them real money at their cost of capital.

  CFO conversation starter:
  "Your GST refund of ₹18L has been pending 52 days.
   At your WACC of 11%, that's costing you ₹28,500 today.
   Next quarter at this claim volume, it's ₹3.4L per year — invisible."

  No ERP, no TMS, no visibility tool shows this number. Fiscalogix does.

Three tracked items:
  1. EXPORT GST REFUND:   IGST paid on exports awaiting GSTN refund
  2. ITC LOCK (IMPORT):   IGST paid on imports awaiting GSTR-2B reflection
  3. DUTY DRAWBACK:       DGFT drawback claim awaiting disbursement

Each item has a claim amount, an age in days, and a working capital cost
computed as: amount × WACC × (age / 365).

The aggregate "GST Working Capital Burn" is the number that goes on the
CFO's dashboard and in the audit report.
"""

from __future__ import annotations

import datetime
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PendingGSTClaim:
    """Represents a single pending GST/drawback claim."""

    CLAIM_TYPES = {
        "export_refund":   "Export IGST Refund (RFD-01)",
        "itc_import":      "Import ITC (GSTR-2B Pending)",
        "drawback_dgft":   "DGFT Duty Drawback",
    }

    def __init__(
        self,
        claim_id:     str,
        claim_type:   str,     # export_refund | itc_import | drawback_dgft
        amount_inr:   float,
        filed_date:   datetime.date,
        shipment_id:  Optional[str] = None,
        hs_code:      Optional[str] = None,
        gstin:        Optional[str] = None,
    ):
        if claim_type not in self.CLAIM_TYPES:
            raise ValueError(f"Unknown claim_type: {claim_type}")

        self.claim_id    = claim_id
        self.claim_type  = claim_type
        self.amount_inr  = amount_inr
        self.filed_date  = filed_date
        self.shipment_id = shipment_id
        self.hs_code     = hs_code
        self.gstin       = gstin

    @property
    def age_days(self) -> int:
        return (datetime.date.today() - self.filed_date).days

    def working_capital_cost(self, wacc: float = 0.11) -> float:
        """Daily cost of capital tied up in this claim."""
        return self.amount_inr * wacc * (self.age_days / 365.0)

    def to_dict(self, wacc: float = 0.11) -> dict:
        wcc = self.working_capital_cost(wacc)
        return {
            "claim_id":              self.claim_id,
            "claim_type":            self.claim_type,
            "claim_type_label":      self.CLAIM_TYPES[self.claim_type],
            "amount_inr":            round(self.amount_inr, 2),
            "filed_date":            self.filed_date.isoformat(),
            "age_days":              self.age_days,
            "working_capital_cost":  round(wcc, 2),
            "daily_burn_inr":        round(self.amount_inr * wacc / 365.0, 2),
            "shipment_id":           self.shipment_id,
            "hs_code":               self.hs_code,
            "status":                self._status_from_age(),
        }

    def _status_from_age(self) -> str:
        """
        SLA-based status classification.
        GSTN committed SLA: 60 days for RFD-01 auto-refund.
        DGFT drawback: 30 days from LEO date (Let Export Order).
        """
        if self.claim_type == "export_refund":
            if self.age_days < 30:   return "in_progress"
            if self.age_days < 60:   return "delayed"
            return "stuck"
        elif self.claim_type == "drawback_dgft":
            if self.age_days < 30:   return "in_progress"
            if self.age_days < 60:   return "delayed"
            return "stuck"
        else:  # itc_import
            if self.age_days < 45:   return "in_progress"
            return "delayed"


class GSTRefundTracker:
    """
    Aggregates all pending GST/drawback claims for a tenant and computes
    the total working capital burn.

    In production:
      - Claims are seeded from the shipment records + GST portal API
      - Celery task refreshes claim status every 24 hours
      - Redis caches the aggregate burn number for the dashboard KPI

    For now: accepts a list of PendingGSTClaim objects and computes on demand.
    The /india/gst-refund-tracker endpoint creates claims from shipment data.
    """

    def __init__(self, claims: Optional[List[PendingGSTClaim]] = None):
        self._claims: List[PendingGSTClaim] = claims or []

    def add_claim(self, claim: PendingGSTClaim):
        self._claims.append(claim)

    def summary(self, wacc: float = 0.11) -> dict:
        """
        Aggregate view — the CFO dashboard number.

        Returns:
          total_locked_inr:         Total amount locked in pending claims
          total_working_capital_burn: Cost of capital on all pending claims (today)
          annual_burn_inr:          Projected annual cost if claims stay pending
          daily_burn_inr:           Daily cost of capital across all claims
          by_type:                  Breakdown per claim type
          stuck_claims:             Claims past SLA — need escalation
          claims:                   Full per-claim detail
        """
        if not self._claims:
            return {
                "total_locked_inr":           0.0,
                "total_working_capital_burn":  0.0,
                "annual_burn_inr":             0.0,
                "daily_burn_inr":              0.0,
                "by_type":                     {},
                "stuck_claims":                [],
                "claims":                      [],
                "message": "No pending GST/drawback claims found.",
            }

        claim_dicts = [c.to_dict(wacc) for c in self._claims]

        total_locked   = sum(c["amount_inr"]            for c in claim_dicts)
        total_burn     = sum(c["working_capital_cost"]   for c in claim_dicts)
        daily_burn     = sum(c["daily_burn_inr"]         for c in claim_dicts)
        annual_burn    = daily_burn * 365

        # Group by claim type
        by_type: Dict[str, dict] = {}
        for c in claim_dicts:
            t = c["claim_type"]
            if t not in by_type:
                by_type[t] = {
                    "label":           c["claim_type_label"],
                    "count":           0,
                    "locked_inr":      0.0,
                    "burn_inr":        0.0,
                }
            by_type[t]["count"]      += 1
            by_type[t]["locked_inr"] += c["amount_inr"]
            by_type[t]["burn_inr"]   += c["working_capital_cost"]

        stuck = [c for c in claim_dicts if c["status"] == "stuck"]

        return {
            "total_locked_inr":           round(total_locked, 2),
            "total_working_capital_burn":  round(total_burn, 2),
            "annual_burn_inr":             round(annual_burn, 2),
            "daily_burn_inr":              round(daily_burn, 2),
            "by_type":                     by_type,
            "stuck_claims":                stuck,
            "stuck_count":                 len(stuck),
            "claims":                      claim_dicts,
        }

    @classmethod
    def from_shipment_records(
        cls,
        shipments: List[dict],
        wacc: float = 0.11,
    ) -> "GSTRefundTracker":
        """
        Build a tracker from raw shipment records.

        Reads these fields from each shipment row:
          shipment_id, hs_code, order_value, route, gst_refund_mode,
          gst_refund_filed_date (ISO date string), igst_paid (optional),
          drawback_filed_date (ISO date string, optional)

        If gst_refund_filed_date is missing, the shipment arrival date is used
        as a conservative proxy.
        """
        from app.financial_system.india.gst_compliance import (
            GSTComplianceModel,
            GST_RATE_BY_HS_CHAPTER,
            _DEFAULT_GST_RATE,
            DGFT_DRAWBACK_AIR,
            _DEFAULT_DRAWBACK_RATE,
        )

        model    = GSTComplianceModel()
        tracker  = cls()
        today    = datetime.date.today()

        for s in shipments:
            shipment_id  = str(s.get("shipment_id", s.get("id", "UNKNOWN")))
            hs_code      = str(s.get("hs_code", "")).strip()
            order_value  = float(s.get("order_value", 0.0))
            route        = str(s.get("route", "LOCAL")).upper().strip()
            refund_mode  = str(s.get("gst_refund_mode", "auto")).lower()

            if order_value <= 0:
                continue

            # ── Export GST refund claim ───────────────────────────────────────
            if model._is_india_export(route) and refund_mode != "lut":
                gst_rate  = model._resolve_gst_rate(hs_code)
                igst_paid = float(s.get("igst_paid", order_value * gst_rate))

                if igst_paid > 0:
                    filed_date_str = s.get("gst_refund_filed_date", "")
                    filed_date = (
                        datetime.date.fromisoformat(filed_date_str)
                        if filed_date_str
                        else today - datetime.timedelta(days=int(s.get("credit_days", 30)))
                    )
                    tracker.add_claim(PendingGSTClaim(
                        claim_id    = f"{shipment_id}-GST-EXPORT",
                        claim_type  = "export_refund",
                        amount_inr  = igst_paid,
                        filed_date  = filed_date,
                        shipment_id = shipment_id,
                        hs_code     = hs_code,
                    ))

            # ── Import ITC claim ──────────────────────────────────────────────
            elif model._is_india_import(route):
                gst_rate       = model._resolve_gst_rate(hs_code)
                bcd_rate       = model._resolve_bcd_rate(hs_code)
                bcd_cost       = order_value * bcd_rate
                igst_on_import = (order_value + bcd_cost) * gst_rate

                if igst_on_import > 0:
                    filed_date_str = s.get("import_date", "")
                    filed_date = (
                        datetime.date.fromisoformat(filed_date_str)
                        if filed_date_str
                        else today - datetime.timedelta(days=30)
                    )
                    tracker.add_claim(PendingGSTClaim(
                        claim_id    = f"{shipment_id}-ITC-IMPORT",
                        claim_type  = "itc_import",
                        amount_inr  = igst_on_import,
                        filed_date  = filed_date,
                        shipment_id = shipment_id,
                        hs_code     = hs_code,
                    ))

            # ── DGFT drawback claim (all exports, regardless of GST mode) ─────
            if model._is_india_export(route):
                drawback_rate  = model._resolve_drawback_rate(hs_code)
                drawback_amount = order_value * drawback_rate

                if drawback_amount > 0:
                    drawback_date_str = s.get("drawback_filed_date", "")
                    drawback_date = (
                        datetime.date.fromisoformat(drawback_date_str)
                        if drawback_date_str
                        else today - datetime.timedelta(days=20)
                    )
                    tracker.add_claim(PendingGSTClaim(
                        claim_id    = f"{shipment_id}-DGFT-DRAWBACK",
                        claim_type  = "drawback_dgft",
                        amount_inr  = drawback_amount,
                        filed_date  = drawback_date,
                        shipment_id = shipment_id,
                        hs_code     = hs_code,
                    ))

        return tracker
