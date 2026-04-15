# Fiscalogix

**Financial Intelligence Platform for Freight & Supply Chain Operations**

Most freight companies run on gut feel and lagging reports. By the time the CFO sees a cash deficit, it happened three weeks ago. Fiscalogix changes that — it turns raw shipment data into forward-looking financial decisions, in real time, for every movement in your portfolio.

---

## The Problem We Solve

A mid-size freight forwarder handling 500 shipments a month is sitting on three invisible problems:

**1. The Working Capital Trap**
You pay the carrier within 7 days. Your client pays you in 45. That 38-day gap, multiplied across 500 shipments, silently ties up ₹2–4 crore in cash every single month. Nobody is measuring it.

**2. Hidden Loss Shipments**
A shipment that invoices ₹10L can still lose money once you account for delay cost, FX erosion, SLA penalties, and capital tied up in transit. Standard accounting only shows you gross margin. It never shows you which shipments are quietly destroying value.

**3. Risk You Can't See Coming**
70% of your volume flows through one port. Three clients represent 60% of your revenue. These are existential concentrations — but they're invisible in a spreadsheet until the crisis hits.

Fiscalogix makes all three visible before they become a problem.

---

## What It Does

### Financial Intelligence on Every Shipment
Every movement gets a complete financial breakdown — not just profit, but the full picture:

| Component | What It Measures |
|---|---|
| **REVM** (Risk-adjusted Enterprise Value Metric) | True profitability after all risk costs |
| **Delay Cost** | Capital locked in transit × your WACC × delay days |
| **FX Erosion** | Currency risk on both freight cost and outstanding receivables |
| **SLA Penalty** | Contractual OTIF fine exposure per shipment |
| **Risk Score** | ML-predicted probability of default or failure (0–100) |

### Working Capital Gap Analysis
Shows exactly how much cash is trapped between carrier payment obligations and client collections — per shipment, per client, and across the portfolio. Includes a specific recommendation to close the gap.

### Cash Flow Forecasting
Predicts your cash position day-by-day for the next 90 days. Flags deficit periods before they arrive. Models the impact of delays, demand drops, and supplier disruptions through scenario simulation.

### Concentration Risk Alerts
Automatically flags when a single client exceeds 30% of revenue or a single port handles over 50% of your volume. Quantifies the exact cash impact if that client delays payment by 30 days.

### CFO-Ready Reports
One-click Excel export with four sheets: KPI Summary, Shipment Detail, AR Aging (5 buckets with action items), and Carrier Gap Analysis. All amounts in INR.

### WhatsApp Alerts
Critical alerts — cash deficits, high-risk clusters, low confidence — delivered to your operations WhatsApp, not buried in an email inbox.

---

## How It Works

```
Your Data (CSV / ERP)
        ↓
  AI Field Mapper          — auto-detects your column names, no manual mapping
        ↓
  ML Inference Layer       — XGBoost risk model + GNN contagion detection
        ↓
  Financial Engine         — REVM, delay cost, FX, SLA, WACC per shipment
        ↓
  Executive Analytics      — cash flow, Monte Carlo VaR, scenario simulation
        ↓
  Freight Analytics        — carrier gap, concentration risk, AR aging
        ↓
  LLM Brief (Claude)       — plain-English CFO narrative with specific actions
        ↓
  Dashboard + Excel Export
```

No ERP integration required to start. Upload a 7-column CSV and get a full financial intelligence report in under 2 minutes.

---

## Getting Started in 3 Steps

### Step 1 — Upload Your Data
Download the freight template and fill in your shipment data:

```
GET /ingestion/freight_simple/template
```

Minimum required columns:
```
AWB No | Consignee | Freight Charges | Carrier | Origin Port | Destination Port | Expected Delivery
```
Everything else — WACC, cargo type, credit terms, risk parameters — is defaulted automatically.

### Step 2 — Run the Intelligence Pipeline
Upload the CSV and get your full financial intelligence report:

```
POST /ingestion/freight_simple
```

### Step 3 — Export Your Report
```
GET /reports/export/excel
```
Downloads a 4-sheet Excel workbook with KPI summary, shipment detail, AR aging, and carrier gap analysis — all in INR.

---

## Local Setup

**Requirements:** Docker, Docker Compose

```bash
git clone https://github.com/your-org/fiscalogix.git
cd fiscalogix

# Copy environment template
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Start everything
docker compose up --build
```

**Services started:**
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`
- PostgreSQL: port 5432
- Redis: port 6379

**First boot:** ML models are trained automatically on startup (~10–15 seconds on synthetic data, longer on your real data once uploaded).

---

## Configuring Alerts

### Email
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASS=your_app_password
ALERT_EMAIL=cfo@yourcompany.com
```

### WhatsApp (Twilio)
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
ALERT_WHATSAPP_TO=whatsapp:+919876543210
```

### Configure Thresholds
```
POST /alerts/configure
{
  "cash_deficit_usd": -50000,
  "high_risk_shipments": 5,
  "confidence_floor": 0.65,
  "alert_whatsapp_to": "whatsapp:+919876543210"
}
```

---

## Deployment

**One-command deploy to Render:**

```bash
# render.yaml is pre-configured
# Set these in the Render dashboard:
ANTHROPIC_API_KEY=...
JWT_SECRET_KEY=...
```

The `render.yaml` defines backend, Celery worker, Redis, and PostgreSQL. All wired together automatically.

---

## API Overview

| Endpoint | What It Does |
|---|---|
| `POST /ingestion/freight_simple` | Upload 7-column freight CSV |
| `GET /ingestion/freight_simple/template` | Download sample CSV |
| `GET /financial-intelligence/` | Full financial intelligence run |
| `GET /reports/export/excel` | 4-sheet Excel report in INR |
| `GET /reports/export/summary` | JSON summary for print/PDF |
| `POST /alerts/configure` | Set alert thresholds + WhatsApp number |
| `POST /alerts/check` | Manually trigger alert evaluation |
| `POST /ingestion/upload` | Full CSV + PDF contract upload |
| `GET /optimization/` | Route and cost optimisation recommendations |

Full interactive docs: `/docs` (Swagger UI)

---

## Intelligence Stack

Built for production-grade financial reasoning, not demo-grade dashboards.

**Machine Learning**
- XGBoost classifier for shipment risk scoring (trained per-tenant on boot)
- Graph Neural Network (GraphSAGE) for supply chain contagion detection
- Random Forest demand forecasting with industry-vertical seasonality profiles
- SHAP explainability on every risk prediction — every score is auditable

**Financial Models**
- Dynamic WACC: Damodaran industry benchmarks + live US Treasury rate adjustment
- Two-component FX model: shipment cost erosion + AR exposure erosion
- Monte Carlo VaR: 1,000-iteration stochastic simulation with log-normal costs, Poisson delays, and Pareto black-swan events
- OTIF SLA penalty model with grace periods and customer-tier penalty rates

**Optimisation**
- Mixed Integer Programming (MIP) route optimisation via Google OR-Tools
- Geopolitical route scoring with real-time contagion propagation
- Multi-echelon inventory optimisation

**AI Layer**
- Claude (Anthropic) for CFO narrative generation and agent orchestration
- RAG pipeline for contract and document intelligence
- LLM-negotiation agent for supplier term recommendations

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│         Dashboard · Ingestion Studio · Reports       │
└──────────────────────┬──────────────────────────────┘
                       │ REST / JWT
┌──────────────────────▼──────────────────────────────┐
│               FastAPI Backend                        │
│                                                      │
│  AdaptiveOrchestrator (8-stage pipeline)             │
│  ├── DataIngestion → ML Inference → CLV Calibration  │
│  ├── GST Compliance → Decision → Situation           │
│  ├── LLM Dispatch → Agent Execution → Persistence    │
│  └── CarrierGap + Concentration (freight analytics)  │
│                                                      │
│  Agents: Risk · Financial · Routing · Anomaly · CFO  │
└─────────┬──────────────────────────┬────────────────┘
          │                          │
┌─────────▼──────────┐  ┌───────────▼────────────────┐
│    PostgreSQL       │  │         Redis               │
│  Shipments · Orders │  │  WACC cache · FX rates      │
│  Risk scores · Logs │  │  Session · Alert thresholds │
└────────────────────┘  └────────────────────────────┘
          │
┌─────────▼──────────┐
│   Celery Worker     │
│  ETL · Model train  │
│  FX warm · Alerts   │
└────────────────────┘
```

---

## For Freight Companies

**What you need to onboard:**
- A CSV of your last 3–6 months of shipments (7 columns minimum)
- 30 minutes for an onboarding call

**What you get in the first session:**
- Full financial breakdown of every shipment in your upload
- Your true loss shipments — movements that looked profitable but weren't
- Your working capital gap — exactly how much cash is trapped and why
- Your concentration risk — which clients or ports are overexposed
- A 90-day cash flow forecast with deficit warnings

**Pricing model:**
- Engagement: fixed-fee financial intelligence audit (one-time)
- Ongoing: monthly advisory with updated reports
- Embedded: full deployment inside your operations

---

## For Innovation Teams & Corporate Ventures

Fiscalogix is a production-grade financial intelligence system built from first principles for the freight and logistics sector.

**Why this is not another dashboard:**

Most logistics analytics tools show you what happened. Fiscalogix tells you what it cost you in real financial terms and what to do about it. The REVM framework — which charges every shipment for its full risk cost including capital, FX, SLA, and delay — is a fundamentally different model from margin analysis or delay tracking.

**The market gap it addresses:**

SAP and Oracle tell you a shipment is delayed. They don't tell you that a 3-day delay on a Net-60 USD invoice on the EU-US route is costing you ₹1.2L in FX erosion alone, and that the same carrier has a 34% risk score based on your last 90 days of movements. That translation from operational data to financial consequence is exactly what Fiscalogix does.

**What makes it defensible:**

The REVM model is not a dashboard feature — it requires WACC, FX volatility, SLA contract terms, ML risk scoring, and cashflow simulation to compute correctly. Each component took months to validate against real freight data. An internal team starting from scratch would need 12–18 months to reach production quality on all components simultaneously.

**Current stage:**

Functional production system. 8-stage ML pipeline, 5 financial models, 3 optimisation engines, LLM agent layer, multi-tenant SaaS infrastructure. Looking for a design partner with real freight data to run the first paid pilot and demonstrate quantified financial outcomes at scale.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy |
| ML | XGBoost · scikit-learn · SHAP · PyTorch (GNN) |
| Optimisation | Google OR-Tools · SciPy |
| AI | Anthropic Claude · Sentence Transformers (RAG) |
| Frontend | React · TypeScript |
| Database | PostgreSQL + pgvector |
| Cache / Queue | Redis · Celery |
| Deploy | Docker · Render · Railway |

---

## Contact

Built by Varshan — supply chain finance, ML engineering, and financial systems.

For a pilot engagement or partnership conversation:

- LinkedIn: [linkedin.com/in/varshan](#)
- Email: varshan@fiscalogix.com

> *"The best time to know your shipment is losing money is before it departs. The second best time is right now."*
