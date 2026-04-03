"""
SLA Contract Text Extractor
A production-ready, rule-based NLP extraction engine that pulls penalty rates
from PDF contract text without requiring a live LLM API call.
Designed to be a reliable, deterministic fallback before fine-tuned models are deployed.
"""
import re
from typing import Dict, Any

class SLAContractExtractor:
    """
    Lightweight, deterministic NLP engine for extracting structured
    SLA penalty data from raw PDF contract text.
    No external API calls required — uses compiled regex patterns.
    """

    # Matches patterns like: "1.5% per day", "2 percent per 24 hours"
    PERCENTAGE_PENALTY_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(?:%|per\s*cent|percent)\s*(?:of\s+\w+\s+value\s+)?(?:per|every|each|a)\s*(?:day|24\s*hours?|diem)',
        re.IGNORECASE
    )

    # Matches patterns like: "$500 per day", "₹50,000 per 24 hours"
    FLAT_PENALTY_PATTERN = re.compile(
        r'(?:\$|₹|USD|INR|€)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:per|every|each|a)\s*(?:day|24\s*hours?)',
        re.IGNORECASE
    )

    # Detects force majeure clauses which nullify penalties
    FORCE_MAJEURE_PATTERN = re.compile(
        r'force\s+majeure|act\s+of\s+god|labor\s+strike|sovereign\s+customs|ICEGATE\s+failure|weather\s+anom',
        re.IGNORECASE
    )

    # Detects penalty caps
    CAP_PATTERN = re.compile(
        r'(?:not\s+exceed|capped\s+at|maximum\s+of|up\s+to)\s+(?:\$|₹|USD)?\s*(\d[\d,\.]+)',
        re.IGNORECASE
    )

    @classmethod
    def extract(cls, raw_text: str) -> Dict[str, Any]:
        """
        Main extraction method. Returns structured penalty data.
        Returns a default safe baseline if no clauses are found.
        """
        result = {
            "extracted_text": raw_text[:500],
            "penalty_type": "NONE_FOUND",
            "penalty_rate": None,
            "flat_fee_per_day": None,
            "force_majeure_applies": False,
            "cap_limit": None,
            "confidence": "LOW"
        }

        # 1. Check for Force Majeure (highest priority — nullifies penalties)
        if cls.FORCE_MAJEURE_PATTERN.search(raw_text):
            result["force_majeure_applies"] = True

        # 2. Extract percentage-based penalties
        pct_match = cls.PERCENTAGE_PENALTY_PATTERN.search(raw_text)
        if pct_match:
            result["penalty_type"] = "PERCENTAGE_PER_DAY"
            result["penalty_rate"] = float(pct_match.group(1)) / 100
            result["confidence"] = "HIGH"

        # 3. Extract flat fee penalties (overrides percentage if both present)
        flat_match = cls.FLAT_PENALTY_PATTERN.search(raw_text)
        if flat_match:
            result["penalty_type"] = "FLAT_FEE_PER_DAY"
            result["flat_fee_per_day"] = float(flat_match.group(1).replace(",", ""))
            result["confidence"] = "HIGH"

        # 4. Check for penalty caps
        cap_match = cls.CAP_PATTERN.search(raw_text)
        if cap_match:
            result["cap_limit"] = float(cap_match.group(1).replace(",", ""))

        return result
