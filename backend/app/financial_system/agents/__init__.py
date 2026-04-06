"""
Multi-Agent System (MAS) — Layer 4 of the Fiscalogix Intelligence Stack.

Each agent wraps one or more deterministic financial engines and returns
a structured result. The AdaptiveOrchestrator decides which agents to run
and in what order based on the live situation context.

Determinism guarantee:
  All financial numbers (ReVM, VaR, risk scores, delay predictions) are
  produced exclusively by the deterministic engines in financial_system/.
  Agents never invent numbers — they only call engines and pass results to
  the LLM for narrative synthesis.

Agent registry:
  RiskAgent       → XGBoost + GNN + SHAP → risk scores, contagion signals
  FinancialAgent  → ReVM, FX, SLA, time value, Monte Carlo VaR
  RoutingAgent    → Dijkstra rerouting, strike detection, geopolitical graph
  AnomalyAgent    → Statistical outlier detection across the portfolio
  ExecutiveAgent  → Synthesizes all prior results into a CFO-ready brief (LLM)
"""
