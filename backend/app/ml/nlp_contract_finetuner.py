import os
import json
import random
import logging

logger = logging.getLogger(__name__)

class RobustTTFVFinetuner:
    """
    Fiscalogix TTFV Hardening: 150K Contract Trap Fine-Tuning.
    
    In a live 30-minute TTFV demo, if the AI parses "Force Majeure" as a penalty and 
    generates a false positive, trust is instantly broken and the sale is lost.
    
    This script generates 150,000 highly varied permutations of Legal Traps.
    It trains the model to act as a rigorous legal auditor, strictly optimizing for zero False Positives.
    """
    
    def __init__(self, dataset_path: str = "backend/data/robust_ttfv_150k.jsonl"):
        self.dataset_path = dataset_path
        
        # --- THE TRAP MATRIX (ENTERPRISE EDGE CASES) ---
        self.base_penalties = [
            "1.5% of freight value per day", 
            "$500 USD per 24 hours", 
            "₹50,000 per day", 
            "2% of invoice value"
        ]
        
        self.grace_periods = [
            "after a 48 hour grace period",
            "following 2 days of unhindered port operations",
            "excluding the first 24 hours post-arrival",
            "with a mutual 12-hour leeway"
        ]
        
        self.force_majeure_clauses = [
            "This penalty is nullified during acts of God or labor strikes.",
            "Exceptions apply for Force Majeure events as defined in Section 8.",
            "provided the delay is not caused by sovereign customs holds or ICEGATE failure.",
            "Demurrage shall not accrue during Level 3 or higher weather anomalies."
        ]
        
        self.conditional_reporting = [
            "provided the carrier submits written notice within 6 hours of the incident.",
            "if and only if the delay is logged in the EDI system before ETA.",
            "Notice must be served to the Charterer prior to port entry to waive fees."
        ]
        
        self.multi_tier_caps = [
            "Penalties shall not exceed 10% of total contracted freight.",
            "Capped at $50,000 USD total liability.",
            "Up to a maximum of 5 days of demurrage charges."
        ]

    def _generate_false_positive_trap(self) -> tuple:
        """Generates a clause that LOOKS like a penalty, but actually isn't (Triggered Force Majeure)"""
        p = random.choice(self.base_penalties)
        f = random.choice(self.force_majeure_clauses)
        text = f"Carrier is liable for {p} of delay. {f} (Context: Ship was delayed by a massive port strike)."
        label = "No penalty. Excluded by Force Majeure strike clause."
        return (text, label)

    def _generate_false_negative_trap(self) -> tuple:
        """Generates a clause where Force Majeure failed due to technicality (Conditional Reporting)"""
        p = random.choice(self.base_penalties)
        f = random.choice(self.force_majeure_clauses)
        c = random.choice(self.conditional_reporting)
        text = f"Carrier is liable for {p} of delay. {f} This waiver applies {c} (Context: Carrier failed to give notice, notifying at 12 hours)."
        label = "Penalty valid. Carrier failed to meet conditional reporting requirements despite Force Majeure."
        return (text, label)

    def _generate_grace_period_trap(self) -> tuple:
        """Generates a sub-grace period trap where AI might accidentally charge for Day 1"""
        p = random.choice(self.base_penalties)
        g = random.choice(self.grace_periods)
        text = f"Liquidated damages of {p} will be assessed {g}. (Context: Total delay was 20 hours)."
        label = "No penalty. Total delay falls within the allowable grace period."
        return (text, label)
        
    def _generate_cap_limit_trap(self) -> tuple:
        """Generates a scenario where AI might mathematically overcharge beyond a stated Cap."""
        p = random.choice(self.base_penalties)
        c = random.choice(self.multi_tier_caps)
        text = f"Demurrage applied at {p}. {c} (Context: Delay was 45 days, vastly exceeding normal limits)."
        label = f"Penalty valid but CAPPED. Calculate at {p} until limit: '{c}' is reached."
        return (text, label)

    def _generate_standard_breach(self) -> tuple:
        """Standard clear-cut breach for baseline calibration"""
        p = random.choice(self.base_penalties)
        text = f"A strict penalty of {p} applies for any delay beyond the contracted ETA. (Context: Delay was 3 days, no excuses)."
        label = f"Penalty valid. Calculate at {p} for 3 days."
        return (text, label)

    def build_dataset(self, num_samples: int = 150000) -> str:
        """
        Generates a JSONL fine-tuning dataset of contract clause trap permutations.
        All samples are written to self.dataset_path.
        Returns the output file path.
        """
        logger.info(f"Generating {num_samples} contract trap permutations → {self.dataset_path}")

        generators = [
            self._generate_false_positive_trap,
            self._generate_false_negative_trap,
            self._generate_grace_period_trap,
            self._generate_cap_limit_trap,
            self._generate_standard_breach,
        ]

        os.makedirs(os.path.dirname(self.dataset_path), exist_ok=True)

        written = 0
        with open(self.dataset_path, "w", encoding="utf-8") as f:
            for i in range(num_samples):
                clause_text, expected_outcome = generators[i % len(generators)]()
                prompt = (
                    "Extract Liquidated Damages logic and determine penalty validity.\n\n"
                    f"Clause & Context: {clause_text}"
                )
                record = {
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a deterministic legal auditor for Fiscalogix. "
                                "Extract penalties. Identify false positives caused by Force Majeure, "
                                "caps, or grace periods. Be precise."
                            ),
                        },
                        {"role": "user",      "content": prompt},
                        {"role": "assistant", "content": expected_outcome},
                    ]
                }
                f.write(json.dumps(record) + "\n")
                written += 1

                if written % 30000 == 0:
                    logger.info(f"  {written:,} samples written...")

        logger.info(f"Dataset complete — {written:,} samples written to {self.dataset_path}")
        return self.dataset_path

    def validate_on_holdout(self, holdout_samples: int = 500) -> dict:
        """
        Runs the SLAContractExtractor regex engine against synthetic holdout cases
        and measures false-positive / false-negative rates.

        This tests the deterministic extraction layer — not a trained model.
        For fine-tuned model evaluation, use your fine-tuning platform's eval pipeline.
        """
        from app.ml.sla_extractor import SLAContractExtractor

        generators = [
            (self._generate_false_positive_trap, "no_penalty"),
            (self._generate_grace_period_trap,   "no_penalty"),
            (self._generate_false_negative_trap, "penalty"),
            (self._generate_cap_limit_trap,      "penalty_with_cap"),
            (self._generate_standard_breach,     "penalty"),
        ]

        tp = fp = tn = fn = 0

        for i in range(holdout_samples):
            gen_func, expected_class = generators[i % len(generators)]
            clause_text, _ = gen_func()
            result = SLAContractExtractor.extract(clause_text)

            has_penalty = (
                result["penalty_rate"] is not None or result["flat_fee_per_day"] is not None
            )
            force_majeure_caught = result["force_majeure_applies"]

            if expected_class == "no_penalty":
                # Model should NOT charge a penalty (force majeure / grace catches it)
                if not has_penalty or force_majeure_caught:
                    tn += 1
                else:
                    fp += 1
            else:
                # Model should detect a penalty
                if has_penalty:
                    tp += 1
                else:
                    fn += 1

        total        = tp + fp + tn + fn
        precision    = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall       = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        fp_rate      = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        metrics = {
            "samples_evaluated": total,
            "true_positives":    tp,
            "false_positives":   fp,
            "true_negatives":    tn,
            "false_negatives":   fn,
            "precision":         round(precision, 4),
            "recall":            round(recall, 4),
            "false_positive_rate": round(fp_rate, 4),
        }

        logger.info(f"Holdout validation complete: {metrics}")
        return metrics

    # Keep backward-compatible alias
    def build_150k_dataset(self, num_samples: int = 150000) -> str:
        return self.build_dataset(num_samples=num_samples)

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150000
    finetuner = RobustTTFVFinetuner()
    path    = finetuner.build_dataset(num_samples=n)
    metrics = finetuner.validate_on_holdout(holdout_samples=500)
    print(f"\nDataset:  {path}")
    print(f"Holdout:  precision={metrics['precision']:.2%}  recall={metrics['recall']:.2%}  FP-rate={metrics['false_positive_rate']:.2%}")
