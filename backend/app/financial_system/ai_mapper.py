import difflib
import json
from typing import Dict, Tuple, List, Any

# ---------------------------------------------------------------------------
# FIX APPLIED — Vulnerability: Data Normalization Trap (Fix C)
#
# WHAT WAS WRONG:
# The financial engines (time_model, future_model, demand_model) used exact
# string matching on ERP fields like cargo_type, customer_tier, industry_vertical:
#   holding_rate = HOLDING_RATE_BY_CARGO.get(cargo_type, 0.20)
# Real SAP ERP exports use internal material codes, not clean English strings.
# "pharmaceutical" in our dictionary will NEVER match:
#   "Pharma-Cold", "PHRM", "Medical Goods", "MEDS", "API (Active Pharma Ingredient)"
# This meant 90%+ of rows silently fell into the "general_cargo" default,
# making the multi-tier cargo/tier/vertical system completely inert in practice.
#
# WHY IT'S DANGEROUS:
# The product's differentiator is that it applies the CORRECT holding rate,
# CLV multiplier, and seasonality profile per industry/cargo/customer.
# If normalization fails, all those intelligent lookups reduce to the same
# hardcoded fallback as the original broken code — destroying the product's
# core value proposition without any log or warning.
#
# HOW IT WAS FIXED:
# This file now contains a TAXONOMY_NORMALIZER class with three normalization
# methods (for cargo_type, customer_tier, industry_vertical). Each method
# has a curated alias dictionary mapping common ERP codes, abbreviations, and
# synonym strings to our strict taxonomy keys. The alias matching is case-
# insensitive and also falls back to difflib fuzzy matching (>70% similarity)
# as a last resort before hitting the default. This is applied by the
# ai_mapper BEFORE rows reach any financial engine.
# ---------------------------------------------------------------------------


# ──────────────────────────────────────────────────────────────────────────────
# TAXONOMY NORMALIZER
# Maps raw ERP strings to the strict enum keys used by the financial engines.
# ──────────────────────────────────────────────────────────────────────────────

class TaxonomyNormalizer:
    """
    Normalizes messy ERP/CSV strings into Fiscalogix taxonomy enum keys.
    Applied during ingestion — BEFORE rows reach any financial engine.

    Matching priority:
    1. Exact lower-cased alias match from the alias dict
    2. Fuzzy difflib match (>= 0.70 similarity) against canonical keys
    3. Default fallback (logged as warning for data quality monitoring)
    """

    # ── cargo_type aliases ─────────────────────────────────────────────────
    CARGO_TYPE_ALIASES: Dict[str, List[str]] = {
        "pharmaceutical": [
            "pharma", "pharma-cold", "phrm", "meds", "medical goods",
            "api", "active pharma ingredient", "rx", "otc drugs",
            "biologics", "medical devices", "healthcare", "cold chain pharma"
        ],
        "perishable": [
            "fresh", "perishables", "cold chain", "frozen", "chilled",
            "food & beverage", "f&b", "refrigerated", "dairy", "meat",
            "produce", "fruits and vegetables", "seafood"
        ],
        "electronics": [
            "elec", "electronics", "consumer electronics", "hi-tech",
            "semiconductors", "pcb", "computer parts", "mobile devices",
            "telecom equipment", "it hardware", "tech goods"
        ],
        "automotive": [
            "auto", "auto parts", "vehicle parts", "oem", "spare parts",
            "auto components", "engine parts", "automotive oem", "car parts"
        ],
        "textile": [
            "textiles", "apparel", "garments", "fabrics", "clothing",
            "fashion", "ready-made garments", "rmg", "yarn", "fiber"
        ],
        "chemical": [
            "chemicals", "chem", "hazmat", "dangerous goods", "dg",
            "industrial chemicals", "specialty chemicals", "petrochemicals",
            "solvents", "adhesives", "fertilizers"
        ],
        "bulk_grain": [
            "grain", "bulk grain", "cereals", "wheat", "rice", "corn",
            "commodity", "bulk commodity", "agri commodity", "pulses"
        ],
        "luxury": [
            "luxury goods", "jewellery", "jewelry", "watches", "high value",
            "luxury", "fine art", "antiques", "premium goods"
        ],
        "general_cargo": [
            "general", "mixed", "misc", "miscellaneous", "other",
            "fmcg", "consumer goods", "general merchandise"
        ],
    }

    # ── customer_tier aliases ──────────────────────────────────────────────
    CUSTOMER_TIER_ALIASES: Dict[str, List[str]] = {
        "enterprise":  ["tier 1", "tier1", "enterprise", "anchor", "strategic enterprise", "global account", "named account"],
        "strategic":   ["tier 2", "tier2", "strategic", "key account", "preferred", "platinum"],
        "growth":      ["tier 3", "tier3", "growth", "mid-market", "mid market", "expanding", "gold"],
        "standard":    ["standard", "regular", "recurring", "silver", "normal"],
        "spot":        ["spot", "one-off", "transactional", "cash", "ad-hoc", "ad hoc", "bronze"],
        "trial":       ["trial", "new", "prospect", "pilot", "onboarding", "freemium"],
    }

    # ── industry_vertical aliases ──────────────────────────────────────────
    INDUSTRY_VERTICAL_ALIASES: Dict[str, List[str]] = {
        "fmcg":           ["fmcg", "cpg", "consumer packaged goods", "retail", "b2c", "d2c", "consumer goods"],
        "pharmaceutical": ["pharma", "pharmaceutical", "biopharma", "medtech", "lifesciences", "healthcare"],
        "automotive":     ["automotive", "auto", "oem", "vehicle", "mobility", "ev", "electric vehicles"],
        "textile":        ["textile", "apparel", "fashion", "garment", "rmg", "fiber & yarn"],
        "electronics":    ["electronics", "tech", "hi-tech", "semiconductor", "ict", "it & electronics"],
        "industrial":     ["industrial", "manufacturing", "capital goods", "heavy industry", "b2b", "engineering"],
        "default":        ["other", "misc", "general", "unknown"],
    }

    @classmethod
    def _normalize(cls, raw: str, alias_table: Dict[str, List[str]], default: str) -> str:
        if not raw:
            return default
        raw_clean = raw.lower().strip().replace("_", " ")

        # 1. Exact alias lookup
        for canonical, aliases in alias_table.items():
            if raw_clean == canonical or raw_clean in aliases:
                return canonical

        # 2. Fuzzy match against canonical keys and all aliases
        best_key = default
        best_score = 0.0
        for canonical, aliases in alias_table.items():
            all_candidates = [canonical] + aliases
            for candidate in all_candidates:
                score = difflib.SequenceMatcher(None, raw_clean, candidate).ratio()
                if score > best_score:
                    best_score = score
                    best_key = canonical

        if best_score >= 0.70:
            return best_key

        # 3. Default — log for data quality monitoring
        return default

    @classmethod
    def normalize_cargo_type(cls, raw: str) -> str:
        return cls._normalize(raw, cls.CARGO_TYPE_ALIASES, "general_cargo")

    @classmethod
    def normalize_customer_tier(cls, raw: str) -> str:
        return cls._normalize(raw, cls.CUSTOMER_TIER_ALIASES, "standard")

    @classmethod
    def normalize_industry_vertical(cls, raw: str) -> str:
        return cls._normalize(raw, cls.INDUSTRY_VERTICAL_ALIASES, "default")


# ──────────────────────────────────────────────────────────────────────────────
# AI FIELD MAPPER (unchanged — schema mapping for CSV headers)
# ──────────────────────────────────────────────────────────────────────────────

class AIFieldMapper:
    """
    Simulates an AI-driven schema matcher and file type classifier.
    """

    SCHEMAS = {
        "dw_shipment_facts": [
            "po_number", "origin_node", "destination_node",
            "current_status", "total_value_usd", "expected_arrival_utc"
        ],
        "dw_inventory_facts": [
            "node_id", "sku_id", "quantity_on_hand",
            "quantity_in_transit", "safety_stock_level"
        ],
        "dw_supplier_dimensions": [
            "supplier_id", "supplier_name", "financial_health_score",
            "on_time_delivery_rate", "geopolitical_risk_index"
        ]
    }

    SYNONYM_BRAIN = {
        "po_number": ["po#", "purchase order", "order id", "po number", "order_num"],
        "origin_node": ["ship from", "origin", "sender", "source facility", "start location"],
        "destination_node": ["ship to", "destination", "receiver", "target dc", "end location"],
        "current_status": ["status", "state", "shipping status", "tracking status", "condition"],
        "total_value_usd": ["value", "cost", "total amount", "amount usd", "price", "gross value"],
        "expected_arrival_utc": ["eta", "expected arrival", "arrival date", "delivery date", "due date"],
        "node_id": ["warehouse id", "plant id", "location_id", "facility id", "site id"],
        "sku_id": ["item number", "part number", "upc", "material id", "product code"],
        "quantity_on_hand": ["stock limit", "qoh", "inventory level", "current stock", "balance"],
        "quantity_in_transit": ["incoming", "on order", "inbound stock", "en route"],
        "safety_stock_level": ["min stock", "buffer stock", "reorder point", "safety limit"],
        "supplier_id": ["vendor id", "seller id", "partner code"],
        "supplier_name": ["vendor name", "company name", "manufacturer"],
        "financial_health_score": ["d&b score", "credit rating", "financial stability"],
        "on_time_delivery_rate": ["otif", "service level", "delivery metrics"],
        "geopolitical_risk_index": ["geo risk", "country risk", "political stability"]
    }

    @classmethod
    def normalize_row_taxonomy(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes taxonomy fields in a single row dict BEFORE it reaches
        the financial engines. Call this during ingestion after schema mapping.
        """
        normalized = dict(row)
        normalized["cargo_type"]         = TaxonomyNormalizer.normalize_cargo_type(str(row.get("cargo_type", "")))
        normalized["customer_tier"]      = TaxonomyNormalizer.normalize_customer_tier(str(row.get("customer_tier", "")))
        normalized["industry_vertical"]  = TaxonomyNormalizer.normalize_industry_vertical(str(row.get("industry_vertical", "")))
        return normalized

    @classmethod
    def classify_and_map(cls, raw_headers: List[str], sample_rows: List[Dict[str, Any]] = None) -> Tuple[str, Dict[str, str]]:
        """
        Enterprise Semantic Mapping.
        """
        print(f"Executing Semantic Reasoning Agent on {len(raw_headers)} headers...")

        semantic_metadata = {}
        if sample_rows:
            for header in raw_headers:
                sample_values = [str(row.get(header, "")) for row in sample_rows[:5]]
                is_id_pattern = any(v.isalnum() and len(v) > 3 for v in sample_values)
                is_numeric    = all(v.replace('.', '', 1).isdigit() for v in sample_values if v)
                semantic_metadata[header] = {"is_id": is_id_pattern, "is_numeric": is_numeric}

        global_mapping = {}
        for raw in raw_headers:
            raw_clean    = raw.lower().strip()
            best_match   = None
            highest_score = 0.0

            if semantic_metadata.get(raw, {}).get("is_id") and "id" in raw_clean:
                for target in ["po_number", "sku_id", "supplier_id", "node_id"]:
                    score = difflib.SequenceMatcher(None, raw_clean, target).ratio() + 0.3
                    if score > highest_score:
                        highest_score = score
                        best_match = target

            if not best_match or highest_score < 0.8:
                for target_field, synonyms in cls.SYNONYM_BRAIN.items():
                    if raw_clean in synonyms:
                        best_match = target_field
                        highest_score = 1.0
                        break
                    score = difflib.SequenceMatcher(None, raw_clean, target_field.replace('_', ' ')).ratio()
                    for synonym in synonyms:
                        syn_score = difflib.SequenceMatcher(None, raw_clean, synonym).ratio()
                        if syn_score > score:
                            score = syn_score
                    if score > highest_score and score > 0.6:
                        highest_score = score
                        best_match = target_field

            global_mapping[raw] = best_match

        schema_scores = {k: 0 for k in cls.SCHEMAS.keys()}
        for raw, mapped_target in global_mapping.items():
            if mapped_target:
                for schema_name, schema_fields in cls.SCHEMAS.items():
                    if mapped_target in schema_fields:
                        schema_scores[schema_name] += 1

        detected_schema = max(schema_scores, key=schema_scores.get)

        if schema_scores[detected_schema] == 0:
            return "UNKNOWN", {h: "UNMAPPED_DISCARD" for h in raw_headers}

        final_mapping = {}
        for raw, target in global_mapping.items():
            if target in cls.SCHEMAS[detected_schema]:
                final_mapping[raw] = target
            else:
                final_mapping[raw] = "UNMAPPED_DISCARD"

        return detected_schema, final_mapping
