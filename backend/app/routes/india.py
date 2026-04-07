"""
India-specific financial intelligence endpoints.

These endpoints expose the India compliance layer — GST, duty drawback,
and working capital cost of tax refund lags — that has no equivalent
in the main financial pipeline (which was built for US/EU importers).

Endpoints:
  POST /india/gst-cost           — per-shipment GST impact (export or import)
  POST /india/gst-refund-tracker — portfolio-level GST working capital burn
  GET  /india/routes             — available Indian trade corridors + rates

These are the DEMO WEDGE endpoints. For a CFO audit report, call:
  1. /india/gst-refund-tracker  with last 3 months of shipment data
  2. Show "total_working_capital_burn" as the headline number

That number — the invisible GST working capital cost — is what no
other platform currently surfaces for Indian exporters.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.financial_system.auth import get_current_user

router = APIRouter(prefix="/india", tags=["India GST Compliance"])


# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ShipmentGSTRequest(BaseModel):
    shipment_id:       str
    route:             str            # e.g. "IN-US", "EU-IN", "IN-EU"
    order_value:       float
    hs_code:           Optional[str]  = ""
    wacc:              float          = 0.11
    gst_refund_mode:   str            = "auto"   # lut | auto | manual | stuck


class GSTRefundClaimInput(BaseModel):
    shipment_id:             str
    route:                   str
    order_value:             float
    hs_code:                 Optional[str]  = ""
    gst_refund_mode:         str            = "auto"
    igst_paid:               Optional[float] = None
    gst_refund_filed_date:   Optional[str]  = None   # ISO date "2026-02-14"
    import_date:             Optional[str]  = None
    drawback_filed_date:     Optional[str]  = None
    credit_days:             int            = 30


class GSTRefundPortfolioRequest(BaseModel):
    shipments: List[GSTRefundClaimInput]
    wacc:      float = 0.11
    tenant_id: str   = "default_tenant"


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/gst-cost")
def compute_gst_cost(
    shipments: List[ShipmentGSTRequest],
    _current_user: dict = Depends(get_current_user),
):
    """
    Computes per-shipment GST and customs cost impact for Indian trade routes.

    For EXPORT routes (IN-XX):
      Returns GST working capital cost of refund lag + DGFT drawback benefit.
      The net impact is what gets deducted from ReVM.

    For IMPORT routes (XX-IN):
      Returns Basic Customs Duty (sunk cost) + IGST ITC working capital cost.

    Key output fields:
      net_gst_impact             — amount to deduct from ReVM (export)
      total_india_customs_cost   — amount to deduct from ReVM (import)
      drawback_receivable        — positive cash flow receivable from DGFT
      gst_working_capital_cost   — cost of refund lag at your WACC
    """
    from app.financial_system.india.gst_compliance import GSTComplianceModel
    model = GSTComplianceModel()

    results = []
    for s in shipments:
        row = s.model_dump()
        route = s.route.upper().strip()

        if model._is_india_export(route):
            detail = model.compute_export(row)
            results.append({
                "shipment_id":  s.shipment_id,
                "direction":    "export",
                "route":        route,
                **detail,
            })
        elif model._is_india_import(route):
            detail = model.compute_import(row)
            results.append({
                "shipment_id":  s.shipment_id,
                "direction":    "import",
                "route":        route,
                **detail,
            })
        else:
            results.append({
                "shipment_id":   s.shipment_id,
                "direction":     "domestic",
                "route":         route,
                "net_gst_impact": 0.0,
                "message":       "Domestic route — no GST/customs cost.",
            })

    return results


@router.post("/gst-refund-tracker")
def track_gst_refunds(
    payload: GSTRefundPortfolioRequest,
    _current_user: dict = Depends(get_current_user),
):
    """
    Portfolio-level GST working capital burn tracker.

    THE DEMO WEDGE ENDPOINT.

    Takes a list of shipments and returns:
      total_locked_inr:          Total GST/drawback amount pending with government
      total_working_capital_burn: What that locked amount is costing today
      annual_burn_inr:            Projected annual cost if nothing is recovered
      daily_burn_inr:             Cost per day
      stuck_claims:               Claims past SLA — need CA/GSTN escalation

    CFO audit report headline:
      "Your ₹X locked in pending GST claims is costing you ₹Y/day.
       ₹Z of that is stuck past the 60-day GSTN SLA."

    Input: same shipment CSV format used elsewhere in Fiscalogix.
    If gst_refund_filed_date is missing, uses credit_days as a proxy.
    """
    from app.financial_system.india.gst_refund_tracker import GSTRefundTracker

    shipment_dicts = [s.model_dump() for s in payload.shipments]
    tracker = GSTRefundTracker.from_shipment_records(
        shipments=shipment_dicts,
        wacc=payload.wacc,
    )

    summary = tracker.summary(wacc=payload.wacc)
    summary["tenant_id"] = payload.tenant_id
    summary["wacc_used"]  = payload.wacc

    return summary


@router.get("/routes")
def get_india_routes(
    _current_user: dict = Depends(get_current_user),
):
    """
    Returns all supported Indian trade corridors with applicable rates.

    Shows:
      - Import duty rate at destination
      - GST treatment (zero-rated for exports under GST law)
      - Applicable FTA/trade agreement
      - Whether DGFT drawback applies
    """
    from app.financial_system.tariff_model import ROUTE_TARIFF_RATES

    india_corridors = {
        # Export corridors
        "IN-US": {
            "direction":     "export",
            "destination":   "United States",
            "import_duty":   ROUTE_TARIFF_RATES.get("IN-US", 0.03),
            "gst_treatment": "zero_rated",
            "fta":           "GSP partially suspended — MFN applies for most goods",
            "dgft_drawback": True,
            "notes":         "US Section 301 tariffs on Chinese goods create opportunity for Indian substitution",
        },
        "IN-EU": {
            "direction":     "export",
            "destination":   "European Union",
            "import_duty":   ROUTE_TARIFF_RATES.get("IN-EU", 0.038),
            "gst_treatment": "zero_rated",
            "fta":           "India-EU FTA under negotiation (2024–26)",
            "dgft_drawback": True,
            "notes":         "EU Carbon Border Adjustment Mechanism (CBAM) applies from 2026 for steel, aluminium",
        },
        "IN-AE": {
            "direction":     "export",
            "destination":   "UAE",
            "import_duty":   ROUTE_TARIFF_RATES.get("IN-AE", 0.05),
            "gst_treatment": "zero_rated",
            "fta":           "India-UAE CEPA (effective May 2022) — preferential rates on 90% of goods",
            "dgft_drawback": True,
            "notes":         "Fastest growing corridor for Indian pharma and engineering exports",
        },
        "IN-SG": {
            "direction":     "export",
            "destination":   "Singapore",
            "import_duty":   ROUTE_TARIFF_RATES.get("IN-SG", 0.00),
            "gst_treatment": "zero_rated",
            "fta":           "India-Singapore CECA — zero duty on most goods",
            "dgft_drawback": True,
            "notes":         "Gateway to ASEAN markets; Singapore acts as re-export hub",
        },
        "IN-UK": {
            "direction":     "export",
            "destination":   "United Kingdom",
            "import_duty":   ROUTE_TARIFF_RATES.get("IN-UK", 0.04),
            "gst_treatment": "zero_rated",
            "fta":           "India-UK FTA in negotiation — interim preferential rate applies",
            "dgft_drawback": True,
            "notes":         "Strong demand for Indian textiles, pharma, IT services post-Brexit",
        },
        # Import corridors
        "CN-IN": {
            "direction":     "import",
            "origin":        "China",
            "bcd_rate":      ROUTE_TARIFF_RATES.get("CN-IN", 0.10),
            "gst_treatment": "igst_levied_at_customs",
            "fta":           "No FTA — elevated BCD + potential anti-dumping duties",
            "itc_recoverable": True,
            "notes":         "Anti-dumping duties on 200+ categories; check DGTR notifications",
        },
        "EU-IN": {
            "direction":     "import",
            "origin":        "European Union",
            "bcd_rate":      ROUTE_TARIFF_RATES.get("EU-IN", 0.075),
            "gst_treatment": "igst_levied_at_customs",
            "fta":           "India-EU FTA under negotiation",
            "itc_recoverable": True,
            "notes":         "Capital goods imports eligible for EPCG scheme (reduced BCD)",
        },
        "US-IN": {
            "direction":     "import",
            "origin":        "United States",
            "bcd_rate":      ROUTE_TARIFF_RATES.get("US-IN", 0.075),
            "gst_treatment": "igst_levied_at_customs",
            "fta":           "No FTA",
            "itc_recoverable": True,
            "notes":         "Technology imports — EPCG and advance authorization schemes available",
        },
    }

    return {
        "corridors":    india_corridors,
        "gst_note":     "All Indian exports are zero-rated under GST. IGST paid on exports is refundable. Exporters registered under LUT avoid upfront IGST payment entirely.",
        "drawback_note": "DGFT All Industry Rate (AIR) drawback applies to all eligible exports. Rates updated annually in July. Claim within 3 years of export date.",
        "wacc_note":    "Working capital cost computations use your tenant WACC. Override via POST /admin/wacc.",
    }
