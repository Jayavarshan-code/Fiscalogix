"""
AlertService — threshold-based detection with email + WhatsApp notifications.

Usage:
    alerts = AlertService.check(financial_data, tenant_id)
    # returns list of fired AlertEvent dicts

Email:
    Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_EMAIL env vars.
    If unset, alerts are logged only (no crash).

WhatsApp (Twilio):
    Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM env vars.
    TWILIO_WHATSAPP_FROM format: "whatsapp:+14155238886"  (Twilio sandbox number)
    ALERT_WHATSAPP_TO format:   "whatsapp:+919876543210" (recipient number)
    If unset, WhatsApp channel is silently skipped — no crash.

Thresholds (configurable via POST /alerts/configure, defaults below):
    cash_deficit_usd:     -10_000   total_revm below this → CASH_DEFICIT
    high_risk_shipments:  3         loss_shipments ≥ this → HIGH_RISK_CLUSTER
    confidence_floor:     0.60      global confidence below → LOW_CONFIDENCE
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Default thresholds ────────────────────────────────────────────────────────
_DEFAULT_THRESHOLDS = {
    "cash_deficit_usd":    -10_000,
    "high_risk_shipments": 3,
    "confidence_floor":    0.60,
}


class AlertService:

    @staticmethod
    def check(
        financial_data: Dict[str, Any],
        tenant_id: str,
        thresholds: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates the financial_data dict (from /financial-intelligence/)
        against alert thresholds. Returns a list of fired AlertEvent dicts.
        Each dict has: event_type, severity, message, value, threshold.
        """
        t = {**_DEFAULT_THRESHOLDS, **(thresholds or {})}
        alerts: List[Dict[str, Any]] = []

        summary    = financial_data.get("summary", {})
        confidence = financial_data.get("confidence", {}).get("global_score", 1.0)
        shocks     = financial_data.get("shocks", [])

        total_revm       = summary.get("total_revm", 0)
        loss_shipments   = summary.get("loss_shipments", 0)

        # 1. Cash deficit
        if total_revm < t["cash_deficit_usd"]:
            alerts.append({
                "event_type": "CASH_DEFICIT",
                "severity":   "critical",
                "message":    f"Portfolio ReVM is ${total_revm:,.0f} — below the ${t['cash_deficit_usd']:,.0f} threshold.",
                "value":      total_revm,
                "threshold":  t["cash_deficit_usd"],
            })

        # 2. High risk cluster
        if loss_shipments >= t["high_risk_shipments"]:
            alerts.append({
                "event_type": "HIGH_RISK_CLUSTER",
                "severity":   "warning",
                "message":    f"{loss_shipments} shipments at negative ReVM — review reroute options.",
                "value":      loss_shipments,
                "threshold":  t["high_risk_shipments"],
            })

        # 3. Low confidence
        if confidence < t["confidence_floor"]:
            alerts.append({
                "event_type": "LOW_CONFIDENCE",
                "severity":   "warning",
                "message":    f"System confidence is {confidence:.0%} — below the {t['confidence_floor']:.0%} floor. Check data quality.",
                "value":      confidence,
                "threshold":  t["confidence_floor"],
            })

        # 4. Active supply chain shocks
        for shock in shocks[:3]:
            alerts.append({
                "event_type": "SUPPLY_SHOCK",
                "severity":   "critical",
                "message":    shock.get("description", "Supply chain shock detected."),
                "value":      shock.get("severity_score", 0),
                "threshold":  0,
            })

        if alerts:
            logger.warning(f"[AlertService] {len(alerts)} alert(s) fired for tenant={tenant_id}")
            AlertService._send_email(alerts, tenant_id)
            AlertService._send_whatsapp(alerts, tenant_id)

        return alerts

    @staticmethod
    def _send_email(alerts: List[Dict[str, Any]], tenant_id: str) -> None:
        """
        Sends an email summary if SMTP env vars are configured.
        Silently skips if SMTP_HOST is not set.
        """
        smtp_host = os.environ.get("SMTP_HOST")
        if not smtp_host:
            return  # Email not configured — alerts are logged only

        try:
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))
            smtp_user = os.environ.get("SMTP_USER", "")
            smtp_pass = os.environ.get("SMTP_PASS", "")
            alert_to  = os.environ.get("ALERT_EMAIL", smtp_user)

            body_lines = [f"Fiscalogix Alert — {len(alerts)} event(s) for tenant: {tenant_id}\n"]
            for a in alerts:
                body_lines.append(f"[{a['severity'].upper()}] {a['event_type']}: {a['message']}")
            body_lines.append("\nLog in to Fiscalogix to review and take action.")

            msg = MIMEText("\n".join(body_lines))
            msg["Subject"] = f"[Fiscalogix] {len(alerts)} Alert(s) Require Attention"
            msg["From"]    = smtp_user
            msg["To"]      = alert_to

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                if smtp_port != 25:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info(f"[AlertService] Email sent to {alert_to} ({len(alerts)} alerts)")
        except Exception as e:
            logger.error(f"[AlertService] Email delivery failed (non-fatal): {e}")


    @staticmethod
    def _send_whatsapp(alerts: List[Dict[str, Any]], tenant_id: str) -> None:
        """
        Sends a WhatsApp message via Twilio if credentials are configured.
        Silently skips if TWILIO_ACCOUNT_SID is not set.

        Required env vars:
            TWILIO_ACCOUNT_SID     — Twilio account SID
            TWILIO_AUTH_TOKEN      — Twilio auth token
            TWILIO_WHATSAPP_FROM   — sender, e.g. "whatsapp:+14155238886"
            ALERT_WHATSAPP_TO      — recipient, e.g. "whatsapp:+919876543210"
        """
        sid   = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_ = os.environ.get("TWILIO_WHATSAPP_FROM")
        to_   = os.environ.get("ALERT_WHATSAPP_TO")

        if not all([sid, token, from_, to_]):
            return  # WhatsApp not configured — skip silently

        try:
            from twilio.rest import Client  # type: ignore
            client = Client(sid, token)

            # Build a concise WhatsApp message (max ~1600 chars, keep it short)
            critical = [a for a in alerts if a["severity"] == "critical"]
            warnings = [a for a in alerts if a["severity"] == "warning"]

            lines = [f"*Fiscalogix Alert* — {len(alerts)} event(s) for {tenant_id}"]
            for a in (critical + warnings)[:5]:   # cap at 5 to avoid spam
                icon = "🔴" if a["severity"] == "critical" else "🟡"
                lines.append(f"{icon} *{a['event_type']}*: {a['message']}")
            if len(alerts) > 5:
                lines.append(f"_...and {len(alerts) - 5} more. Log in to Fiscalogix._")

            body = "\n".join(lines)

            client.messages.create(body=body, from_=from_, to=to_)
            logger.info(f"[AlertService] WhatsApp sent to {to_} ({len(alerts)} alerts)")

        except ImportError:
            logger.warning(
                "[AlertService] twilio package not installed. "
                "Run: pip install twilio  to enable WhatsApp alerts."
            )
        except Exception as e:
            logger.error(f"[AlertService] WhatsApp delivery failed (non-fatal): {e}")


# ── Alert configuration endpoint (stored in Redis or module-level dict) ───────
_tenant_thresholds: Dict[str, Dict[str, Any]] = {}


def get_thresholds(tenant_id: str) -> Dict[str, Any]:
    return _tenant_thresholds.get(tenant_id, _DEFAULT_THRESHOLDS.copy())


def set_thresholds(tenant_id: str, thresholds: Dict[str, Any]) -> None:
    _tenant_thresholds[tenant_id] = {**_DEFAULT_THRESHOLDS, **thresholds}
    # Persist to Redis if available
    try:
        from app.Db.redis_client import cache
        import json
        cache.setex(f"alert_thresholds:{tenant_id}", 86400 * 7, json.dumps(_tenant_thresholds[tenant_id]))
    except Exception:
        pass
