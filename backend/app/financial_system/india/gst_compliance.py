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
    # ── SECTION I: Live animals & animal products (Ch 01–05) ─────────────────
    "01": 0.00,   # Live animals — Nil
    "02": 0.00,   # Meat & edible offal — Nil (fresh/chilled); 12% for processed
    "03": 0.05,   # Fish & crustaceans — 5% (processed/frozen); Nil for fresh
    "04": 0.05,   # Dairy, eggs, honey — 5% (branded); Nil for unbranded
    "05": 0.05,   # Animal products NES — 5%

    # ── SECTION II: Vegetable products (Ch 06–14) ────────────────────────────
    "06": 0.05,   # Live plants, flowers — 5%
    "07": 0.00,   # Vegetables — Nil (fresh); 5% for frozen/preserved
    "08": 0.00,   # Fruits & nuts — Nil (fresh); 12% for dried/processed
    "09": 0.05,   # Coffee, tea, spices — 5%
    "10": 0.00,   # Cereals (rice, wheat) — Nil (unbranded); 5% for branded
    "11": 0.05,   # Milling products (flour, starch) — 5%
    "12": 0.05,   # Oil seeds, misc grains — 5%
    "13": 0.12,   # Lac, gums, resins — 12% (shellac 5%)
    "14": 0.00,   # Vegetable plaiting materials — Nil

    # ── SECTION III: Animal/vegetable fats & oils (Ch 15) ────────────────────
    "15": 0.05,   # Fats, oils (edible) — 5%; hydrogenated veg oil 12%

    # ── SECTION IV: Food, beverages, tobacco (Ch 16–24) ─────────────────────
    "16": 0.12,   # Preparations of meat, fish — 12%
    "17": 0.05,   # Sugar, confectionery — 5% (sugar); 18% (chocolates)
    "18": 0.18,   # Cocoa & preparations — 18%
    "19": 0.18,   # Cereals, flour preparations (biscuits, bread) — 18%
    "20": 0.12,   # Preparations of vegetables, fruits — 12% (jams, juices)
    "21": 0.18,   # Miscellaneous edible preparations (sauces, soups) — 18%
    "22": 0.28,   # Beverages, spirits, vinegar — 28% + cess
    "23": 0.00,   # Residues, animal feed — Nil
    "24": 0.28,   # Tobacco & manufactured substitutes — 28% + cess

    # ── SECTION V: Mineral products (Ch 25–27) ───────────────────────────────
    "25": 0.05,   # Salt, sulphur, earth, stone — 5% (cement 28%)
    "26": 0.00,   # Ores, slag, ash — Nil
    "27": 0.05,   # Mineral fuels, petroleum products — 5% (LNG/CNG); petrol/diesel outside GST

    # ── SECTION VI: Chemicals (Ch 28–38) ────────────────────────────────────
    "28": 0.18,   # Inorganic chemicals — 18%
    "29": 0.18,   # Organic chemicals — 18%
    "30": 0.12,   # Pharmaceutical products — 12% (life-saving drugs 5% or Nil)
    "31": 0.05,   # Fertilisers — 5%
    "32": 0.18,   # Tanning/dyeing extracts, paints, varnishes — 18%
    "33": 0.18,   # Essential oils, cosmetics, toiletries — 18% (28% for luxury perfumes)
    "34": 0.18,   # Soap, detergents, waxes — 18%
    "35": 0.18,   # Albuminoidal substances, glues, enzymes — 18%
    "36": 0.18,   # Explosives, pyrotechnics — 18%
    "37": 0.18,   # Photographic/cinematographic goods — 18%
    "38": 0.18,   # Miscellaneous chemical products — 18%

    # ── SECTION VII: Plastics & rubber (Ch 39–40) ────────────────────────────
    "39": 0.18,   # Plastics and articles thereof — 18% (12% for some packaging)
    "40": 0.18,   # Rubber and articles thereof — 18%

    # ── SECTION VIII: Hides, leather, travel goods (Ch 41–43) ───────────────
    "41": 0.05,   # Raw hides and skins — 5%
    "42": 0.18,   # Leather articles, saddlery, bags — 18%
    "43": 0.12,   # Furskins and articles — 12%

    # ── SECTION IX: Wood, cork, straw (Ch 44–46) ────────────────────────────
    "44": 0.18,   # Wood and articles thereof — 18% (12% for plywood)
    "45": 0.12,   # Cork and articles thereof — 12%
    "46": 0.12,   # Manufactures of straw, basketware — 12%

    # ── SECTION X: Pulp, paper (Ch 47–49) ───────────────────────────────────
    "47": 0.12,   # Pulp of wood — 12%
    "48": 0.12,   # Paper and paperboard — 12% (18% for coated/specialty)
    "49": 0.12,   # Printed books, newspapers, maps — 12% (0% for books)

    # ── SECTION XI: Textiles (Ch 50–63) ─────────────────────────────────────
    "50": 0.05,   # Silk — 5%
    "51": 0.05,   # Wool, animal hair — 5%
    "52": 0.05,   # Cotton — 5%
    "53": 0.05,   # Other vegetable textile fibres — 5%
    "54": 0.12,   # Man-made filaments — 12%
    "55": 0.12,   # Man-made staple fibres — 12%
    "56": 0.12,   # Wadding, felt, nonwovens, cordage — 12%
    "57": 0.12,   # Carpets and textile floor coverings — 12%
    "58": 0.12,   # Special woven fabrics — 12%
    "59": 0.12,   # Impregnated/coated textile fabrics — 12%
    "60": 0.12,   # Knitted or crocheted fabrics — 12%
    "61": 0.12,   # Knitted or crocheted apparel — 12% (5% if ≤₹1000/pc)
    "62": 0.12,   # Woven apparel — 12% (5% if ≤₹1000/pc)
    "63": 0.05,   # Textile made-ups, worn clothing — 5% (12% for blankets)

    # ── SECTION XII: Footwear, headgear (Ch 64–67) ──────────────────────────
    "64": 0.18,   # Footwear — 18% (5% if ≤₹1000/pair)
    "65": 0.18,   # Headgear — 18%
    "66": 0.12,   # Umbrellas, walking sticks — 12%
    "67": 0.12,   # Prepared feathers, artificial flowers — 12%

    # ── SECTION XIII: Stone, ceramic, glass (Ch 68–70) ──────────────────────
    "68": 0.18,   # Stone, plaster, cement articles — 18% (28% for cement)
    "69": 0.18,   # Ceramic products — 18% (12% for earthenware)
    "70": 0.18,   # Glass and glassware — 18%

    # ── SECTION XIV: Precious metals, gems (Ch 71) ──────────────────────────
    "71": 0.03,   # Precious metals, gems, jewellery — 3% (0.25% for diamonds)

    # ── SECTION XV: Base metals (Ch 72–83) ──────────────────────────────────
    "72": 0.18,   # Iron and steel — 18%
    "73": 0.18,   # Articles of iron or steel — 18%
    "74": 0.18,   # Copper and articles thereof — 18%
    "75": 0.18,   # Nickel and articles thereof — 18%
    "76": 0.18,   # Aluminium and articles thereof — 18%
    "77": 0.18,   # Reserved chapter — 18% default
    "78": 0.18,   # Lead and articles thereof — 18%
    "79": 0.18,   # Zinc and articles thereof — 18%
    "80": 0.18,   # Tin and articles thereof — 18%
    "81": 0.18,   # Other base metals — 18%
    "82": 0.18,   # Tools, cutlery — 18%
    "83": 0.18,   # Miscellaneous articles of base metal — 18%

    # ── SECTION XVI: Machinery & electrical (Ch 84–85) ──────────────────────
    "84": 0.18,   # Nuclear reactors, machinery — 18% (12% for some agri machinery)
    "85": 0.18,   # Electrical equipment, electronics — 18% (28% for ACs, TVs >32")

    # ── SECTION XVII: Vehicles & transport (Ch 86–89) ───────────────────────
    "86": 0.12,   # Railway locomotives and stock — 12%
    "87": 0.28,   # Motor vehicles — 28% + cess (e-vehicles 5%)
    "88": 0.18,   # Aircraft, spacecraft — 18% (5% for parts used in MRO)
    "89": 0.05,   # Ships and boats — 5%

    # ── SECTION XVIII: Optical, clocks, instruments (Ch 90–92) ─────────────
    "90": 0.18,   # Optical, photographic, medical instruments — 18%
    "91": 0.18,   # Clocks and watches — 18%
    "92": 0.12,   # Musical instruments — 12%

    # ── SECTION XIX: Arms & ammunition (Ch 93) ──────────────────────────────
    "93": 0.18,   # Arms, ammunition — 18%

    # ── SECTION XX: Miscellaneous manufactures (Ch 94–96) ───────────────────
    "94": 0.18,   # Furniture, bedding, lamps — 18% (12% for wooden furniture)
    "95": 0.12,   # Toys, games, sports equipment — 12% (28% if video games)
    "96": 0.18,   # Miscellaneous manufactured articles — 18%

    # ── SECTION XXI: Works of art, antiques (Ch 97–98) ──────────────────────
    "97": 0.12,   # Works of art, collectors' pieces, antiques — 12%
    "98": 0.18,   # Special classification provisions (project imports etc.) — 18%
}

# Default GST rate for chapters not listed — 18% is India's standard rate
_DEFAULT_GST_RATE = 0.18

# ─────────────────────────────────────────────────────────────────────────────
# BASIC CUSTOMS DUTY (BCD) — India import tariff
# Separate from GST. Source: Customs Tariff Act (as amended in Union Budget FY26)
# BCD is sunk cost — NOT recoverable as ITC.
# ─────────────────────────────────────────────────────────────────────────────

BCD_RATE_BY_HS_CHAPTER: Dict[str, float] = {
    # ── Live animals & animal products ───────────────────────────────────────
    "01": 0.00,   # Live animals — 0% (India is net importer for stud animals)
    "02": 0.30,   # Meat — 30% (protectionist)
    "03": 0.30,   # Fish — 30%
    "04": 0.30,   # Dairy — 30% (60% for liquid milk; protecting domestic dairy)
    "05": 0.00,   # Animal products NES — 0%

    # ── Vegetable products ───────────────────────────────────────────────────
    "06": 0.05,   # Plants, flowers — 5%
    "07": 0.30,   # Vegetables — 30% (agricultural protection)
    "08": 0.30,   # Fruits, nuts — 30% (50% for apples)
    "09": 0.10,   # Coffee, tea, spices — 10%
    "10": 0.50,   # Cereals — 50% (wheat 100%; rice highly protected)
    "11": 0.30,   # Milling products — 30%
    "12": 0.30,   # Oil seeds — 30% (0% for soybean for crushing)
    "13": 0.10,   # Gums, resins — 10%
    "14": 0.00,   # Vegetable plaiting materials — 0%

    # ── Fats & oils ──────────────────────────────────────────────────────────
    "15": 0.10,   # Edible oils — 10% (100% for crude palm oil seasonally)

    # ── Food & beverages ─────────────────────────────────────────────────────
    "16": 0.30,   # Meat/fish preparations — 30%
    "17": 0.40,   # Sugar — 40% (highly protected sector)
    "18": 0.30,   # Cocoa products — 30%
    "19": 0.30,   # Cereal preparations — 30%
    "20": 0.30,   # Vegetable/fruit preparations — 30%
    "21": 0.30,   # Misc edible preparations — 30%
    "22": 0.150,  # Beverages, spirits — 150% for spirits; 50% average
    "23": 0.05,   # Animal feed residues — 5%
    "24": 0.30,   # Tobacco — 30%

    # ── Mineral products ─────────────────────────────────────────────────────
    "25": 0.05,   # Salt, stone, cement raw materials — 5%
    "26": 0.00,   # Ores — 0% (India needs raw materials)
    "27": 0.05,   # Petroleum — 5% (crude 0%; refined products 2.5–5%)

    # ── Chemicals ────────────────────────────────────────────────────────────
    "28": 0.075,  # Inorganic chemicals — 7.5%
    "29": 0.075,  # Organic chemicals — 7.5%
    "30": 0.10,   # Pharmaceuticals — 10% (0% for patented life-saving)
    "31": 0.05,   # Fertilisers — 5% (0% for urea; strategic import)
    "32": 0.075,  # Paints, varnishes — 7.5%
    "33": 0.20,   # Cosmetics, essential oils — 20%
    "34": 0.10,   # Soap, detergents — 10%
    "35": 0.075,  # Albuminoidal substances — 7.5%
    "36": 0.10,   # Explosives — 10%
    "37": 0.10,   # Photo goods — 10%
    "38": 0.075,  # Misc chemical products — 7.5%

    # ── Plastics & rubber ────────────────────────────────────────────────────
    "39": 0.075,  # Plastics — 7.5%
    "40": 0.10,   # Rubber — 10% (25% for tyres)

    # ── Hides & leather ──────────────────────────────────────────────────────
    "41": 0.00,   # Raw hides — 0% (India is major exporter)
    "42": 0.10,   # Leather goods, bags — 10%
    "43": 0.10,   # Furskins — 10%

    # ── Wood, cork, straw ────────────────────────────────────────────────────
    "44": 0.10,   # Wood — 10% (5% for logs; afforestation policy)
    "45": 0.10,   # Cork — 10%
    "46": 0.10,   # Basketware — 10%

    # ── Paper & printing ─────────────────────────────────────────────────────
    "47": 0.05,   # Paper pulp — 5%
    "48": 0.10,   # Paper, paperboard — 10%
    "49": 0.00,   # Printed books — 0% (education policy)

    # ── Textiles ─────────────────────────────────────────────────────────────
    "50": 0.10,   # Silk — 10%
    "51": 0.10,   # Wool — 10%
    "52": 0.00,   # Cotton raw — 0% (India is net exporter)
    "53": 0.10,   # Other veg fibres — 10%
    "54": 0.20,   # Man-made filaments — 20%
    "55": 0.20,   # Man-made staple — 20%
    "56": 0.20,   # Wadding, felt, nonwovens — 20%
    "57": 0.20,   # Carpets — 20%
    "58": 0.20,   # Special woven fabrics — 20%
    "59": 0.20,   # Coated fabrics — 20%
    "60": 0.20,   # Knitted fabrics — 20%
    "61": 0.20,   # Knitted apparel — 20%
    "62": 0.20,   # Woven apparel — 20%
    "63": 0.20,   # Textile made-ups — 20%

    # ── Footwear & headgear ──────────────────────────────────────────────────
    "64": 0.20,   # Footwear — 20%
    "65": 0.20,   # Headgear — 20%
    "66": 0.20,   # Umbrellas — 20%
    "67": 0.20,   # Feathers, artificial flowers — 20%

    # ── Stone, ceramic, glass ────────────────────────────────────────────────
    "68": 0.075,  # Stone articles — 7.5%
    "69": 0.10,   # Ceramics — 10%
    "70": 0.10,   # Glass — 10%

    # ── Precious metals & gems ───────────────────────────────────────────────
    "71": 0.075,  # Gold 15%; silver 15%; diamonds 0%; jewellery 7.5% avg

    # ── Base metals ──────────────────────────────────────────────────────────
    "72": 0.075,  # Iron and steel — 7.5% (0% for scrap; protects domestic mills)
    "73": 0.075,  # Steel articles — 7.5%
    "74": 0.05,   # Copper — 5%
    "75": 0.025,  # Nickel — 2.5%
    "76": 0.075,  # Aluminium — 7.5%
    "77": 0.075,  # Reserved — 7.5% default
    "78": 0.025,  # Lead — 2.5%
    "79": 0.025,  # Zinc — 2.5%
    "80": 0.025,  # Tin — 2.5%
    "81": 0.075,  # Other base metals — 7.5%
    "82": 0.075,  # Tools, cutlery — 7.5%
    "83": 0.075,  # Misc base metal articles — 7.5%

    # ── Machinery & electrical ───────────────────────────────────────────────
    "84": 0.075,  # Machinery — 7.5% (0% for some capital goods; PLI scheme)
    "85": 0.10,   # Electronics — 10% (20% for mobile phones; PLI tariff wall)

    # ── Transport equipment ──────────────────────────────────────────────────
    "86": 0.075,  # Railway — 7.5%
    "87": 0.125,  # Vehicles — 12.5%–100% (cars 60–100%; e-vehicles 15%)
    "88": 0.025,  # Aircraft — 2.5% (strategic; mostly 0% for commercial)
    "89": 0.05,   # Ships — 5%

    # ── Instruments ──────────────────────────────────────────────────────────
    "90": 0.075,  # Instruments, medical devices — 7.5%
    "91": 0.10,   # Clocks, watches — 10%
    "92": 0.10,   # Musical instruments — 10%

    # ── Arms ────────────────────────────────────────────────────────────────
    "93": 0.10,   # Arms, ammunition — 10% (defence imports often 0%)

    # ── Misc manufactures ────────────────────────────────────────────────────
    "94": 0.20,   # Furniture — 20%
    "95": 0.20,   # Toys, games — 20% (60% for toy imports post-2021 policy)
    "96": 0.20,   # Misc manufactured articles — 20%

    # ── Art & antiques ───────────────────────────────────────────────────────
    "97": 0.00,   # Works of art, antiques — 0%
    "98": 0.075,  # Special provisions — 7.5% default
}

_DEFAULT_BCD_RATE = 0.075  # MFN average; used only if HS chapter resolution fails


# ─────────────────────────────────────────────────────────────────────────────
# DGFT DUTY DRAWBACK — All Industry Rates (AIR)
# Source: DGFT Customs & Central Excise Duty Drawback Rules
# Expressed as % of FOB export value. NOT a refund of specific duty paid.
# Key: HS chapter prefix (2 digits)
# ─────────────────────────────────────────────────────────────────────────────

DGFT_DRAWBACK_AIR: Dict[str, float] = {
    # ── Animal products ───────────────────────────────────────────────────────
    "02": 0.000,  # Meat — 0% (no AIR; perishable; exports are Nil-rated)
    "03": 0.010,  # Processed fish — 1.0%
    "04": 0.000,  # Dairy — 0%
    "05": 0.005,  # Animal products NES — 0.5%

    # ── Vegetable products ───────────────────────────────────────────────────
    "08": 0.010,  # Processed fruits — 1.0%
    "09": 0.015,  # Spices, tea, coffee — 1.5%
    "11": 0.010,  # Milling products — 1.0%
    "12": 0.008,  # Oil seeds — 0.8%
    "13": 0.010,  # Gums, resins — 1.0%

    # ── Fats & oils ──────────────────────────────────────────────────────────
    "15": 0.015,  # Edible oils (refined) — 1.5%

    # ── Food preparations ────────────────────────────────────────────────────
    "16": 0.020,  # Meat/fish preparations — 2.0%
    "17": 0.010,  # Sugar products — 1.0%
    "18": 0.015,  # Cocoa preparations — 1.5%
    "19": 0.015,  # Cereal preparations (biscuits, pasta) — 1.5%
    "20": 0.018,  # Fruit/veg preparations — 1.8%
    "21": 0.015,  # Misc food preparations — 1.5%

    # ── Chemicals ────────────────────────────────────────────────────────────
    "28": 0.015,  # Inorganic chemicals — 1.5%
    "29": 0.018,  # Organic chemicals — 1.8%
    "30": 0.021,  # Pharma formulations — 2.1%
    "32": 0.014,  # Paints, varnishes, inks — 1.4%
    "33": 0.016,  # Cosmetics, essential oils — 1.6%
    "34": 0.012,  # Soaps, detergents — 1.2%
    "38": 0.013,  # Misc chemicals — 1.3%

    # ── Plastics & rubber ────────────────────────────────────────────────────
    "39": 0.014,  # Plastics and articles — 1.4%
    "40": 0.015,  # Rubber articles — 1.5%

    # ── Leather & travel goods ───────────────────────────────────────────────
    "41": 0.010,  # Leather (raw/semi-processed) — 1.0%
    "42": 0.035,  # Leather goods, bags, harness — 3.5%
    "43": 0.020,  # Furskin articles — 2.0%

    # ── Wood & paper ─────────────────────────────────────────────────────────
    "44": 0.010,  # Wood articles — 1.0%
    "47": 0.008,  # Paper pulp — 0.8%
    "48": 0.010,  # Paper, paperboard — 1.0%

    # ── Textiles (India's largest drawback beneficiary sector) ───────────────
    "50": 0.020,  # Silk fabrics — 2.0%
    "51": 0.018,  # Wool fabrics — 1.8%
    "52": 0.025,  # Cotton yarn/fabric — 2.5%
    "53": 0.015,  # Other veg fibre — 1.5%
    "54": 0.022,  # Man-made filament fabrics — 2.2%
    "55": 0.022,  # Man-made staple fabrics — 2.2%
    "56": 0.015,  # Nonwovens, cordage — 1.5%
    "57": 0.025,  # Carpets — 2.5%
    "58": 0.020,  # Special woven fabrics — 2.0%
    "59": 0.015,  # Coated/industrial fabrics — 1.5%
    "60": 0.020,  # Knitted fabrics — 2.0%
    "61": 0.030,  # Knitted apparel — 3.0%
    "62": 0.028,  # Woven apparel — 2.8%
    "63": 0.022,  # Textile made-ups (towels, bed linen) — 2.2%

    # ── Footwear ────────────────────────────────────────────────────────────
    "64": 0.032,  # Footwear (leather uppers) — 3.2%

    # ── Stone, ceramic, glass ────────────────────────────────────────────────
    "68": 0.008,  # Stone articles — 0.8%
    "69": 0.010,  # Ceramics — 1.0%
    "70": 0.010,  # Glass — 1.0%

    # ── Gems & jewellery ────────────────────────────────────────────────────
    "71": 0.010,  # Gems and jewellery — 1.0% (cut & polished diamonds vary)

    # ── Base metals & metal products ────────────────────────────────────────
    "72": 0.010,  # Iron and steel — 1.0%
    "73": 0.012,  # Steel articles — 1.2%
    "74": 0.012,  # Copper articles — 1.2%
    "75": 0.010,  # Nickel articles — 1.0%
    "76": 0.012,  # Aluminium articles — 1.2%
    "82": 0.015,  # Tools, cutlery — 1.5%
    "83": 0.015,  # Misc base metal articles — 1.5%

    # ── Machinery & engineering ──────────────────────────────────────────────
    "84": 0.019,  # Machinery (engineering goods) — 1.9%
    "85": 0.015,  # Electronics — 1.5%

    # ── Transport ────────────────────────────────────────────────────────────
    "86": 0.010,  # Railway equipment — 1.0%
    "87": 0.017,  # Auto parts, vehicles — 1.7%
    "89": 0.010,  # Ships, boats — 1.0%

    # ── Precision instruments ────────────────────────────────────────────────
    "90": 0.018,  # Instruments, medical devices — 1.8%
    "91": 0.015,  # Watches, clocks — 1.5%
    "92": 0.012,  # Musical instruments — 1.2%

    # ── Misc manufactures ────────────────────────────────────────────────────
    "94": 0.018,  # Furniture — 1.8%
    "95": 0.015,  # Toys, sporting goods — 1.5%
    "96": 0.012,  # Misc manufactures — 1.2%
}

_DEFAULT_DRAWBACK_RATE = 0.012  # 1.2% — DGFT AIR average for uncategorised chapters

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
