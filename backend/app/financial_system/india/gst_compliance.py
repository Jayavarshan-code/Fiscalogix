"""
GSTComplianceModel — India-specific GST and customs cost intelligence.

WHY THIS WAS MISSING:
  The existing tariff_model.py covers US Section 301, EU MFN, and RCEP rates.
  It has zero knowledge of Indian tax law. For Indian exporters, this matters:

  1. IGST on IMPORTS (inbound shipments):
     India levies IGST (Integrated GST) on imports at the point of customs clearance.
     Unlike tariff duty, IGST is recoverable as Input Tax Credit (ITC) — but only
     after the goods are sold and GST returns are filed. The lag between paying IGST
     at the port and recovering it as ITC creates a WORKING CAPITAL COST that no
     existing tool quantifies per shipment.

     Example: ₹1Cr pharma API import, IGST @ 12% = ₹12L paid at port.
     ITC recovery takes 45–90 days. At WACC 11%: hidden cost = ₹12L × 11% × (67/365)
     = ₹24,200. Per shipment. Every month. Invisible in the P&L.

  2. GST ON EXPORTS (outbound shipments):
     Exports are ZERO-RATED under GST. Exporters have two paths:
       (a) Export under LUT (Letter of Undertaking) → no upfront GST payment.
           Zero working capital impact. Correct path for registered exporters.
       (b) Pay IGST and claim refund → working capital locked until refund arrives.
           Refund processing: 30–90 days (GSTN auto-refund) or longer for manual.
           This is the hidden cost for exporters who haven't filed their LUT.

  3. INDIAN DUTY DRAWBACK (DGFT All Industry Rate — AIR):
     India's duty drawback scheme reimburses Basic Customs Duty (BCD) paid on
     inputs used in manufactured exports. Published annually by DGFT as
     "All Industry Rate" (AIR) schedules.
     This is DIFFERENT from US CBP drawback — it's a percentage of FOB export value,
     not a refund of specific duty paid. Rates range from 0.5% to 4% of FOB value
     depending on the product category.

  4. BASIC CUSTOMS DUTY (BCD) on imports to India:
     India's import tariff. Separate from IGST. Levied first; IGST levied on
     (CIF value + BCD). BCD is NOT recoverable — it's a sunk cost.

WHAT THIS MODEL COMPUTES:
  For OUTBOUND (Indian export) shipments:
    → gst_working_capital_cost: cost of IGST refund lag (if not under LUT)
    → dgft_drawback_benefit: duty drawback receivable (positive cash flow)
    → net_gst_impact: working capital cost net of drawback

  For INBOUND (import to India) shipments:
    → igst_on_import: IGST paid at customs clearance
    → itc_recovery_days: estimated days to recover ITC
    → itc_working_capital_cost: time cost of ITC recovery lag
    → bcd_cost: Basic Customs Duty (sunk cost, not recoverable)
    → total_india_customs_cost: BCD + IGST working capital cost

HOW IT INTEGRATES:
  GSTComplianceModel is called alongside TariffDutyModel in the orchestrator.
  For Indian routes, both models contribute to ReVM:
    ReVM = contribution_profit
           − risk_penalty − time_cost − future_cost − fx_cost
           − sla_penalty − tariff_cost − gst_cost       ← new
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# GST RATE SCHEDULE (India)
# Source: CBIC GST Rate Schedules (as of FY 2025-26)
# Key: HS chapter prefix (2 digits)
# ─────────────────────────────────────────────────────────────────────────────

GST_RATE_BY_HS_CHAPTER: Dict[str, float] = {
    # 0% — Exempt / Zero-rated
    "01": 0.00,   # Live animals
    "02": 0.00,   # Meat and edible offal
    "03": 0.05,   # Fish (5% for processed)
    "10": 0.00,   # Cereals
    "30": 0.12,   # Pharmaceutical products (12%)
    # 5% slab
    "09": 0.05,   # Coffee, tea, spices
    "25": 0.05,   # Salt, sulphur, earth, stone
    "27": 0.05,   # Mineral fuels (petroleum — specific rates apply)
    "50": 0.05,   # Silk
    "52": 0.05,   # Cotton
    "63": 0.05,   # Textile articles
    # 12% slab
    "39": 0.12,   # Plastics and articles thereof
    "48": 0.12,   # Paper and paperboard
    "61": 0.12,   # Knitted apparel
    "62": 0.12,   # Woven apparel
    "64": 0.12,   # Footwear
    "73": 0.18,   # Steel articles (18% for most processed steel)
    # 18% slab (default for most industrial goods)
    "28": 0.18,   # Inorganic chemicals
    "29": 0.18,   # Organic chemicals
    "32": 0.18,   # Paints, varnishes, inks
    "33": 0.18,   # Essential oils, cosmetics
    "38": 0.18,   # Miscellaneous chemical products
    "40": 0.18,   # Rubber
    "44": 0.18,   # Wood and articles thereof
    "68": 0.18,   # Stone, plaster, cement articles
    "69": 0.18,   # Ceramic products
    "70": 0.18,   # Glass
    "72": 0.18,   # Iron and steel
    "76": 0.18,   # Aluminium
    "84": 0.18,   # Machinery and mechanical appliances
    "85": 0.18,   # Electrical equipment
    "87": 0.28,   # Vehicles (28% — luxury/automotive)
    "90": 0.18,   # Optical, medical instruments
    "94": 0.18,   # Furniture
    # 28% slab
    "22": 0.28,   # Beverages, spirits, vinegar
    "24": 0.28,   # Tobacco
}

# Default GST rate for chapters not listed — 18% is India's standard rate
_DEFAULT_GST_RATE = 0.18

# ─────────────────────────────────────────────────────────────────────────────
# BASIC CUSTOMS DUTY (BCD) — India import tariff
# Separate from GST. Source: Customs Tariff Act (as amended in Union Budget FY26)
# BCD is sunk cost — NOT recoverable as ITC.
# ─────────────────────────────────────────────────────────────────────────────

BCD_RATE_BY_HS_CHAPTER: Dict[str, float] = {
    "30": 0.10,   # Pharma APIs — 10% BCD
    "84": 0.075,  # Machinery — 7.5%
    "85": 0.10,   # Electronics — 10% (PLI benefit applies separately)
    "87": 0.125,  # Auto components — 12.5%
    "61": 0.20,   # Apparel — 20%
    "62": 0.20,   # Apparel — 20%
    "72": 0.075,  # Steel — 7.5%
    "29": 0.075,  # Organic chemicals — 7.5%
    "39": 0.075,  # Plastics — 7.5%
    "52": 0.00,   # Raw cotton — 0% (India is net exporter)
    "90": 0.075,  # Medical instruments — 7.5%
}

_DEFAULT_BCD_RATE = 0.075  # Conservative average for unclassified chapters


# ─────────────────────────────────────────────────────────────────────────────
# DGFT DUTY DRAWBACK — All Industry Rates (AIR)
# Source: DGFT Customs & Central Excise Duty Drawback Rules
# Expressed as % of FOB export value. NOT a refund of specific duty paid.
# Key: HS chapter prefix (2 digits)
# ─────────────────────────────────────────────────────────────────────────────

DGFT_DRAWBACK_AIR: Dict[str, float] = {
    "30": 0.021,  # Pharma formulations — 2.1% of FOB
    "84": 0.019,  # Engineering machinery — 1.9%
    "85": 0.015,  # Electronics — 1.5%
    "87": 0.017,  # Auto components — 1.7%
    "61": 0.030,  # Knitted apparel — 3.0%
    "62": 0.028,  # Woven apparel — 2.8%
    "72": 0.010,  # Steel — 1.0%
    "29": 0.018,  # Organic chemicals — 1.8%
    "52": 0.025,  # Cotton yarn/fabric — 2.5%
    "63": 0.022,  # Textile made-ups — 2.2%
    "39": 0.014,  # Plastics — 1.4%
    "90": 0.018,  # Instruments — 1.8%
}

_DEFAULT_DRAWBACK_RATE = 0.012  # 1.2% conservative default

# ─────────────────────────────────────────────────────────────────────────────
# GST REFUND LAG — realistic processing times
# Source: GSTN auto-refund SLA + field observations
# ─────────────────────────────────────────────────────────────────────────────

GST_REFUND_PROCESSING_DAYS = {
    "lut":        0,   # LUT registered exporter — no GST paid, zero lag
    "auto":      30,   # GSTN automated refund (Form RFD-01) — 30 days typical
    "manual":    75,   # Manual refund processing — 60-90 day range, use 75 midpoint
    "stuck":    120,   # Pending/stuck claims (common for first-time filers)
}

# ITC recovery lag for importers (days from import to ITC reflection in GSTR-2B)
ITC_REFLECTION_DAYS = 45  # GSTR-2B auto-population lag + reconciliation time


class GSTComplianceModel:
    """
    Computes India-specific GST and customs cost impact per shipment.

    Two modes depending on shipment direction:
      EXPORT (India origin): GST working capital cost + DGFT drawback benefit
      IMPORT (India destination): BCD + IGST cost + ITC recovery working capital

    Direction is inferred from the route string:
      Routes starting with "IN-" → EXPORT (India → foreign)
      Routes ending with "-IN"  → IMPORT (foreign → India)
      Domestic (IN-IN or LOCAL) → zero impact

    WACC is required to compute time-value of working capital.
    Passed in per-row (row["wacc"]) or defaults to tenant WACC (0.11 = 11%).
    """

    def compute_export(self, row: dict) -> dict:
        """
        Computes GST impact for an outbound Indian export shipment.

        Returns:
          gst_working_capital_cost: cost of GST refund lag (0 if LUT registered)
          dgft_drawback_benefit:    DGFT AIR drawback receivable (positive)
          net_gst_impact:           working capital cost net of drawback benefit
          refund_mode:              lut / auto / manual / stuck
          igst_paid:                IGST amount paid at time of export (0 for LUT)
          drawback_receivable:      INR value of drawback claim
        """
        order_value  = float(row.get("order_value", 0.0))
        hs_code      = str(row.get("hs_code", "")).strip()
        wacc         = float(row.get("wacc", 0.11))
        refund_mode  = str(row.get("gst_refund_mode", "auto")).lower()

        # Clamp refund_mode to known values
        if refund_mode not in GST_REFUND_PROCESSING_DAYS:
            refund_mode = "auto"

        # Resolve GST rate for this product
        gst_rate = self._resolve_gst_rate(hs_code)

        # IGST paid at export (only if NOT under LUT)
        igst_paid = 0.0
        gst_working_capital_cost = 0.0

        if refund_mode != "lut":
            igst_paid     = order_value * gst_rate
            refund_days   = GST_REFUND_PROCESSING_DAYS[refund_mode]
            # Working capital cost = IGST × WACC × (refund_days / 365)
            gst_working_capital_cost = igst_paid * wacc * (refund_days / 365.0)

        # DGFT duty drawback — receivable regardless of LUT status
        drawback_rate       = self._resolve_drawback_rate(hs_code)
        drawback_receivable = order_value * drawback_rate
        # Drawback receivable in ~90 days — its present value is slightly discounted
        drawback_pv = drawback_receivable * (1 - wacc * (90 / 365.0))

        net_gst_impact = gst_working_capital_cost - drawback_pv

        return {
            "gst_rate":                  gst_rate,
            "igst_paid":                 round(igst_paid, 2),
            "refund_mode":               refund_mode,
            "refund_lag_days":           GST_REFUND_PROCESSING_DAYS[refund_mode],
            "gst_working_capital_cost":  round(gst_working_capital_cost, 2),
            "drawback_rate":             drawback_rate,
            "drawback_receivable":       round(drawback_receivable, 2),
            "drawback_pv":               round(drawback_pv, 2),
            "net_gst_impact":            round(net_gst_impact, 2),
        }

    def compute_import(self, row: dict) -> dict:
        """
        Computes customs cost for an inbound Indian import shipment.

        BCD is sunk cost — added directly to ReVM deductions.
        IGST is recoverable as ITC, but the lag creates a working capital cost.

        Returns:
          bcd_cost:               Basic Customs Duty (sunk, non-recoverable)
          igst_on_import:         IGST levied at customs (BCD value-inclusive base)
          itc_working_capital_cost: cost of ITC recovery lag
          total_india_customs_cost: bcd_cost + itc_working_capital_cost (ReVM deduction)
        """
        cif_value    = float(row.get("order_value", 0.0))   # CIF value at Indian port
        hs_code      = str(row.get("hs_code", "")).strip()
        wacc         = float(row.get("wacc", 0.11))

        # Step 1: Basic Customs Duty (non-recoverable)
        bcd_rate = self._resolve_bcd_rate(hs_code)
        bcd_cost = cif_value * bcd_rate

        # Step 2: IGST is levied on (CIF + BCD) — the assessable value
        assessable_value = cif_value + bcd_cost
        gst_rate         = self._resolve_gst_rate(hs_code)
        igst_on_import   = assessable_value * gst_rate

        # Step 3: ITC recovery working capital cost
        # IGST is fully recoverable but GSTR-2B reflection takes ~45 days
        itc_working_capital_cost = igst_on_import * wacc * (ITC_REFLECTION_DAYS / 365.0)

        total_india_customs_cost = bcd_cost + itc_working_capital_cost

        return {
            "bcd_rate":                  bcd_rate,
            "bcd_cost":                  round(bcd_cost, 2),
            "gst_rate":                  gst_rate,
            "igst_on_import":            round(igst_on_import, 2),
            "itc_recovery_days":         ITC_REFLECTION_DAYS,
            "itc_working_capital_cost":  round(itc_working_capital_cost, 2),
            "total_india_customs_cost":  round(total_india_customs_cost, 2),
        }

    def compute(self, row: dict) -> float:
        """
        Single entry point for the ReVM pipeline.
        Returns the net GST cost to deduct from ReVM (always >= 0 in practice
        unless drawback fully offsets, which is possible for high-AIR categories).

        Direction inferred from route string.
        """
        route = str(row.get("route", "LOCAL")).upper().strip()

        if self._is_india_export(route):
            result = self.compute_export(row)
            # Store detailed breakdown on the row for audit trail
            row["gst_breakdown"] = result
            return max(0.0, result["net_gst_impact"])

        elif self._is_india_import(route):
            result = self.compute_import(row)
            row["gst_breakdown"] = result
            return result["total_india_customs_cost"]

        # Domestic or non-Indian route — zero GST impact from this model
        return 0.0

    def compute_batch(self, rows_list: list) -> list:
        return [self.compute(row) for row in rows_list]

    # ── Direction detection ───────────────────────────────────────────────────

    @staticmethod
    def _is_india_export(route: str) -> bool:
        """India → foreign. Route starts with IN- but isn't domestic."""
        return route.startswith("IN-") and not route.endswith("-IN")

    @staticmethod
    def _is_india_import(route: str) -> bool:
        """Foreign → India. Route ends with -IN but doesn't start with IN."""
        return route.endswith("-IN") and not route.startswith("IN-")

    # ── Rate resolution helpers ───────────────────────────────────────────────

    @staticmethod
    def _resolve_gst_rate(hs_code: str) -> float:
        if hs_code and len(hs_code) >= 2:
            chapter = hs_code[:2]
            if chapter in GST_RATE_BY_HS_CHAPTER:
                return GST_RATE_BY_HS_CHAPTER[chapter]
        return _DEFAULT_GST_RATE

    @staticmethod
    def _resolve_bcd_rate(hs_code: str) -> float:
        if hs_code and len(hs_code) >= 2:
            chapter = hs_code[:2]
            if chapter in BCD_RATE_BY_HS_CHAPTER:
                return BCD_RATE_BY_HS_CHAPTER[chapter]
        return _DEFAULT_BCD_RATE

    @staticmethod
    def _resolve_drawback_rate(hs_code: str) -> float:
        if hs_code and len(hs_code) >= 2:
            chapter = hs_code[:2]
            if chapter in DGFT_DRAWBACK_AIR:
                return DGFT_DRAWBACK_AIR[chapter]
        return _DEFAULT_DRAWBACK_RATE
