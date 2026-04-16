# Fiscalogix

**Financial Intelligence Platform for Freight & Supply Chain**

Most freight companies run on gut feel and lagging reports. By the time the CFO sees a cash deficit, it happened three weeks ago. Fiscalogix changes that — it turns raw shipment data into forward-looking financial decisions, in real time.

---

## The Problem

A mid-size freight forwarder handling 500 shipments a month faces three invisible problems:

**Working Capital Trap** — You pay the carrier in 7 days. Your client pays in 45. That gap, multiplied across your portfolio, silently ties up crores in cash every month with nobody measuring it.

**Hidden Loss Shipments** — A shipment invoiced at ₹10L can still destroy value once you account for delay cost, FX erosion, SLA penalties, and capital tied up in transit. Standard accounting never shows you this.

**Invisible Concentration Risk** — 70% of volume through one port. Three clients representing 60% of revenue. These are existential exposures — invisible in a spreadsheet until the crisis hits.

Fiscalogix makes all three visible before they become a problem.

---

## What You Get

- **True shipment profitability** — every movement scored for its real financial cost, not just gross margin
- **Working capital gap analysis** — exactly how much cash is trapped and why, with a specific recommendation to close it
- **90-day cash flow forecast** — deficit warnings before they arrive, with scenario modelling
- **Concentration risk alerts** — automatic flags when client or port exposure crosses safe thresholds
- **India GST Intelligence** — GST working capital cost, IGST on imports, DGFT drawback across all 98 HS chapters
- **CFO-ready reports** — one-click Excel export with KPI summary, AR aging, and carrier gap analysis
- **WhatsApp & email alerts** — critical warnings delivered where your team actually reads them

---

## Getting Started

Upload a CSV of your last 3–6 months of shipments (7 columns minimum) and get a full financial intelligence report in under 2 minutes. No ERP integration required to start.

Minimum required columns:
```
AWB No | Consignee | Freight Charges | Carrier | Origin Port | Destination Port | Expected Delivery
```

---

## Deployment

Runs on Docker. Deployable to Railway or Render with the included configuration files.

**Required environment variables:**
```
ANTHROPIC_API_KEY=...
JWT_SECRET_KEY=...
DATABASE_URL=...
REDIS_URL=...
```

---

## For Freight Companies

**What you need to onboard:**
- A CSV of your last 3–6 months of shipments
- 30 minutes for an onboarding call

**What you get in the first session:**
- Full financial breakdown of every shipment in your upload
- Your true loss shipments — movements that looked profitable but weren't
- Your working capital gap — exactly how much cash is trapped and why
- Your concentration risk — which clients or ports are overexposed
- A 90-day cash flow forecast with deficit warnings

**Engagement model:**
- One-time financial intelligence audit (fixed fee)
- Monthly advisory with updated reports
- Full embedded deployment inside your operations

---

## Contact

Built by Varshan — supply chain finance, ML engineering, and financial systems.

- LinkedIn: [linkedin.com/in/varshan](#)
- Email: varshan@fiscalogix.com

> *"The best time to know your shipment is losing money is before it departs. The second best time is right now."*
