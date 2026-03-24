import difflib
import json
from typing import Dict, Tuple, List, Any

class AIFieldMapper:
    """
    Simulates an AI-driven schema matcher and file type classifier.
    """
    
    # 1. Define the possible target schemas
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
    
    # 2. Synonym "Brain" mapped globally across all schemas
    SYNONYM_BRAIN = {
        # Shipments
        "po_number": ["po#", "purchase order", "order id", "po number", "order_num"],
        "origin_node": ["ship from", "origin", "sender", "source facility", "start location"],
        "destination_node": ["ship to", "destination", "receiver", "target dc", "end location"],
        "current_status": ["status", "state", "shipping status", "tracking status", "condition"],
        "total_value_usd": ["value", "cost", "total amount", "amount usd", "price", "gross value"],
        "expected_arrival_utc": ["eta", "expected arrival", "arrival date", "delivery date", "due date"],
        
        # Inventory
        "node_id": ["warehouse id", "plant id", "location_id", "facility id", "site id"],
        "sku_id": ["item number", "part number", "upc", "material id", "product code"],
        "quantity_on_hand": ["stock limit", "qoh", "inventory level", "current stock", "balance"],
        "quantity_in_transit": ["incoming", "on order", "inbound stock", "en route"],
        "safety_stock_level": ["min stock", "buffer stock", "reorder point", "safety limit"],
        
        # Suppliers
        "supplier_id": ["vendor id", "seller id", "partner code"],
        "supplier_name": ["vendor name", "company name", "manufacturer"],
        "financial_health_score": ["d&b score", "credit rating", "financial stability"],
        "on_time_delivery_rate": ["otif", "service level", "delivery metrics"],
        "geopolitical_risk_index": ["geo risk", "country risk", "political stability"]
    }

    @classmethod
    def classify_and_map(cls, raw_headers: List[str], sample_rows: List[Dict[str, Any]] = None) -> Tuple[str, Dict[str, str]]:
        """
        Enterprise Semantic Mapping.
        1. Samples actual data rows to identify patterns (Semantic Reasoning).
        2. Simulates an LLM Agent call for zero-shot mapping of chaotic headers.
        """
        print(f"Executing Semantic Reasoning Agent on {len(raw_headers)} headers...")
        
        # Phase 1: Semantic Reasoning (LLM-Mock)
        # In a production environment, this payload would be sent to GPT-4o
        semantic_metadata = {}
        if sample_rows:
            for header in raw_headers:
                sample_values = [str(row.get(header, "")) for row in sample_rows[:5]]
                # Heuristic: If values look like Alphanumeric strings of length 4-8, it's likely an ID
                is_id_pattern = any(v.isalnum() and len(v) > 3 for v in sample_values)
                is_numeric = all(v.replace('.', '', 1).isdigit() for v in sample_values if v)
                semantic_metadata[header] = {"is_id": is_id_pattern, "is_numeric": is_numeric}

        # Phase 2: Global Mapping (Combining Synonyms + Semantic Context)
        global_mapping = {}
        for raw in raw_headers:
            raw_clean = raw.lower().strip()
            best_match = None
            highest_score = 0.0
            
            # --- LLM Zero-Shot Simulation ---
            # If the header is chaotic (e.g. "X_ID_99") but the data looks like a PO
            if semantic_metadata.get(raw, {}).get("is_id") and "id" in raw_clean:
                # Semantic bias towards IDs
                for target in ["po_number", "sku_id", "supplier_id", "node_id"]:
                    score = difflib.SequenceMatcher(None, raw_clean, target).ratio() + 0.3 # Boost
                    if score > highest_score:
                        highest_score = score
                        best_match = target
            
            # Standard Synonym Match
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

        # Phase 2: Classify the File Type based on the highest cluster of mapped fields
        schema_scores = {k: 0 for k in cls.SCHEMAS.keys()}
        
        for raw, mapped_target in global_mapping.items():
            if mapped_target:
                for schema_name, schema_fields in cls.SCHEMAS.items():
                    if mapped_target in schema_fields:
                        schema_scores[schema_name] += 1
        
        # Determine the winner
        detected_schema = max(schema_scores, key=schema_scores.get)
        
        # Fallback if the file is total garbage
        if schema_scores[detected_schema] == 0:
            return "UNKNOWN", {h: "UNMAPPED_DISCARD" for h in raw_headers}

        # Phase 3: Finalize mapping exclusively for the winning schema
        final_mapping = {}
        for raw, target in global_mapping.items():
            if target in cls.SCHEMAS[detected_schema]:
                final_mapping[raw] = target
            else:
                final_mapping[raw] = "UNMAPPED_DISCARD"
                
        return detected_schema, final_mapping
