"""
Reports Router — PDF and Excel export for CFO/board use.

Endpoints:
  GET /reports/export/excel   — Downloads shipment financial data as .xlsx
                                 Sheets: KPI Summary | Shipment Detail |
                                         AR Aging | Carrier Gap Analysis
  GET /reports/export/summary — Returns JSON summary (for browser PDF print)

Currency: amounts are shown in the tenant's display currency (default INR).
No heavy PDF library — Excel via openpyxl, PDF via browser print dialog.
"""

import io
import logging
import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.financial_system.auth import get_current_user
from app.utils.currency import get_tenant_currency, convert_from_usd, symbol as currency_symbol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports & Export"])


@router.get("/export/excel")
def export_excel(current_user: dict = Depends(get_current_user)):
    """
    Exports the tenant's shipment financial data as an Excel workbook.
    Sheets: KPI Summary | Shipment Detail | AR Aging | Carrier Gap Analysis

    All monetary columns are shown in the tenant's display currency (default INR).
    """
    tenant_id = current_user.get("tenant_id", "default_tenant")
    currency  = get_tenant_currency(tenant_id)
    sym       = currency_symbol(tenant_id)

    def _to_currency(series):
        """Convert a USD pandas Series to tenant currency."""
        return series.apply(lambda v: round(convert_from_usd(float(v or 0), currency), 2))

    try:
        import pandas as pd
        from app.Db.connections import engine
        import sqlalchemy

        # ── Sheet 1: Shipment detail ──────────────────────────────────────────
        df_ships = pd.read_sql(
            sqlalchemy.text("""
                SELECT
                    s.shipment_id,
                    o.order_id,
                    COALESCE(o.customer_id, 'Unknown')                          AS client,
                    o.order_value,
                    s.shipment_cost,
                    s.delay_days,
                    s.carrier,
                    s.route,
                    s.origin_node,
                    s.destination_node,
                    COALESCE(o.credit_days, 30)                                 AS credit_days,
                    COALESCE(o.payment_delay_days, 0)                           AS payment_delay_days,
                    (COALESCE(sk.holding_cost_per_day,0) * s.delay_days)        AS holding_cost,
                    (s.delay_days * fp.penalty_rate * o.order_value)            AS delay_penalty,
                    (o.order_value * fp.wacc)                                   AS wacc_cost,
                    (o.order_value - s.shipment_cost
                       - (COALESCE(sk.holding_cost_per_day,0) * s.delay_days)
                       - (s.delay_days * fp.penalty_rate * o.order_value)
                       - (o.order_value * fp.wacc))                             AS revm,
                    s.created_at                                                AS shipment_date
                FROM orders o
                JOIN shipments s ON o.order_id = s.order_id AND s.tenant_id = o.tenant_id
                LEFT JOIN sku sk ON o.sku_id = sk.sku_id AND sk.tenant_id = o.tenant_id
                JOIN financial_parameters fp ON fp.tenant_id = o.tenant_id
                WHERE o.tenant_id = :tid
                ORDER BY s.created_at DESC
                LIMIT 5000
            """),
            engine,
            params={"tid": tenant_id},
        )

        # Convert monetary columns to tenant currency
        for col in ["order_value", "shipment_cost", "holding_cost",
                    "delay_penalty", "wacc_cost", "revm"]:
            if col in df_ships.columns:
                df_ships[col] = _to_currency(df_ships[col])
                df_ships.rename(columns={col: f"{col} ({sym})"}, inplace=True)

        # ── Sheet 2: KPI summary ──────────────────────────────────────────────
        rev_col  = f"order_value ({sym})"
        cost_col = f"shipment_cost ({sym})"
        revm_col = f"revm ({sym})"
        delay_col = "delay_days"

        summary = {
            "Metric": [
                f"Total Revenue ({currency})",
                f"Total Shipment Cost ({currency})",
                f"Total ReVM ({currency})",
                "Loss Shipments (negative ReVM)",
                "Average Delay (days)",
                "Export Generated (UTC)",
            ],
            "Value": [
                round(df_ships[rev_col].sum(), 2)       if rev_col   in df_ships.columns else 0,
                round(df_ships[cost_col].sum(), 2)      if cost_col  in df_ships.columns else 0,
                round(df_ships[revm_col].sum(), 2)      if revm_col  in df_ships.columns else 0,
                int((df_ships[revm_col] < 0).sum())     if revm_col  in df_ships.columns else 0,
                round(df_ships[delay_col].mean(), 1)    if delay_col in df_ships.columns else 0,
                datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            ],
        }
        df_summary = pd.DataFrame(summary)

        # ── Sheet 3: AR Aging ─────────────────────────────────────────────────
        # Buckets: current (not yet due), 1-30d, 31-60d, 61-90d, 90d+
        df_ar = _build_ar_aging(engine, tenant_id, currency, sym)

        # ── Sheet 4: Carrier Gap Analysis ────────────────────────────────────
        df_gap = _build_carrier_gap(engine, tenant_id, currency, sym)

        # ── Build workbook ────────────────────────────────────────────────────
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_summary.to_excel(writer, sheet_name="KPI Summary",       index=False)
            df_ships.to_excel(writer,   sheet_name="Shipment Detail",   index=False)
            df_ar.to_excel(writer,      sheet_name="AR Aging",          index=False)
            df_gap.to_excel(writer,     sheet_name="Carrier Gap",       index=False)

            # Auto-size columns for readability
            for sheet_name in writer.sheets:
                ws = writer.sheets[sheet_name]
                for col_cells in ws.columns:
                    max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
                    ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 40)

        output.seek(0)
        filename = f"fiscalogix_report_{tenant_id}_{datetime.date.today()}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error(f"Excel export failed for tenant={tenant_id}: {e}", exc_info=True)
        import pandas as pd
        output = io.BytesIO()
        pd.DataFrame({"Error": [str(e)]}).to_excel(output, index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="fiscalogix_error_report.xlsx"'},
        )


def _build_ar_aging(engine, tenant_id: str, currency: str, sym: str):
    """
    Builds the AR Aging sheet: outstanding receivables bucketed by overdue days.
    Buckets: Not Due | 1-30d | 31-60d | 61-90d | 90d+
    """
    import pandas as pd
    import sqlalchemy
    import datetime

    today = datetime.date.today()

    try:
        df = pd.read_sql(
            sqlalchemy.text("""
                SELECT
                    o.order_id,
                    COALESCE(o.customer_id, 'Unknown')  AS client,
                    o.order_value,
                    o.order_month,
                    COALESCE(o.credit_days, 30)         AS credit_days,
                    COALESCE(o.payment_delay_days, 0)   AS payment_delay_days,
                    s.delay_days
                FROM orders o
                JOIN shipments s ON o.order_id = s.order_id AND s.tenant_id = o.tenant_id
                WHERE o.tenant_id = :tid
                  AND o.status NOT IN ('paid', 'closed')
                LIMIT 2000
            """),
            engine,
            params={"tid": tenant_id},
        )
    except Exception:
        # status column may not exist on all schemas — fallback query
        df = pd.read_sql(
            sqlalchemy.text("""
                SELECT
                    o.order_id,
                    COALESCE(o.customer_id, 'Unknown')  AS client,
                    o.order_value,
                    o.order_month,
                    COALESCE(o.credit_days, 30)         AS credit_days,
                    0                                   AS payment_delay_days,
                    s.delay_days
                FROM orders o
                JOIN shipments s ON o.order_id = s.order_id AND s.tenant_id = o.tenant_id
                WHERE o.tenant_id = :tid
                LIMIT 2000
            """),
            engine,
            params={"tid": tenant_id},
        )

    if df.empty:
        return pd.DataFrame({
            "Bucket": ["Not Due", "1-30 days", "31-60 days", "61-90 days", "90+ days"],
            f"Amount ({sym})": [0] * 5,
            "Invoice Count": [0] * 5,
        })

    # Estimate days outstanding: order_month → approximate days since month start
    # In production this would use an actual invoice_date column
    def _days_overdue(row):
        try:
            invoice_month = int(row.get("order_month", today.month))
            invoice_year  = today.year if invoice_month <= today.month else today.year - 1
            invoice_date  = datetime.date(invoice_year, invoice_month, 1)
            due_date = invoice_date + datetime.timedelta(
                days=int(row.get("delay_days", 0)) + int(row.get("credit_days", 30))
            )
            return max(0, (today - due_date).days)
        except Exception:
            return 0

    df["days_overdue"] = df.apply(_days_overdue, axis=1)
    df["value_converted"] = df["order_value"].apply(
        lambda v: round(convert_from_usd(float(v or 0), currency), 2)
    )

    buckets = [
        ("Not Due",     lambda d: d == 0),
        ("1-30 days",   lambda d: 1 <= d <= 30),
        ("31-60 days",  lambda d: 31 <= d <= 60),
        ("61-90 days",  lambda d: 61 <= d <= 90),
        ("90+ days",    lambda d: d > 90),
    ]

    rows = []
    for label, cond in buckets:
        mask = df["days_overdue"].apply(cond)
        rows.append({
            "Bucket":           label,
            f"Amount ({sym})":  round(df.loc[mask, "value_converted"].sum(), 2),
            "Invoice Count":    int(mask.sum()),
            "Action":           _ar_action(label),
        })

    return pd.DataFrame(rows)


def _ar_action(bucket: str) -> str:
    return {
        "Not Due":    "Monitor — within payment terms",
        "1-30 days":  "Send friendly payment reminder",
        "31-60 days": "Escalate to account manager",
        "61-90 days": "Issue formal demand notice",
        "90+ days":   "Legal / collections — consider write-off provision",
    }.get(bucket, "")


def _build_carrier_gap(engine, tenant_id: str, currency: str, sym: str):
    """
    Builds the Carrier Gap sheet: working capital tied up between
    carrier payment due date and client collection date per shipment.
    """
    import pandas as pd
    import sqlalchemy
    import datetime

    today = datetime.date.today()

    try:
        df = pd.read_sql(
            sqlalchemy.text("""
                SELECT
                    s.shipment_id,
                    COALESCE(o.customer_id, 'Unknown')          AS client,
                    s.carrier,
                    o.order_value,
                    COALESCE(s.shipment_cost, o.order_value * 0.15) AS carrier_cost,
                    COALESCE(o.credit_days, 30)                 AS credit_days,
                    COALESCE(s.delay_days, 0)                   AS delay_days,
                    COALESCE(o.payment_delay_days, 0)           AS payment_delay_days,
                    COALESCE(s.supplier_payment_terms, 7)       AS carrier_payment_days
                FROM orders o
                JOIN shipments s ON o.order_id = s.order_id AND s.tenant_id = o.tenant_id
                WHERE o.tenant_id = :tid
                ORDER BY s.created_at DESC
                LIMIT 1000
            """),
            engine,
            params={"tid": tenant_id},
        )
    except Exception as e:
        logger.warning(f"Carrier gap query failed: {e}")
        return pd.DataFrame({"Note": ["Carrier gap data unavailable — check shipments table schema."]})

    if df.empty:
        return pd.DataFrame({"Note": ["No shipment data found."]})

    rows = []
    for _, r in df.iterrows():
        carrier_due_days = int(r.get("carrier_payment_days", 7))
        inflow_days      = int(r.get("delay_days", 0)) + int(r.get("credit_days", 30)) + int(r.get("payment_delay_days", 0))
        gap_days         = max(0, inflow_days - carrier_due_days)
        carrier_cost_raw = float(r.get("carrier_cost") or float(r.get("order_value", 0)) * 0.15)

        rows.append({
            "Shipment ID":             r.get("shipment_id", ""),
            "Client":                  r.get("client", "Unknown"),
            "Carrier":                 r.get("carrier", "Unknown"),
            f"Carrier Cost ({sym})":   round(convert_from_usd(carrier_cost_raw, currency), 2),
            f"Invoice Value ({sym})":  round(convert_from_usd(float(r.get("order_value", 0)), currency), 2),
            "Carrier Payment Due (days)": carrier_due_days,
            "Client Payment Due (days)":  inflow_days,
            "Gap (days)":              gap_days,
            f"Cash Tied Up ({sym})":   round(convert_from_usd(carrier_cost_raw, currency), 2),
            "Risk":                    "HIGH" if gap_days > 45 else ("MEDIUM" if gap_days > 21 else "LOW"),
        })

    df_out = pd.DataFrame(rows)
    df_out.sort_values("Gap (days)", ascending=False, inplace=True)
    return df_out


@router.get("/export/summary")
def export_summary(current_user: dict = Depends(get_current_user)):
    """
    Returns a structured JSON summary for the browser to render as a
    print-friendly PDF (frontend calls window.print() on this data).
    """
    tenant_id = current_user.get("tenant_id", "default_tenant")

    try:
        import pandas as pd
        from app.Db.connections import engine
        import sqlalchemy

        row = pd.read_sql(
            sqlalchemy.text("""
                SELECT
                    COUNT(*)                                                     AS shipment_count,
                    COALESCE(SUM(o.order_value), 0)                             AS total_revenue,
                    COALESCE(SUM(s.shipment_cost), 0)                           AS total_cost,
                    COALESCE(AVG(s.delay_days), 0)                              AS avg_delay,
                    COALESCE(SUM(
                        o.order_value - s.shipment_cost
                        - (COALESCE(sk.holding_cost_per_day,0) * s.delay_days)
                        - (s.delay_days * fp.penalty_rate * o.order_value)
                        - (o.order_value * fp.wacc)
                    ), 0)                                                        AS total_revm
                FROM orders o
                JOIN shipments s ON o.order_id = s.order_id AND s.tenant_id = o.tenant_id
                LEFT JOIN sku sk ON o.sku_id = sk.sku_id AND sk.tenant_id = o.tenant_id
                JOIN financial_parameters fp ON fp.tenant_id = o.tenant_id
                WHERE o.tenant_id = :tid
            """),
            engine,
            params={"tid": tenant_id},
        ).iloc[0]

        return {
            "tenant_id":       tenant_id,
            "generated_at":    datetime.datetime.utcnow().isoformat(),
            "shipment_count":  int(row["shipment_count"]),
            "total_revenue":   round(float(row["total_revenue"]), 2),
            "total_cost":      round(float(row["total_cost"]), 2),
            "avg_delay_days":  round(float(row["avg_delay"]), 1),
            "total_revm":      round(float(row["total_revm"]), 2),
        }

    except Exception as e:
        logger.error(f"Summary export failed for tenant={tenant_id}: {e}")
        return {"error": str(e), "tenant_id": tenant_id}
