"""
CashflowDecisionSupport — generates specific operational actions from cashflow shocks.

P1-D FIX: root_causes parameter was accepted but never read.
WHAT WAS WRONG:
  compute(self, shocks, root_causes) took root_causes as a parameter but the method
  body never referenced it. All three shock types produced the same 3 generic actions
  regardless of what caused the shock:
    - CASH_DEFICIT → always "EXPEDITE RECEIVABLES OR FACTOR INVOICES"
    - LOW_LIQUIDITY → always "DELAY NON-CRITICAL PAYABLES"
    - SUDDEN_DROP   → always "REDUCE INVENTORY EXPOSURE"

  This is useless in practice: if the root cause is "carrier delay on EU→HUB_A
  caused by strike", factoring invoices is the wrong action.
  The right action is "activate contingency carrier contract" or "reroute via CAPE".

FIX: root_causes now drives a secondary action layer on top of the generic shock
  response. If a specific root cause is known, a targeted operational action is
  prepended to the generic financial recommendation.
"""

from typing import List, Dict, Any


# Root cause → targeted action mapping
# Keys are substrings matched against the root_cause string (case-insensitive)
_ROOT_CAUSE_ACTIONS = {
    "carrier":       ("Operational", "ACTIVATE CONTINGENCY CARRIER CONTRACT — switch carrier on affected routes"),
    "strike":        ("Operational", "REROUTE VIA ALTERNATE CORRIDOR — bypass strike-affected lane immediately"),
    "delay":         ("Operational", "EXPEDITE PRIORITY SHIPMENTS — upgrade mode for high-ReVM shipments"),
    "congestion":    ("Operational", "DIVERT THROUGH ALTERNATE PORT — avoid congested node"),
    "fx":            ("Financial",   "HEDGE FX EXPOSURE — execute forward contract to lock current rate"),
    "demand":        ("Commercial",  "ACCELERATE DEMAND PULL — run incentive program with key accounts"),
    "inventory":     ("Operational", "TRIGGER SAFETY STOCK REPLENISHMENT — reorder before stockout threshold"),
    "supplier":      ("Procurement", "DUAL-SOURCE CRITICAL SKUs — qualify alternate supplier immediately"),
    "payment":       ("Financial",   "ACCELERATE COLLECTIONS — assign AR team to overdue accounts"),
    "customer":      ("Commercial",  "EXECUTIVE ACCOUNT REVIEW — CFO outreach to at-risk enterprise customers"),
}


class CashflowDecisionSupport:
    """
    Translates predicted cashflow shocks and their root causes into
    specific, prioritized operational decisions.
    """

    def compute(
        self,
        shocks: List[Dict[str, Any]],
        root_causes: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Args:
            shocks:      List of cashflow shock dicts from the cashflow predictor.
                         Each has: {type, date, severity, ...}
            root_causes: List of strings describing the drivers of the shocks.
                         E.g. ["carrier delay on EU→HUB_A", "FX volatility spike"]
                         Now actually used — drives targeted operational actions.
        """
        recommendations = []

        # P1-D FIX: Build root-cause action lookup from the provided list
        targeted_actions = self._extract_targeted_actions(root_causes)

        for shock in shocks:
            shock_type = shock.get("type", "")
            shock_date = shock.get("date", "")
            severity   = shock.get("severity", 0)

            # Format severity for human readability
            if isinstance(severity, (int, float)):
                severity_str = f"${severity:,.0f}"
            else:
                severity_str = str(severity)

            # Generic financial response (unchanged baseline)
            if shock_type == "CASH_DEFICIT":
                generic = {
                    "shock_date":   shock_date,
                    "action_type":  "Financial",
                    "action":       "EXPEDITE RECEIVABLES OR FACTOR INVOICES",
                    "reason":       f"Critical cash deficit of {severity_str} mathematically predicted.",
                    "priority":     "CRITICAL",
                }
            elif shock_type == "LOW_LIQUIDITY":
                generic = {
                    "shock_date":   shock_date,
                    "action_type":  "Operational",
                    "action":       "DELAY NON-CRITICAL PAYABLES",
                    "reason":       f"Liquidity dips {severity_str} below safety threshold.",
                    "priority":     "HIGH",
                }
            elif shock_type == "SUDDEN_DROP":
                generic = {
                    "shock_date":   shock_date,
                    "action_type":  "Strategic",
                    "action":       "REDUCE INVENTORY EXPOSURE",
                    "reason":       f"Sudden cash drain of {severity_str} identified.",
                    "priority":     "HIGH",
                }
            else:
                generic = {
                    "shock_date":   shock_date,
                    "action_type":  "Monitor",
                    "action":       "REVIEW CASHFLOW POSITION",
                    "reason":       f"Unclassified shock of {severity_str} detected.",
                    "priority":     "MEDIUM",
                }

            recommendations.append(generic)

            # P1-D FIX: Prepend targeted action if root cause is known
            for action_type, action_text in targeted_actions:
                # P3-4 FIX: root_causes may be list[dict]; extract text before joining
                _rc_texts = [
                    rc.get("reason_text", rc.get("reason", str(rc))) if isinstance(rc, dict) else str(rc)
                    for rc in root_causes[:2]
                ]
                targeted_rec = {
                    "shock_date":   shock_date,
                    "action_type":  action_type,
                    "action":       action_text,
                    "reason":       f"Root cause analysis: {', '.join(_rc_texts)}",
                    "priority":     "CRITICAL",   # targeted actions are always high priority
                    "root_cause_driven": True,
                }
                recommendations.append(targeted_rec)

        # Deduplicate on (date, action) — same as before
        seen = set()
        unique = []
        for r in recommendations:
            key = (r["shock_date"], r["action"])
            if key not in seen:
                seen.add(key)
                unique.append(r)

        # Sort: root-cause-driven first, then by priority, then by date
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        unique.sort(key=lambda r: (
            0 if r.get("root_cause_driven") else 1,
            priority_order.get(r.get("priority", "MEDIUM"), 2),
            r.get("shock_date", ""),
        ))

        return unique

    def _extract_targeted_actions(
        self, root_causes: List
    ) -> List[tuple]:
        """
        Matches root cause strings against the action registry.
        Accepts list[str] OR list[dict] (from RootCauseEngine — P3-4 fix).
        Returns list of (action_type, action_text) tuples — one per matched cause.
        Each cause can trigger at most one targeted action (first match wins).
        """
        if not root_causes:
            return []

        triggered = []
        seen_actions = set()

        for cause in root_causes:
            # P3-4 FIX: RootCauseEngine returns list[dict], not list[str].
            # Calling .lower() on a dict raised AttributeError silently and suppressed
            # ALL targeted actions. Now extract the text field from dicts gracefully.
            if isinstance(cause, dict):
                cause_str = cause.get("reason_text", cause.get("reason", ""))
            else:
                cause_str = str(cause)
            cause_lower = cause_str.lower()
            for keyword, (action_type, action_text) in _ROOT_CAUSE_ACTIONS.items():
                if keyword in cause_lower and action_text not in seen_actions:
                    triggered.append((action_type, action_text))
                    seen_actions.add(action_text)
                    break   # one match per cause

        return triggered
