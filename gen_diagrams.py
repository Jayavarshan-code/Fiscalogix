#!/usr/bin/env python3
"""Fiscalogix – Colorful Architecture Diagrams PDF (12 pages)."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages

OUTPUT = r"c:\Users\varshan\fiscalogix\fiscalogix_architecture_diagrams.pdf"

BG = "#0F172A"; PANEL = "#1E293B"; DGRAY = "#475569"; LGRAY = "#CBD5E1"; WHITE = "#F1F5F9"
C = {
    "client":"#3B82F6","api":"#7C3AED","ml":"#059669","data":"#D97706",
    "ext":"#DC2626","task":"#EA580C","auth":"#4F46E5","spatial":"#0891B2",
    "erp":"#DB2777","rag":"#65A30D","deploy":"#64748B","fin":"#0D9488",
    "risk":"#B45309","agent":"#6D28D9","gbm":"#0369A1","yellow":"#FDE68A",
}

def _fig(title, w=20, h=13):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0,0.945),1,0.055,boxstyle="square,pad=0",fc=PANEL,ec="none",zorder=1))
    ax.add_patch(FancyBboxPatch((0,0.942),1,0.006,boxstyle="square,pad=0",fc=C["api"],ec="none",zorder=2))
    ax.text(0.5,0.972,title,ha="center",va="center",fontsize=14,color=WHITE,fontweight="bold",zorder=3)
    ax.text(0.01,0.972,"FISCALOGIX",ha="left",va="center",fontsize=8,color=C["api"],fontweight="bold",zorder=3)
    return fig, ax

def box(ax, x, y, w, h, fc, text, fs=8, tc=WHITE, lw=1, alpha=1.0):
    ax.add_patch(FancyBboxPatch((x+.002,y+.002),w-.004,h-.004,
        boxstyle="round,pad=0.005",fc=fc,ec=WHITE,linewidth=lw,alpha=alpha,zorder=3))
    lines = text.split("\n"); step = min(0.018, h/(len(lines)+1))
    sy = y+h/2+(len(lines)-1)*step/2
    for i,l in enumerate(lines):
        ax.text(x+w/2,sy-i*step,l,ha="center",va="center",fontsize=fs,
                color=tc,fontweight="bold" if i==0 else "normal",zorder=4)

def sec(ax, x, y, w, h, fc, title=""):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.01",
        fc=fc,ec=fc,linewidth=2,alpha=0.12,zorder=1))
    ax.add_patch(FancyBboxPatch((x+.003,y+.003),w-.006,h-.006,boxstyle="round,pad=0.007",
        fc="none",ec=fc,linewidth=1,linestyle="--",alpha=0.45,zorder=2))
    if title: ax.text(x+.008,y+h-.008,title,ha="left",va="top",fontsize=7,color=fc,fontweight="bold",zorder=3)

def arr(ax, x1, y1, x2, y2, fc=WHITE, lw=1.5, rad=0):
    ax.annotate("",xy=(x2,y2),xytext=(x1,y1),
        arrowprops=dict(arrowstyle="->",color=fc,lw=lw,
                        connectionstyle=f"arc3,rad={rad}"),zorder=5)

def lbl(ax, x, y, t, fs=7.5, fc=LGRAY, ha="center"):
    ax.text(x,y,t,ha=ha,va="center",fontsize=fs,color=fc,zorder=4)

# ── DIAGRAM 1 ─────────────────────────────────────────────────────────────────
def d1():
    fig,ax = _fig("1 · High-Level System Architecture")
    # CLIENT
    sec(ax,.01,.79,.98,.14,C["client"],"CLIENT LAYER  (React + Vite · axios · React Query)")
    for label,x in [("Dashboard\nKPI / Risk",.03),("Intelligence\nMatrix H3",.21),
                    ("Ingestion\nStudio",.39),("Realtime Hub\nWebSocket",.57),("Cashflow\nTimeline",.75)]:
        box(ax,x,.81,.17,.10,C["client"],label,fs=8)
    arr(ax,.50,.79,.50,.775); lbl(ax,.54,.782,"HTTPS + JWT",fs=7)
    # API
    sec(ax,.01,.645,.98,.135,C["api"],"API GATEWAY LAYER  (FastAPI · uvicorn · SlowAPI rate-limiting · CORS middleware)")
    for label,x in [("/auth/* /register",.03),("/financial-\nintelligence",.19),
                    ("/api/v1/* predict\noptimize docs",.35),("/ingestion/*\n/data-grid",.51),
                    ("/execution/*\n/sla/* /gst/*",.67),("/reports/*\n/alerts/* /admin",.83)]:
        box(ax,x,.665,.155,.10,C["api"],label,fs=7.5)
    arr(ax,.50,.645,.50,.63)
    # CORE (3 panels)
    sec(ax,.01,.395,.44,.225,C["fin"],"FINANCIAL INTELLIGENCE ENGINE")
    box(ax,.02,.505,.20,.10,C["fin"],"AdaptiveOrchestrator\n8-Stage Pipeline",fs=8)
    box(ax,.02,.41,.095,.09,C["ml"],"DelayModel\nXGBoost",fs=7.5)
    box(ax,.12,.41,.095,.09,C["risk"],"RiskEngine\n3-Tier",fs=7.5)
    box(ax,.225,.41,.095,.09,C["spatial"],"FeatureBuilder\nSpatialInject",fs=7.5)
    box(ax,.325,.41,.11,.09,C["agent"],"5 Agents\nDispatch",fs=7.5)
    box(ax,.225,.505,.21,.10,C["fin"],"CashflowPredictor\nMonteCarloEngine",fs=8)

    sec(ax,.46,.395,.25,.225,C["task"],"ASYNC TASKS  (Celery + Beat)")
    box(ax,.47,.545,.115,.06,C["task"],"warm_fx_cache\n55 min",fs=7.5)
    box(ax,.595,.545,.105,.06,C["task"],"warm_spatial\n60 min",fs=7.5)
    box(ax,.47,.475,.115,.065,C["ml"],"retrain_ml\nSunday 02:00",fs=7.5)
    box(ax,.595,.475,.105,.065,C["rag"],"refresh_rag\nnightly",fs=7.5)
    box(ax,.47,.41,.235,.055,DGRAY,"process_csv · etl_pipeline  (API-triggered)",fs=7.5)

    sec(ax,.72,.395,.27,.225,C["auth"],"AUTH + GOVERNANCE")
    box(ax,.73,.545,.12,.06,C["auth"],"JWT Auth\nPermissionEngine",fs=7.5)
    box(ax,.86,.545,.115,.06,C["auth"],"RBAC\nHITL Gate",fs=7.5)
    box(ax,.73,.475,.245,.065,C["fin"],"AuditLogger · RevmSnapshot",fs=7.5)
    box(ax,.73,.41,.245,.055,C["rag"],"RAG Pipeline · LLMGateway",fs=7.5)

    arr(ax,.50,.395,.50,.38)
    # DATA
    sec(ax,.01,.215,.98,.16,C["data"],"DATA LAYER")
    box(ax,.03,.23,.22,.13,C["data"],"PostgreSQL 15\ndw_shipment_facts\nsla_contracts\nml_model_versions\nexternal_spatial_events",fs=7.5)
    box(ax,.28,.23,.22,.13,"#991B1B","Redis 7\nfx_cache (55m TTL)\nwacc_cache (6h TTL)\nspatial_events (5m)\nCelery broker",fs=7.5)
    box(ax,.53,.23,.22,.13,"#1E3A5F","Neo4j\nSupply chain graph\ncarrier/route nodes\npath analysis",fs=7.5)
    box(ax,.78,.23,.20,.13,"#14532D","ML Models (disk)\ndelay_model.pkl\nrisk_pipeline.pkl\nrisk_fallback.pkl\ndemand_model.pkl",fs=7.5)
    arr(ax,.50,.215,.50,.20)
    # EXTERNAL
    sec(ax,.01,.03,.98,.16,C["ext"],"EXTERNAL INTEGRATIONS")
    for label,x,c in [("open.er-api.com\nFX Rates",.03,C["ext"]),
                      ("OpenWeatherMap\nWeather Events",.19,"#B45309"),
                      ("ACLED API\nGeopolitical",.35,"#7C2D12"),
                      ("MarineTraffic\nPort Congestion",.51,"#0C4A6E"),
                      ("FRED API\nUS Treasury",.67,"#1A1A2E"),
                      ("NetSuite / SAP\nERP OAuth2",.83,C["erp"])]:
        box(ax,x,.06,.14,.08,c,label,fs=7.5)
    return fig

# ── DIAGRAM 2 ─────────────────────────────────────────────────────────────────
def d2():
    fig,ax = _fig("2 · Financial Intelligence Pipeline — 8-Stage Data Flow",w=20,h=14)
    stage_colors=[C["client"],C["api"],C["fin"],C["auth"],C["spatial"],C["ml"],C["agent"],C["data"]]
    stages=[
        ("Stage 1 · DataIngestion","Validate required fields · Resolve tenant_id from JWT\nLoad ERP context (NetSuite/SAP if connected) · Extract claims"),
        ("Stage 2 · MLInference","FeatureBuilder.build(row, spatial_severity)  ←  SpatialRiskInjector\nDelayModel → XGBoost Regressor (delay_days)\nRiskEngine → XGBoost → GBM → Logit  (3-tier)\nDemandModel → RandomForest  ·  FXRiskModel → Redis cache"),
        ("Stage 3 · CLVCalibration","CLVCalibrator: tier_multiplier (1.5×–8.0×)\nPayment health factor (credit term decay 0.70–1.0)\nMargin factor (0.5–2.0) → CLV proxy score"),
        ("Stage 4 · Decision","WACC-adjusted ROI · SLA penalty injection\nRisk threshold check vs user risk appetite slider\nHITL gate: risk > threshold + !can_approve → approval queue"),
        ("Stage 5 · SituationAssessment","MonteCarloEngine.simulate(scenarios=1000)\nConfidenceEngine.score(predictions, variance)\nConcentrationEngine (supplier/carrier) · LiquidityEngine.assess()"),
        ("Stage 6 · DispatchPlanning","ActionGenerator.generate(decision, situation)\nActionSimulator.simulate(actions)\nGeopoliticalRouteOptimizer · CashflowPredictor.project_90d()"),
        ("Stage 7 · AgentExecution","FinancialAgent → ROI analysis\nRiskAgent → mitigation  ·  AnomalyAgent → outlier flags\nRoutingAgent → carrier routing  ·  ExecutiveAgent → LLM narrative"),
        ("Stage 8 · Persistence","AuditLogger.log(decision, user, timestamp, permissions)\nRevmSnapshotLogger.persist()  ·  ERPWriteback.push()\nAlertService.evaluate(thresholds) → notifications"),
    ]
    box(ax,.02,.915,.96,.022,C["client"],"INPUT  ·  POST /financial-intelligence  ·  {route, carrier, order_value, total_cost, credit_days, cargo_type, industry_vertical, ...}",fs=8)
    h_each=.097; gap=.011; start_y=.895
    for i,(title,detail) in enumerate(stages):
        y=start_y-i*(h_each+gap)
        box(ax,.02,y,.46,h_each,stage_colors[i],title,fs=9)
        box(ax,.51,y,.47,h_each,PANEL,detail,fs=8,tc=LGRAY,lw=0)
        if i<7:
            ax.plot([.245,.245],[y,y-gap],color=stage_colors[i+1],lw=2,zorder=5)
            arr(ax,.245,y-gap+.001,.245,y-gap-0,fc=stage_colors[i+1])
        ax.plot([.48,.51],[y+h_each/2,y+h_each/2],color=DGRAY,lw=1,linestyle="--",zorder=4)
    out_y=start_y-8*(h_each+gap)+gap
    box(ax,.02,out_y-.028,.96,.026,C["rag"],
        "RESPONSE · {predictions, risk_score, decision, confidence, actions, narrative, cashflow_90d, requires_approval}",fs=8)
    lbl(ax,.245,.925,"PIPELINE STAGES",fs=8.5,fc=WHITE)
    lbl(ax,.745,.925,"IMPLEMENTATION DETAIL",fs=8.5,fc=WHITE)
    return fig

# ── DIAGRAM 3 ─────────────────────────────────────────────────────────────────
def d3():
    fig,ax = _fig("3 · Risk Scoring — 3-Tier Inference Architecture",w=20,h=14)
    box(ax,.22,.905,.56,.038,C["client"],
        "INPUT · {route, carrier, order_value, total_cost, credit_days, cargo_type, industry_vertical, delay_days}",fs=8)
    arr(ax,.50,.905,.50,.888)
    # STEP 0
    sec(ax,.03,.735,.94,.148,C["spatial"],"STEP 0 · Spatial Enrichment  (spatial_risk_injector.py)")
    box(ax,.05,.79,.24,.075,C["spatial"],"SpatialRiskInjector\n.get_route_severity(route,\n  cargo_type)",fs=8.5)
    box(ax,.05,.755,.24,.032,"#0C4A6E","Redis cache (TTL 5 min)",fs=8,tc=LGRAY)
    arr(ax,.17,.79,.17,.787)
    box(ax,.32,.775,.63,.075,"#164E63",
        "_route_to_h3_cells('CN-EU_SUEZ')  tokens: [CN, EU, SUEZ]\n"
        "CN→H3(31.23,121.47,r3)  EU→H3(51.90,4.48,r3)  SUEZ→H3(29.97,32.55,r3)\n"
        "for each event: contribution = severity × 0.55^h3_distance  (MAX_HOPS=3)\n"
        "max_severity = max(all contributions across all route cells)",
        fs=8,tc=LGRAY,lw=0)
    arr(ax,.29,.8275,.32,.8275)
    box(ax,.32,.745,.26,.026,C["spatial"],"→ spatial_severity: float [0.0 – 1.0]",fs=8.5)
    arr(ax,.50,.735,.50,.718)
    # STEP 0b
    sec(ax,.03,.575,.94,.138,C["ml"],"STEP 0b · Feature Engineering  (feature_builder.py)")
    box(ax,.05,.595,.35,.105,"#064E3B",
        "Derived Scalars\ncost_ratio = total_cost / order_value\nmargin_pct = margin / order_value\n"
        "carrier_reliability (CARRIER_RELIABILITY_REGISTRY)\nroute_complexity (1.0–4.0)  ·  holding_rate (cargo type)\nseasonality_idx (industry_vertical × month)",
        fs=8,tc=LGRAY,lw=0)
    box(ax,.43,.595,.52,.105,"#14532D",
        "Interaction Terms (9 features)\ncost_x_delay  ·  carrier_x_route  ·  spatial_x_route  ·  spatial_x_cargo\n"
        "margin_x_spatial  ·  seasonal_x_cargo  ·  credit_delay_exposure\n"
        "margin_compression = margin_pct / max(cost_ratio, 0.01)\n"
        "risk_pressure = cost_ratio × carrier_risk × route_complexity  ← highest-signal 3-way term",
        fs=8,tc=LGRAY,lw=0)
    arr(ax,.50,.575,.50,.558)
    # 3 TIERS
    ty=.37; th=.175
    sec(ax,.03,ty,.29,th,C["ml"],"TIER 1 · XGBoost  (Primary)")
    box(ax,.05,ty+.10,.25,.062,C["ml"],"XGBClassifier\nn_est=150 · max_depth=4\nscale_pos_weight=auto\neval_metric=logloss",fs=8)
    box(ax,.05,ty+.055,.25,.040,"#065F46","ColumnTransformer\n(passthrough + OHE route/carrier)",fs=8)
    box(ax,.05,ty+.006,.25,.044,C["spatial"],"spatial_lift = severity × 0.25 × (1 - base_prob)\nfinal = base_prob + lift",fs=8,tc=LGRAY,lw=0)

    sec(ax,.35,ty,.30,th,C["gbm"],"TIER 2 · GBM Fallback")
    box(ax,.37,ty+.10,.26,.062,C["gbm"],"GradientBoostingClassifier\nn_est=120 · max_depth=4\nsubsample=0.8\nmin_samples_leaf=20",fs=8)
    box(ax,.37,ty+.055,.26,.040,"#0C4A6E","risk_fallback.pkl\n23-col numeric input (no OHE)",fs=8)
    box(ax,.37,ty+.006,.26,.044,"#082F49","Loads: risk_fallback_columns.pkl\nAligns feature order at runtime",fs=8,tc=LGRAY,lw=0)

    sec(ax,.68,ty,.29,th,C["risk"],"TIER 3 · Logistic Guard  (no disk deps)")
    box(ax,.70,ty+.11,.25,.055,C["risk"],"sigmoid(logit)",fs=9)
    box(ax,.70,ty+.05,.25,.055,"#78350F",
        "logit = cost_ratio×2.0 − margin_pct×4.0\n  + delay_days×0.5 + risk_pressure×1.5",fs=8,tc=LGRAY,lw=0)
    box(ax,.70,ty+.006,.25,.040,"#451A03","Always available · pure math\nno file loads required",fs=8,tc=LGRAY,lw=0)

    # Fallback arrows
    arr(ax,.32,ty+.09,.35,ty+.09,fc="#4ADE80"); lbl(ax,.335,ty+.10,"pkl missing",fs=7,fc="#4ADE80")
    arr(ax,.65,ty+.09,.68,ty+.09,fc=C["yellow"]); lbl(ax,.665,ty+.10,"fallback\nmissing",fs=7,fc=C["yellow"])
    for xo in [.175,.50,.825]: arr(ax,xo,ty,xo,ty-.02)
    box(ax,.18,ty-.055,.64,.032,"#1D4ED8","OUTPUT  →  risk_score: float [0,1]    risk_label: HIGH / MEDIUM / LOW",fs=9)
    return fig

# ── DIAGRAM 4 ─────────────────────────────────────────────────────────────────
def d4():
    fig,ax = _fig("4 · ML Training Pipeline — Data Flow",w=20,h=13)
    box(ax,.10,.905,.80,.038,C["task"],
        "TRIGGER  ·  python -m app.financial_system.ml_pipeline.train_models\n"
        "           OR Celery task 'retrain_ml_models' (every Sunday 02:00 UTC via Beat)",fs=8.5)
    arr(ax,.50,.905,.50,.882)
    # Dataset
    sec(ax,.02,.745,.96,.132,C["data"],"_build_dataset()")
    box(ax,.04,.795,.26,.065,C["data"],"_load_from_db()\nSELECT route,carrier,total_value_usd,\ntotal_cost_usd,credit_days,\ndelay_days_calculated,margin_usd\nFROM dw_shipment_facts LIMIT 100000",fs=8)
    lbl(ax,.355,.835,"rows ≥ 500?",fs=9,fc=C["yellow"])
    arr(ax,.30,.83,.34,.83)
    box(ax,.44,.795,.22,.065,"#14532D","YES → REAL DATA\nproduction-grade path",fs=8.5,tc="#4ADE80")
    box(ax,.70,.795,.25,.065,"#7F1D1D","NO → SYNTHETIC (n=10,000)\n5 routes · 4 carriers\n5 cargo_types · 5 verticals\ncargo delay penalties",fs=8)
    arr(ax,.34,.837,.44,.837); lbl(ax,.41,.843,"YES",fs=7,fc="#4ADE80")
    arr(ax,.34,.823,.70,.823); lbl(ax,.52,.816,"NO",fs=7,fc="#F87171")
    box(ax,.04,.755,.42,.038,"#78350F","risk_label = delay>10 | credit>60 | cost_ratio>0.80 | margin_pct<0.05",fs=8,tc=LGRAY,lw=0)
    box(ax,.50,.755,.46,.038,"#065F46","future_demand (CLV) = order_value × tier_mult × payment_health × margin_factor  (no delay_days leak!)",fs=8,tc=LGRAY,lw=0)
    arr(ax,.50,.745,.50,.728)
    # Feature builder
    sec(ax,.02,.605,.96,.118,C["ml"],"_apply_feature_builder()  —  23-column enriched DataFrame")
    box(ax,.04,.62,.42,.09,"#064E3B",
        "feature_builder.build(row, spatial_severity=0.0)\n"
        "Derived: cost_ratio · margin_pct · carrier_reliability\n"
        "  route_complexity · holding_rate · seasonality_idx\n"
        "Interactions: 9 cross-term features (see Diagram 3)",fs=8,tc=LGRAY,lw=0)
    box(ax,.50,.62,.46,.09,"#0C4A6E",
        "spatial_severity fixed at 0.0 during training\n"
        "(no historical event labels on past shipments)\n"
        "Model learns 0.0 as the no-disruption baseline\n"
        "Inference injects live SpatialRiskInjector values",fs=8,tc=LGRAY,lw=0)
    arr(ax,.46,.665,.50,.665); lbl(ax,.48,.672,"always 0",fs=7)
    arr(ax,.50,.605,.50,.588)
    # 4 model boxes
    my=.365; mh=.21
    for i,(title,sub,feat,tgt,model,out,mc) in enumerate([
        ("DELAY MODEL","XGBRegressor","order_value,total_cost\ncredit_days,route,carrier\n(OHE) — no delay_days!","Target: delay_days","n_est=150 · max_depth=5\nlr=0.08","delay_model.pkl",C["ml"]),
        ("RISK MODEL\n(Primary)","XGBClassifier","order_value,total_cost\ncredit_days,delay_days\nroute,carrier (OHE)","Target: risk_label 0/1","n_est=150 · max_depth=4\nscale_pos_weight=auto","risk_pipeline.pkl\ntrain_columns.pkl",C["risk"]),
        ("GBM FALLBACK","GradientBoosting\nClassifier","23-col enriched vec\n(all NUMERIC_FEATURES)\nno OHE needed","Target: risk_label 0/1","n_est=120 · subsample=0.8\nmin_samples_leaf=20","risk_fallback.pkl\nrisk_fallback_columns.pkl",C["gbm"]),
        ("DEMAND MODEL","RandomForest\nRegressor","order_value,total_cost\ncredit_days,route,carrier\n(OHE) — no delay leak!","Target: CLV proxy\nnot delay-derived","n_est=100 · max_depth=10\nn_jobs=-1","demand_model.pkl",C["fin"]),
    ]):
        x=.02+i*.245
        sec(ax,x,my,.235,mh,mc,title)
        box(ax,x+.01,my+.14,.215,.058,mc,f"{sub}",fs=8.5)
        box(ax,x+.01,my+.09,.215,.046,PANEL,feat,fs=7.5,tc=LGRAY,lw=0)
        box(ax,x+.01,my+.047,.215,.038,PANEL,tgt,fs=7.5,tc=LGRAY,lw=0)
        box(ax,x+.01,my+.009,.215,.033,PANEL,model,fs=7.5,tc=LGRAY,lw=0)
        arr(ax,x+.1175,.605,x+.1175,.575)
    arr(ax,.50,my,.50,my-.028)
    box(ax,.15,my-.062,.70,.028,C["auth"],
        "→ INSERT ml_model_versions {version, delay_rmse, risk_accuracy, demand_rmse, training_rows, data_source}",fs=8)
    return fig

# ── DIAGRAM 5 ─────────────────────────────────────────────────────────────────
def d5():
    fig,ax = _fig("5 · Celery Async Task Topology",w=20,h=13)
    box(ax,.30,.875,.40,.055,"#7F1D1D","REDIS BROKER  (REDIS_URL)\nCelery broker + result backend + distributed cache",fs=9)
    box(ax,.02,.735,.20,.115,C["task"],"CELERY BEAT\nScheduler\n\n55-min: warm_fx\n6-hr: warm_wacc\n60-min: spatial\nSun 02:00: retrain\nDaily 01:00: rag",fs=8)
    box(ax,.25,.735,.45,.115,DGRAY,"CELERY WORKERS  (--concurrency=2  --max-tasks-per-child=50)\nautoretry_for=(Exception,)  max_retries=3  retry_backoff=True\ncountdown = 30 × 2^retry_number",fs=8.5)
    box(ax,.73,.735,.24,.115,C["ml"],"WORKER ISOLATION\nmax-tasks-per-child=50\nprevents OOM from\nML model inference\nmemory leaks",fs=8)
    arr(ax,.50,.875,.50,.855)
    arr(ax,.30,.855,.12,.855); ax.plot([.12,.12],[.855,.775],color=C["task"],lw=1.5,zorder=5)
    arr(ax,.12,.775,.25,.79)
    ax.plot([.70,.85],[.855,.855],color=DGRAY,lw=1.5,zorder=5); arr(ax,.85,.855,.85,.85)
    # Task cards
    tasks=[
        (.02,.53,.30,.17,C["data"],"warm_fx_cache  (every 55 min)",
         "1. GET open.er-api.com/v6/latest\n   → volatility indices per trade route\n   SETEX Redis 'fx_vol:{route}' TTL 55m\n\n2. GET frankfurter.app (ECB feed)\n   → USD→X spot rates all currencies\n   SETEX Redis 'fx_rate:{ccy}' TTL 55m\n\nINFERENCE reads ONLY from Redis\n(never makes live HTTP call)"),
        (.35,.53,.30,.17,"#7C2D12","warm_wacc_cache  (every 6 hours)",
         "GET FRED API → 10yr US Treasury yield\ndelta = current_yield − 4.0%  (Damodaran baseline)\n\nfor each industry vertical:\n  wacc_adjusted = base_wacc + delta\n  SETEX Redis 'wacc:{vertical}' TTL 6h\n\nFallback: raw Damodaran values\nif Redis/FRED unavailable"),
        (.68,.53,.30,.17,C["spatial"],"warm_spatial_events  (every 60 min)",
         "ExternalApiIngester.execute_ingestion_cycle()\n\nGET OpenWeatherMap → storm/weather events\nGET ACLED API → conflict/protest events\nGET MarineTraffic → port congestion\n\nh3.geo_to_h3(lat, lon, resolution=5)\nINSERT INTO external_spatial_events\ninvalidate_cache() ← flush Redis spatial key"),
        (.02,.32,.30,.19,C["ml"],"retrain_ml_models  (Sunday 02:00 UTC)",
         "train_all()\n  _build_dataset()\n    dw_shipment_facts if ≥500 rows\n    else synthetic (n=10,000)\n  XGBoost delay model → delay_model.pkl\n  XGBoost risk classifier → risk_pipeline.pkl\n  GBM fallback → risk_fallback.pkl\n  RandomForest demand → demand_model.pkl\n  deactivate old ml_model_versions\n  INSERT new version (governance record)"),
        (.35,.32,.63,.19,C["erp"],"process_bulk_csv / process_etl_pipeline  (API-triggered)",
         "process_bulk_csv:\n  pd.read_csv(nrows=10) → AIFieldMapper.classify_and_map(columns)\n  for chunk in read_csv(chunksize=10000):\n    chunk.rename(columns=rename_map)\n    chunk.to_sql(detected_schema, engine, if_exists='append')\n  os.remove(filepath) on success\n  retry: countdown=30×2^n  max_retries=3\n\nprocess_etl_pipeline:\n  pdfplumber → SLAContractExtractor → penalty_rate\n  CSV stream + nlp_extracted_penalty_rate column\n  SELECT SUM(ABS(margin_usd)) → financial_impact"),
    ]
    for x,y,w,h,fc,title,detail in tasks:
        sec(ax,x,y,w,h,fc,title)
        body=FancyBboxPatch((x+.008,y+.008),w-.016,h-.048,
            boxstyle="square,pad=0",fc=PANEL,ec="none",alpha=.9,zorder=2)
        ax.add_patch(body)
        ax.text(x+.012,y+h-.014,title,ha="left",va="top",fontsize=8,color=fc,fontweight="bold",zorder=4)
        lines=detail.split("\n")
        for j,line in enumerate(lines):
            ax.text(x+.012,y+h-.034-j*.019,line,ha="left",va="top",fontsize=7.5,color=LGRAY,zorder=4)
    for xo in [.12,.475,.83]: arr(ax,xo,.735,xo,.715)
    return fig

# ── DIAGRAM 6 ─────────────────────────────────────────────────────────────────
def d6():
    fig,ax = _fig("6 · ERP Connector Data Flow",w=20,h=13)
    cols=[("USER / FRONTEND",.08,C["client"]),("BACKEND",.42,C["api"]),("ERP SYSTEM",.76,C["erp"])]
    for t,x,c in cols:
        box(ax,x,.895,.20,.038,c,t,fs=9)
        ax.plot([x+.10,x+.10],[.05,.895],color=c,lw=.4,linestyle="--",alpha=.25,zorder=1)
    rows=[
        (.81,"User clicks\n[Reroute Shipment]",C["client"],"POST /execution/action\n{action_type, internal_id}",C["api"],None,None,"→"),
        (.72,None,None,"ConnectorsGateway\n.execute(action_type, internal_id)",C["api"],None,None,""),
        (.62,None,None,"NetSuiteConnector\n_load_creds()\nNETSUITE_ACCOUNT_ID\nNETSUITE_CLIENT_ID/SECRET",C["erp"],None,None,""),
        (.51,None,None,"_fetch_token()\nPOST suitetalk.api.netsuite.com\n/services/rest/auth/oauth2/v1/token\ngrant_type=client_credentials\n_TokenCache (refresh 60s early)",C["erp"],None,None,""),
        (.40,None,None,"execute_action(REROUTE)\nPATCH /salesOrder/{internal_id}\n{shipMethod, shipAddressLine1}",C["api"],"NetSuite REST API\nOAuth 2.0 Bearer\n/salesOrder/{id}",C["erp"],"→ERP"),
        (.30,"WebSocket push\nRealtimeHub\n(live update)",C["client"],"AuditLogger.log()\nERPWriteback.push()\nerp_connector.execute()",C["api"],None,None,"←"),
    ]
    for y,ltxt,lc,mtxt,mc,rtxt,rc,d in rows:
        h=.075
        if ltxt and lc: box(ax,.08,y,.20,h,lc,ltxt,fs=8)
        box(ax,.40,y,.25,h,mc,mtxt,fs=8,tc=LGRAY,lw=0)
        if d=="→": arr(ax,.28,y+h/2,.40,y+h/2)
        elif d=="←": arr(ax,.40,y+h/2,.28,y+h/2)
        elif d=="→ERP":
            arr(ax,.28,y+h/2,.40,y+h/2)
            if rtxt and rc:
                box(ax,.70,y,.25,h,rc,rtxt,fs=8)
                arr(ax,.65,y+h/2,.70,y+h/2,fc=rc)
    sec(ax,.68,.38,.29,.22,C["erp"],"ERP Action Types")
    for name,detail,yo in [("REROUTE","PATCH shipMethod\n+ shipAddressLine1",.50),
                            ("EXPEDITE","PATCH expedite=True\n+ shipDate (soonest)",.44),
                            ("CANCEL","PATCH transtatus\n= Cancelled",.38)]:
        box(ax,.70,yo,.07,.05,C["erp"],name,fs=7.5)
        lbl(ax,.90,yo+.025,detail,fs=7.5,fc=LGRAY)
    # Sandbox
    sec(ax,.03,.10,.93,.17,DGRAY,"SANDBOX MODE  (no real ERP connected — for demos)")
    box(ax,.05,.12,.25,.085,DGRAY,"POST /connectors/sandbox/simulate",fs=8.5)
    arr(ax,.30,.16,.38,.16)
    box(ax,.38,.12,.30,.085,"#334155","sandbox_router.py\nawait asyncio.sleep(0.8)  ← async!\n(NOT time.sleep — event loop safe)\nsimulate response per action_type",fs=8,tc=LGRAY,lw=0)
    arr(ax,.68,.16,.75,.16)
    box(ax,.75,.12,.19,.085,"#1E293B","Mocked ERP response\n{status: 'success'\n transaction_id: uuid}",fs=8)
    return fig

# ── DIAGRAM 7 ─────────────────────────────────────────────────────────────────
def d7():
    fig,ax = _fig("7 · Spatial Risk Data Flow — H3 Geospatial Pipeline",w=20,h=13)
    for t,x,c in [("EXTERNAL SOURCES",.02,C["ext"]),("INGESTION LAYER",.37,C["data"]),("INFERENCE LAYER",.70,C["spatial"])]:
        box(ax,x,.895,.29,.038,c,t,fs=9)
    for txt,y,c in [("OpenWeatherMap API\nStorm alerts · Cyclones\nWeather events",.77,C["ext"]),
                    ("ACLED API\nConflict events\nProtest / Port strikes",.63,"#7C2D12"),
                    ("MarineTraffic API\nPort congestion\nVessel tracking",.49,"#0C4A6E")]:
        box(ax,.03,y,.29,.10,c,txt,fs=8.5)
        arr(ax,.32,y+.05,.37,y+.05)
    sec(ax,.37,.43,.29,.44,C["data"],"ExternalApiIngester")
    box(ax,.39,.80,.25,.07,C["data"],".execute_ingestion_cycle()",fs=9)
    box(ax,.39,.70,.25,.095,"#78350F","for each event:\n  lat, lon, severity\n  event_type\n  h3_index=h3.geo_to_h3(\n    lat, lon, resolution=5)",fs=8,tc=LGRAY,lw=0)
    box(ax,.39,.59,.25,.07,C["data"],"INSERT\nexternal_spatial_events",fs=8.5)
    box(ax,.39,.53,.25,.05,C["spatial"],"invalidate_cache()  ← flush Redis\nafter each ingestion cycle",fs=8)
    box(ax,.39,.40,.25,.10,"#78350F","external_spatial_events\nh3_index (resolution 5)\nseverity_score [0,1]\nevent_type · is_active\nrecorded_at",fs=7.5,tc=LGRAY,lw=0)
    arr(ax,.515,.53,.515,.50)
    for y in [.80,.70,.59]: arr(ax,.515,y,.515,y-.005)
    sec(ax,.70,.18,.28,.69,C["spatial"],"SpatialRiskInjector  (inference)")
    for txt,y,c in [("_load_events()",.835,C["spatial"]),
                    ("Redis GET spatial_injector:\n  active_events\n  HIT → return JSON\n  MISS → DB + SETEX",.745,"#164E63"),
                    ("_route_to_h3_cells(route)\ntokenize 'CN-EU_SUEZ'\n[CN, EU, SUEZ]\neach→ROUTE_ANCHORS\n→h3.geo_to_h3(lat,lon,r3)",.635,C["spatial"]),
                    ("for each active event:\n  event_cell=h3_to_parent(r3)\n  dist=h3_distance(route,event)\n  if dist>3: skip\n  contrib=severity×0.55^dist\nmax_severity=max(all)",  .495,"#0C4A6E"),
                    ("→ spatial_severity [0.0–1.0]",.41,C["spatial"]),
                    ("feature_builder.build(\n  row, spatial_severity)\nspatial_x_route\nspatial_x_cargo\nmargin_x_spatial",.295,"#14532D"),
                    ("→ RiskEngine.compute(enriched)",.21,C["ml"])]:
        h=.082 if "\n" in txt else .042
        box(ax,.72,y,.24,h,c,txt,fs=8,tc=(LGRAY if "\n" in txt else WHITE),lw=0 if "\n" in txt else 1)
    for y in [.835,.745,.635,.495,.41,.33]: arr(ax,.84,y,.84,y-.008)
    arr(ax,.66,.50,.70,.84,fc=C["spatial"]); arr(ax,.66,.45,.72,.75,fc=DGRAY)
    sec(ax,.02,.09,.64,.15,DGRAY,"ROUTE_ANCHORS  (27 port/waypoint mappings)")
    for txt,x in [("CN→Shanghai\n(31.23,121.47)",.04),("EU→Rotterdam\n(51.90,4.48)",.18),
                  ("US→Los Angeles\n(33.74,-118.27)",.32),("SUEZ→Canal\n(29.97,32.55)",.46),
                  ("MALACCA→Strait\n(1.26,103.58)",.54)]:
        box(ax,x,.11,.13,.06,"#1E3A5F",txt,fs=7.5)
    return fig

# ── DIAGRAM 8 ─────────────────────────────────────────────────────────────────
def d8():
    fig,ax = _fig("8 · Frontend Component Architecture  (React + Vite)",w=20,h=13)
    box(ax,.38,.905,.24,.038,C["api"],"App.tsx — Root Router",fs=9)
    box(ax,.10,.835,.22,.055,C["auth"],"AuthProvider\n(AuthContext.tsx)\ncurrentUser · JWT",fs=8)
    box(ax,.68,.835,.22,.055,C["fin"],"CurrencyProvider\n(CurrencyContext.tsx)\nlocale · rates",fs=8)
    arr(ax,.50,.905,.21,.89,fc=C["auth"]); arr(ax,.50,.905,.79,.89,fc=C["fin"])
    box(ax,.35,.765,.30,.055,DGRAY,"Shell.tsx  —  Main Application Container",fs=9)
    arr(ax,.21,.835,.50,.82,fc=C["auth"]); arr(ax,.79,.835,.50,.82,fc=C["fin"])
    for txt,x,w,c in [("SyntheticDataBanner\nGET /ingestion/data-quality\namber banner if is_synthetic",.01,.19,C["data"]),
                      ("TopMenuRibbon\nTab navigation\nOverview|Matrix|Ingest...",.22,.19,DGRAY),
                      ("Sidebar\nSecondary nav\nper module",.43,.16,DGRAY),
                      ("TopBar\nUser menu\nnotifications",.61,.16,DGRAY)]:
        box(ax,x,.675,w,.075,c,txt,fs=7.5)
        arr(ax,.50,.765,x+w/2,.75)
    box(ax,.35,.60,.30,.05,"#334155","<main> — activeView State Router",fs=8.5)
    arr(ax,.50,.675,.50,.65)
    views1=[("dashboard\nDashboard.tsx\nKPICard×4\nCashflowChart\nRiskRadar",.01,.13,.12,C["client"]),
            ("matrix\nIntelligenceMatrix\nConfidencePanel\nSpatialGridOverlay\nRerouteStudio",.15,.15,.12,C["risk"]),
            ("ingest\nIngestionStudio\nCSV drag-drop\nAIFieldMapper\nVisionDiagnostic",.32,.14,.12,C["data"]),
            ("warehouse\nShipmentWarehouse\nPaginated grid\nGET /data-grid\nExport CSV",.48,.14,.12,C["fin"]),
            ("realtime\nRealtimeHub\nWebSocket\nlive alerts\nHITL approvals",.64,.13,.12,C["spatial"]),
            ("admin\nAdminDashboard\nModelPerformance\nUser mgmt\nRoles/perms",.79,.20,.12,C["auth"])]
    for txt,x,w,h,c in views1:
        box(ax,x,.455,w,h,c,txt,fs=7.5)
        arr(ax,.50,.60,x+w/2,.455+h)
    views2=[("optimization\nOptimizationPage\nPOST /optimize/routes\nprofit maximize",.05,.17,.095,C["ml"]),
            ("sla\nSLAPage\nGET /sla/contracts\npenalty tracking",.25,.16,.095,C["erp"]),
            ("gst\nGSTDashboard\nGST compliance\nIndia module",.44,.16,.095,"#065F46"),
            ("cashflow\nCashflow Timeline\n90d projection\nshock detector",.63,.16,.095,C["fin"]),
            ("reports\nReportsPage\nExport PDF/CSV\nScheduled",.82,.15,.095,DGRAY)]
    for txt,x,w,h,c in views2:
        box(ax,x,.32,w,h,c,txt,fs=7.5)
    sec(ax,.02,.08,.96,.18,C["api"],"API Client Layer  (services/api.ts · hooks/queries.ts · context/)")
    for txt,x,c in [("axios instance\nJWT interceptor\nAuto Bearer header",.04,C["api"]),
                    ("React Query hooks\ncache + refetch\nhooks/queries.ts",.24,C["ml"]),
                    ("AuthContext\nuseAuth() hook\nlocalStorage JWT",.45,C["auth"]),
                    ("CurrencyContext\nuseCurrency()\nformat helpers",.66,C["fin"]),
                    ("VITE_API_URL\nenv var\nbase URL",.86,DGRAY)]:
        box(ax,x,.10,.18,.12,c,txt,fs=7.5)
    return fig

# ── DIAGRAM 9 ─────────────────────────────────────────────────────────────────
def d9():
    fig,ax = _fig("9 · Database Schema — Key Tables",w=20,h=13)
    sec(ax,.02,.08,.60,.87,C["data"],"PostgreSQL 15")
    tables=[
        (.03,.72,.26,.21,C["data"],"dw_shipment_facts",
         ["id (PK)","tenant_id  ← multi-tenancy key","source_system  'BULK-CSV'|'ERP-SYNC'",
          "route","carrier","total_value_usd","total_cost_usd","margin_usd",
          "credit_days","delay_days_calculated","nlp_extracted_penalty_rate","recorded_at"]),
        (.32,.72,.27,.21,C["erp"],"sla_contracts",
         ["id (PK)","tenant_id","contract_name",
          "penalty_rate","penalty_type  'percentage'|'flat_fee'",
          "force_majeure_applies  BOOLEAN","extracted_at"]),
        (.03,.47,.26,.22,C["spatial"],"external_spatial_events",
         ["id (PK)","h3_index  (resolution 5)",
          "severity_score  NUMERIC [0,1]","event_type  'weather'|'conflict'|",
          "  'port_congestion'","is_active  BOOLEAN","recorded_at"]),
        (.32,.47,.27,.22,C["ml"],"ml_model_versions",
         ["id (PK)","tenant_id","model_name",
          "version  'v-2026-05-05'","is_active  BOOLEAN",
          "training_rows","data_source  'real'|'synthetic'",
          "delay_rmse","risk_accuracy","demand_rmse"]),
        (.03,.24,.26,.20,C["auth"],"roles",
         ["id (PK)","name",
          "permissions  JSONB {","  can_approve: bool",
          "  can_admin: bool","  can_write: bool","  can_view_costs: bool }"]),
        (.32,.24,.27,.20,C["client"],"users",
         ["id (PK)","email","hashed_password","tenant_id","role_id  (FK → roles.id)"]),
        (.03,.10,.56,.12,"#7F1D1D","audit_log",
         ["id (PK)","user_id","tenant_id","action_type","payload  JSONB","timestamp"]),
    ]
    for x,y,w,h,fc,name,cols in tables:
        box(ax,x,y+h-.038,w,.038,fc,name,fs=8.5)
        ax.add_patch(FancyBboxPatch((x+.002,y+.002),w-.004,h-.042,
            boxstyle="square,pad=0",fc=PANEL,ec=fc,linewidth=1,alpha=.9,zorder=2))
        cy=y+h-.055
        for col in cols:
            ax.text(x+.008,cy,f"  {col}",ha="left",va="top",fontsize=7,color=LGRAY,zorder=4)
            cy-=.018
    arr(ax,.32,.34,.29,.34,fc=C["auth"]); lbl(ax,.305,.348,"FK",fs=6.5,fc=C["auth"])
    # Redis
    sec(ax,.64,.08,.34,.87,"#991B1B","Redis 7  (Cache + Broker)")
    redis_items=[
        ("fx_rates:{currency}","TTL: 55 min","Spot rates all currencies\nopen.er-api.com → ECB feed",C["data"],.66,.80),
        ("wacc:{vertical}","TTL: 6 hours","WACC per industry vertical\nadjusted vs FRED Treasury yield","#7C2D12",.66,.70),
        ("spatial_injector:\nactive_events","TTL: 5 min","JSON list of active H3 events\nflushed after each ingestion",C["spatial"],.66,.59),
        ("celery broker\ntask queues","persistent","Beat schedule + API-triggered\ntask routing and results",C["task"],.66,.49),
        ("session tokens","TTL: 24 hr","JWT token store\n(logout blacklist support)",C["auth"],.66,.39),
    ]
    for name,ttl,desc,fc,x,y in redis_items:
        box(ax,x,y,.30,.085,fc,f"{name}\n{ttl}\n{desc}",fs=7.5,lw=0,tc=LGRAY)
    patches=[mpatches.Patch(fc=c,label=l,ec=WHITE) for c,l in [
        (C["data"],"Fact table"),(C["erp"],"Contracts"),(C["spatial"],"Spatial events"),
        (C["ml"],"ML governance"),(C["auth"],"Auth/RBAC"),(C["client"],"Users")]]
    ax.legend(handles=patches,loc="lower right",bbox_to_anchor=(.99,.01),
              facecolor=PANEL,edgecolor=DGRAY,fontsize=7,labelcolor=WHITE,framealpha=.8)
    return fig

# ── DIAGRAM 10 ────────────────────────────────────────────────────────────────
def d10():
    fig,ax = _fig("10 · Deployment Architecture — Production EC2",w=20,h=13)
    box(ax,.38,.905,.24,.038,"#1E40AF","INTERNET\nHTTPS traffic",fs=9)
    arr(ax,.50,.905,.50,.882)
    sec(ax,.04,.12,.92,.76,DGRAY,"AWS EC2  (t3.medium+)  —  docker-compose.prod.yml")
    box(ax,.28,.835,.44,.038,"#334155","docker-compose.prod.yml",fs=9)
    arr(ax,.50,.882,.50,.873)
    for title,detail,x,c in [
        ("frontend\n(nginx)",":80/:443\nHTTPS termination\nProxy /api→backend\nStatic React build\ncertbot SSL",.07,C["client"]),
        ("backend\n(FastAPI+uvicorn)",":8000\nGET /health\n30s interval\n180s start-period\nAll API routes",.27,C["api"]),
        ("worker\n(Celery+Beat)","internal only\n--concurrency=2\n--max-tasks=50\nScheduled tasks\nRetry logic",.50,C["task"]),
        ("redis\n(broker+cache)",":6379 internal\nCelery broker\nFX/WACC cache\nSpatial events\nSession tokens",.72,"#7F1D1D"),
    ]:
        box(ax,x,.70,.20,.09,c,title,fs=9)
        box(ax,x,.575,.20,.122,PANEL,detail,fs=8,tc=LGRAY,lw=0)
        arr(ax,.50,.835,x+.10,.79)
    ax.annotate("",xy=(.27,.645),xytext=(.26,.645),
        arrowprops=dict(arrowstyle="<->",color=WHITE,lw=1.5),zorder=5)
    lbl(ax,.265,.66,"proxy",fs=7)
    ax.annotate("",xy=(.50,.645),xytext=(.47,.645),
        arrowprops=dict(arrowstyle="<->",color=C["task"],lw=1.5),zorder=5)
    lbl(ax,.485,.66,"tasks",fs=7,fc=C["task"])
    ax.annotate("",xy=(.72,.645),xytext=(.70,.645),
        arrowprops=dict(arrowstyle="<->",color="#F87171",lw=1.5),zorder=5)
    lbl(ax,.71,.66,"broker",fs=7,fc="#F87171")
    sec(ax,.06,.38,.88,.17,"#065F46","Docker Volumes  (persistent across restarts)")
    box(ax,.09,.40,.40,.12,"#14532D",
        "ml_models volume\n/code/app/financial_system/ml_pipeline/models/\ndelay_model.pkl  risk_pipeline.pkl\nrisk_fallback.pkl  demand_model.pkl",fs=8,tc=LGRAY,lw=0)
    box(ax,.53,.40,.38,.12,"#78350F",
        "uploads volume\n/code/tmp_uploads/\nTemporary CSV/PDF during ETL\nDeleted after success",fs=8,tc=LGRAY,lw=0)
    box(ax,.10,.17,.35,.16,C["data"],
        "AWS RDS\n(PostgreSQL — managed)\nDATABASE_URL env var\nNOT containerized",fs=8.5)
    arr(ax,.27,.575,.27,.33); arr(ax,.27,.33,.27,.33)
    box(ax,.52,.17,.40,.16,"#334155",
        "Runtime Env Vars\nDATABASE_URL  REDIS_URL  JWT_SECRET_KEY\nNETSUITE_*  OPENWEATHER_API_KEY\nACLED_*  MARINETRAFFIC_API_KEY\nFRED_API_KEY  PORT=8000",fs=8,tc=LGRAY,lw=0)
    return fig

# ── DIAGRAM 11 ────────────────────────────────────────────────────────────────
def d11():
    fig,ax = _fig("11 · Authentication & Authorization Flow",w=20,h=13)
    for sec_title,sy,sc in [("REGISTRATION",.675,C["auth"]),("LOGIN",.385,C["api"]),("EVERY PROTECTED REQUEST",.09,C["fin"])]:
        sec(ax,.02,sy,.96,.265,sc,sec_title)
    # Registration
    box(ax,.04,.73,.17,.17,C["client"],"Browser\nPOST /auth/register\n{email, password\n tenant_id}",fs=8)
    arr(ax,.21,.815,.29,.815)
    box(ax,.29,.73,.20,.17,C["auth"],"bcrypt.hash\n(password)\n→ hashed_password",fs=8.5)
    arr(ax,.49,.815,.57,.815)
    box(ax,.57,.73,.26,.17,C["data"],"INSERT users\n(email, hashed_pw\n tenant_id, role_id)\n→ 200 {user_id}",fs=8.5)
    arr(ax,.83,.815,.88,.815)
    box(ax,.88,.755,.08,.11,"#14532D","200\nOK",fs=8.5,tc="#4ADE80")
    # Login
    box(ax,.04,.44,.17,.17,C["client"],"Browser\nPOST /auth/login\n{email\n password}",fs=8)
    arr(ax,.21,.525,.29,.525)
    box(ax,.29,.44,.20,.17,"#7C3AED","bcrypt.verify\n(password,\n hashed_pw)",fs=8.5)
    arr(ax,.49,.525,.57,.525)
    box(ax,.57,.44,.26,.17,C["auth"],"jwt.encode({\n  user_id, tenant_id\n  role, exp=24h\n}, JWT_SECRET_KEY)\n→ access_token",fs=8.5)
    arr(ax,.83,.525,.88,.525)
    box(ax,.84,.445,.115,.165,"#14532D","200 OK\n{access_token\n token_type:\n 'bearer'}",fs=8,tc="#4ADE80")
    lbl(ax,.50,.40,"Frontend → localStorage.setItem('token', access_token)  ·  axios interceptor → Authorization: Bearer {token}",fs=8,fc=LGRAY)
    # Protected request
    box(ax,.04,.15,.16,.165,C["client"],"axios request\nAuthorization:\nBearer <token>",fs=8.5)
    arr(ax,.20,.235,.28,.235)
    box(ax,.28,.15,.19,.165,C["fin"],"get_current_user()\n[FastAPI Depends]\njwt.decode()\nSELECT users\n→ {user_id,\n  tenant_id,\n  role, perms}",fs=8)
    arr(ax,.47,.235,.55,.235)
    box(ax,.55,.15,.19,.165,C["auth"],"PermissionEngine\n.check(user.perms,\n required_perm)\n\ncan_approve\ncan_admin\ncan_write",fs=8.5)
    arr(ax,.74,.235,.82,.235)
    box(ax,.82,.15,.14,.165,C["risk"],"HITL Gate\nrisk_score>\nthreshold AND\n!can_approve\n→ {requires\n_approval:true}",fs=8)
    box(ax,.55,.105,.10,.032,"#14532D","PASS→proceed",fs=7.5,tc="#4ADE80")
    box(ax,.67,.105,.10,.032,"#7F1D1D","FAIL→403",fs=7.5,tc="#F87171")
    return fig

# ── DIAGRAM 12 ────────────────────────────────────────────────────────────────
def d12():
    fig,ax = _fig("12 · RAG (Retrieval-Augmented Generation) Pipeline",w=20,h=13)
    sec(ax,.02,.50,.96,.44,C["rag"],"NIGHTLY INGESTION  (01:00 UTC — Celery Beat  ·  refresh_rag_knowledge_base)")
    box(ax,.04,.895,.92,.035,C["task"],"RAGIngestionPipeline.run_full(tenant_id)  →  re-embeds last 90 days of operational data",fs=9)
    arr(ax,.50,.895,.50,.877)
    for txt,x,c in [("dw_shipment_facts\n(last 90 days)\nroute, carrier,\ndelay, margin\n→ text chunks",.05,C["data"]),
                    ("sla_contracts\npenalty clauses\nforce majeure\ncontract terms\n→ text chunks",.29,C["erp"]),
                    ("audit_log\npast decisions\n+ outcomes\nfeedback loop\n→ text chunks",.53,C["auth"]),
                    ("external_spatial\n_events\nactive disruptions\nlocation+type\n→ text chunks",.77,C["spatial"])]:
        box(ax,x,.70,.20,.165,c,txt,fs=8,tc=LGRAY,lw=0)
        arr(ax,x+.10,.70,x+.10,.683)
    box(ax,.18,.565,.64,.105,C["rag"],
        "RAGEmbedder.embed(chunk)\nsentence-transformers/all-MiniLM-L6-v2  →  384-dimensional vector per chunk\nUPSERT vector_store  (pgvector or in-memory index)",fs=9)
    for x in [.15,.39,.63,.87]: arr(ax,x,.70,.50,.67)
    arr(ax,.50,.565,.50,.548)
    ax.plot([.02,.98],[.50,.50],color=C["rag"],lw=2,linestyle="--",alpha=.5,zorder=5)
    lbl(ax,.50,.508,"── NIGHTLY INGESTION ABOVE  ·  INFERENCE BELOW ──",fs=8.5,fc=C["rag"])
    sec(ax,.02,.06,.96,.435,"#1A2E05","INFERENCE TIME  (Executive Narrative Generation)")
    box(ax,.04,.44,.30,.038,C["agent"],"ExecutiveAgent.generate_narrative(decision, context)",fs=8.5)
    arr(ax,.19,.44,.19,.422)
    box(ax,.04,.325,.30,.092,C["rag"],
        "RAGRetriever.search(query, top_k=5)\n  embed(query) → 384-dim vector\n  cosine_similarity(query, all_chunks)\n  → top-5 most relevant contexts",fs=8.5)
    box(ax,.04,.195,.30,.125,"#365314",
        "Retrieved context chunks:\n• Route CN-EU Maersk 14d delay margin $12,400\n• Hamburg port strike severity 0.82 (ACLED)\n• Prior decision 2025-11-12: REROUTE ✓\n• SLA contract: 5%/day penalty clause",fs=8,tc=LGRAY,lw=0)
    arr(ax,.34,.375,.42,.375)
    box(ax,.42,.27,.30,.14,"#14532D",
        "LLMGateway.complete(\n  system='CFO-level supply chain analyst...'\n  context=retrieved_chunks\n  user_query=decision_summary\n)\n→ Claude/GPT API call",fs=8.5)
    arr(ax,.72,.34,.79,.34)
    box(ax,.79,.22,.18,.18,C["rag"],
        "NARRATIVE OUTPUT\n\n'Given Hamburg port\ncongestion (sev 0.82)\n+ CN-EU exposure,\nmargin compression\nrisk elevated.\nConsider Cape of\nGood Hope reroute.'",fs=8,tc=WHITE,lw=0)
    arr(ax,.865,.22,.50,.155)
    box(ax,.20,.085,.60,.08,C["fin"],
        "response.narrative → ExecutiveDecisionBanner.tsx\nconfidence_score · cashflow_impact_90d · recommended_actions[]",fs=8.5)
    return fig

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("Generating Fiscalogix Architecture PDF …")
    diagrams=[
        (d1,"1. High-Level System Architecture"),
        (d2,"2. Financial Intelligence Pipeline"),
        (d3,"3. Risk Scoring 3-Tier Inference"),
        (d4,"4. ML Training Pipeline"),
        (d5,"5. Celery Async Task Topology"),
        (d6,"6. ERP Connector Data Flow"),
        (d7,"7. Spatial Risk H3 Pipeline"),
        (d8,"8. Frontend Component Architecture"),
        (d9,"9. Database Schema"),
        (d10,"10. Deployment Architecture"),
        (d11,"11. Authentication & Authorization"),
        (d12,"12. RAG Pipeline"),
    ]
    with PdfPages(OUTPUT) as pdf:
        for i,(fn,title) in enumerate(diagrams):
            print(f"  [{i+1}/{len(diagrams)}] {title}")
            fig=fn()
            pdf.savefig(fig,bbox_inches="tight",facecolor=fig.get_facecolor(),dpi=150)
            plt.close(fig)
        d=pdf.infodict()
        d["Title"]="Fiscalogix System Architecture Diagrams"
        d["Author"]="Fiscalogix Engineering"
        d["Subject"]="Low-level system design, data flow charts, and workflow diagrams"
    print(f"\nDone -> {OUTPUT}")

if __name__=="__main__":
    main()
