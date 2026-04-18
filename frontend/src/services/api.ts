export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface DashboardData {
  summary: {
    total_revenue:    number;
    total_cost:       number;
    total_profit:     number;
    total_revm:       number;
    loss_shipments:   number;
    breakdown?: {
      delay_cost:        number;
      penalty_cost:      number;
      inventory_holding: number;
      opportunity_cost:  number;
    };
  };
  confidence:      { global_score: number };
  financial_impact?: { wacc_cost?: number; total_efi?: number };
  shocks?:         any[];
}

export interface MLPerformance {
  delay_accuracy_pct: number;
  delay_accuracy_delta: string;
  cost_accuracy_pct: number;
  cost_accuracy_delta: string;
  system_bias_inr: number;
  drift_detected: boolean;
  drift_model: string;
  drift_detail: string;
  retraining_mode: string;
  last_retrained: string;
  trust_score: number;
  learning_insights: string[];
  updated_at: string;
}

export interface RedisStatus {
  available: boolean;
  host: string;
  degraded_features: string[];
  fallback_behavior: string | null;
}



/**
 * Get the Authorization header using the stored JWT token.
 */
const getAuthHeader = (): Record<string, string> => {
  const token = localStorage.getItem('access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const apiService = {
  /**
   * Fetch executive dashboard metrics
   */
  async getExecutiveOverview(tenantId: string = 'default_tenant'): Promise<DashboardData> {
    try {
      const response = await fetch(`${API_BASE_URL}/financial-intelligence?tenant_id=${tenantId}`, {
        headers: getAuthHeader()
      });
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error("Failed to fetch executive overview:", error);
      throw error;
    }
  },

  /**
   * Fetch live SHAP insights and Monte Carlo data for the Executive Cockpit
   */
  async getShipmentInsights(shipmentId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/predict/shipment/${shipmentId}/insights`, {
        headers: getAuthHeader()
      });
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error(`Failed to fetch insights for ${shipmentId}:`, error);
      throw error;
    }
  },

  /**
   * Push a structural decision (e.g., REROUTE) back to the backend + ERP
   */
  async executeAction(payload: {
    action_type: string;
    shipment_id: string;
    erp_target: string;
    confidence_score: number;
    parameters?: any;
  }) {
    try {
      const response = await fetch(`${API_BASE_URL}/execution/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify(payload) // No mock_user_id — the JWT carries identity now
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Execution failed');
      }
      return await response.json();
    } catch (error) {
      console.error(`Failed to execute action on ${payload.shipment_id}:`, error);
      throw error;
    }
  },

  /**
   * Fetch predictive cashflow trajectories from AR survival model
   */
  async getPredictiveCashflow(tenantId: string = "default_tenant") {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/predict/cashflow/trajectory?tenant_id=${tenantId}`, {
        headers: getAuthHeader()
      });
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error(`Failed to fetch cashflow trajectory:`, error);
      throw error;
    }
  },

  /**
   * Fetch live ML model health status for Governance Shield
   */
  async getModelHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/model-health`, {
        headers: getAuthHeader()
      });
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error("Failed to fetch model health:", error);
      throw error;
    }
  },

  /**
   * Fetch explainability details for a shipment from the Confidence Studio
   * Returns: risk_probability, model_confidence, key_drivers, narrative, cfo_brief
   */
  async getConfidenceExplain(shipmentId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/confidence-studio/explain/${shipmentId}`, {
        headers: getAuthHeader()
      });
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error(`Failed to fetch confidence explain for ${shipmentId}:`, error);
      throw error;
    }
  },

  /**
   * POST to freight hedging engine — predicts 6-month spot rate and optimal contract decision
   * routes: array of { route_id, current_spot_rate, current_contract_rate, market_volatility_index? }
   */
  async getFreightHedging(routes: {
    route_id: string;
    current_spot_rate: number;
    current_contract_rate: number;
    market_volatility_index?: number;
  }[]) {
    try {
      const response = await fetch(`${API_BASE_URL}/enterprise/freight-hedging`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify(routes)
      });
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error("Failed to fetch freight hedging:", error);
      throw error;
    }
  },

  /**
   * POST to AR default predictor — returns probability of default + expected credit loss
   */
  async getARDefault(customers: {
    customer_id: string;
    order_value: number;
    credit_days: number;
    historical_defaults?: number;
    macro_economic_index?: number;
  }[]) {
    try {
      const response = await fetch(`${API_BASE_URL}/enterprise/ar-default`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify(customers)
      });
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error("Failed to fetch AR default risk:", error);
      throw error;
    }
  },

  /** POST /enterprise/carbon-tax — Scope 3 emissions + CBAM tax per shipment */
  async getCarbonTax(shipments: {
    shipment_id: string; route: string; carrier: string;
    order_value: number; total_cost: number; weight_tons?: number;
  }[]) {
    const response = await fetch(`${API_BASE_URL}/enterprise/carbon-tax`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(shipments)
    });
    if (!response.ok) throw new Error('Carbon tax engine error');
    return await response.json();
  },

  /** POST /enterprise/meio-inventory — Multi-echelon inventory optimization */
  async getMEIO(skus: {
    sku: string; global_inventory: number; wacc?: number;
    holding_cost_usd: number; stockout_penalty_usd: number;
  }[]) {
    const response = await fetch(`${API_BASE_URL}/enterprise/meio-inventory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(skus)
    });
    if (!response.ok) throw new Error('MEIO engine error');
    return await response.json();
  },

  /** POST /enterprise/gnn-systemic-risk — GNN contagion risk propagation */
  async getGNNRisk(shipments: Record<string, any>[]) {
    const response = await fetch(`${API_BASE_URL}/enterprise/gnn-systemic-risk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ shipments })
    });
    if (!response.ok) throw new Error('GNN risk engine error');
    return await response.json();
  },

  /** POST /enterprise/llm-negotiator — LLM contract negotiation prompts */
  async getLLMNegotiator(suppliers: {
    supplier_id: string; historical_delay_variance_pct?: number;
    current_payment_terms?: number; target_payment_terms?: number;
    wacc_carrying_cost_usd: number;
  }[]) {
    const response = await fetch(`${API_BASE_URL}/enterprise/llm-negotiator`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(suppliers)
    });
    if (!response.ok) throw new Error('LLM negotiator error');
    return await response.json();
  },

  /** POST /optimization/network — MILP network routing (returns job_id) */
  async optimizeNetwork(payload: {
    origins: string[]; destinations: string[];
    supply: Record<string, number>; demand: Record<string, number>;
    costs: Record<string, Record<string, number>>;
    capacities: Record<string, Record<string, number>>;
  }) {
    const response = await fetch(`${API_BASE_URL}/optimization/network`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error('Network optimizer error');
    return await response.json();
  },

  /** POST /optimization/inventory_meio — MEIO via job queue (returns job_id) */
  async optimizeInventoryQueue(nodes: Record<string, any>[], service_level = 0.95) {
    const response = await fetch(`${API_BASE_URL}/optimization/inventory_meio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ nodes, service_level })
    });
    if (!response.ok) throw new Error('Inventory optimizer error');
    return await response.json();
  },

  /** POST /optimization/monte_carlo_risk — Step-cost Monte Carlo (returns job_id) */
  async runMonteCarloRisk(legs: Record<string, number>[], target_arrival_days: number, simulations = 10000) {
    const response = await fetch(`${API_BASE_URL}/optimization/monte_carlo_risk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ legs, target_arrival_days, simulations })
    });
    if (!response.ok) throw new Error('Monte Carlo engine error');
    return await response.json();
  },

  /** POST /api/v1/predict/delay — Batch delay prediction */
  async predictDelay(shipments: Record<string, any>[]) {
    const response = await fetch(`${API_BASE_URL}/api/v1/predict/delay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(shipments)
    });
    if (!response.ok) throw new Error('Delay prediction error');
    return await response.json();
  },

  /** POST /api/v1/predict/efi — StochasticMIP EFI optimization */
  async optimizeEFI(candidateMatrix: Record<string, any>[][], available_cash = 1000000, risk_appetite = 'BALANCED') {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/predict/efi?available_cash=${available_cash}&risk_appetite=${risk_appetite}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify(candidateMatrix)
      }
    );
    if (!response.ok) throw new Error('EFI optimizer error');
    return await response.json();
  },

  /** GET /api/v1/documents/agentic/gaps — Cross-document coverage gap analysis */
  async getDocumentGaps() {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/agentic/gaps`, {
      headers: getAuthHeader()
    });
    if (!response.ok) throw new Error('Document gap analysis error');
    return await response.json();
  },

  /** GET /api/v1/documents/agentic/disputes — Autonomous billing dispute detection */
  async getDocumentDisputes() {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/agentic/disputes`, {
      headers: getAuthHeader()
    });
    if (!response.ok) throw new Error('Dispute detection error');
    return await response.json();
  },

  /** POST /api/v1/mapping/erp — AI ERP field mapper */
  async mapERPFields(headers: string[]) {
    const response = await fetch(`${API_BASE_URL}/api/v1/mapping/erp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(headers)
    });
    if (!response.ok) throw new Error('ERP mapping error');
    return await response.json();
  },

  /** GET /execution/spatial/active-risks — live H3 spatial risk events */
  async getSpatialRisks() {
    const response = await fetch(`${API_BASE_URL}/execution/spatial/active-risks`, {
      headers: getAuthHeader()
    });
    if (!response.ok) throw new Error('Spatial risk query failed');
    return await response.json();
  },

  /** GET /optimization/status/:jobId — poll for background job result */
  async getJobStatus(jobId: string) {
    const response = await fetch(`${API_BASE_URL}/optimization/status/${jobId}`, {
      headers: getAuthHeader(),
    });
    if (!response.ok) throw new Error('Job status check failed');
    return await response.json();
  },

  /** GET /admin/redis-status — whether Redis is live and which features are degraded */
  async getRedisStatus() {
    const response = await fetch(`${API_BASE_URL}/admin/redis-status`, {
      headers: getAuthHeader()
    });
    if (!response.ok) throw new Error('Redis status check failed');
    return await response.json();
  },

  /** GET /admin/ml-performance — model accuracy, drift, learning loop status */
  async getMLPerformance() {
    const response = await fetch(`${API_BASE_URL}/admin/ml-performance`, {
      headers: getAuthHeader()
    });
    if (!response.ok) throw new Error('ML performance fetch failed');
    return await response.json();
  },

  /** GET /reports/export/excel — downloads .xlsx workbook; returns raw Response for blob handling */
  async downloadExcel(): Promise<Response> {
    return fetch(`${API_BASE_URL}/reports/export/excel`, { headers: getAuthHeader() });
  },

  /** GET /reports/export/summary — JSON summary for print-to-PDF */
  async getReportSummary() {
    const response = await fetch(`${API_BASE_URL}/reports/export/summary`, { headers: getAuthHeader() });
    if (!response.ok) throw new Error('Report summary fetch failed');
    return await response.json();
  },

  /** GET /alerts/thresholds — current alert thresholds */
  async getAlertThresholds() {
    const response = await fetch(`${API_BASE_URL}/alerts/thresholds`, { headers: getAuthHeader() });
    if (!response.ok) throw new Error('Alert threshold fetch failed');
    return await response.json();
  },

  /** POST /alerts/configure — save thresholds + notification channels */
  async configureAlerts(config: {
    cash_deficit_usd?:    number;
    high_risk_shipments?: number;
    confidence_floor?:    number;
    alert_email?:         string;
    alert_whatsapp_to?:   string;
  }) {
    const response = await fetch(`${API_BASE_URL}/alerts/configure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error('Alert configure failed');
    return await response.json();
  },

  /** POST /alerts/check — trigger live alert evaluation */
  async checkAlerts() {
    const response = await fetch(`${API_BASE_URL}/alerts/check`, {
      method: 'POST',
      headers: getAuthHeader(),
    });
    if (!response.ok) throw new Error('Alert check failed');
    return await response.json();
  },

  /** GET /datagrid/shipments — paginated sortable shipment grid */
  async getShipmentGrid(page: number, sortBy: string, sortDir: 'asc' | 'desc') {
    const response = await fetch(
      `${API_BASE_URL}/datagrid/shipments?page=${page}&limit=50&sort_by=${sortBy}&sort_dir=${sortDir}`,
      { headers: getAuthHeader() }
    );
    if (!response.ok) throw new Error('Shipment grid fetch failed');
    return await response.json();
  },

  // ── India GST Intelligence ────────────────────────────────────────────────

  /** POST /india/gst-cost — per-shipment GST and customs cost breakdown */
  async getGSTCost(shipments: {
    shipment_id: string;
    route: string;
    order_value: number;
    hs_code?: string;
    wacc?: number;
    gst_refund_mode?: string;
  }[]) {
    const response = await fetch(`${API_BASE_URL}/india/gst-cost`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(shipments),
    });
    if (!response.ok) throw new Error('GST cost calculation failed');
    return await response.json();
  },

  /** POST /india/gst-refund-tracker — portfolio working capital burn from GST refund lag */
  async getGSTRefundTracker(payload: {
    shipments: {
      shipment_id: string;
      route: string;
      order_value: number;
      hs_code?: string;
      gst_refund_mode?: string;
      igst_paid?: number;
      gst_refund_filed_date?: string;
      credit_days?: number;
    }[];
    wacc?: number;
    tenant_id?: string;
  }) {
    const response = await fetch(`${API_BASE_URL}/india/gst-refund-tracker`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('GST refund tracker failed');
    return await response.json();
  },

  /** GET /india/routes — supported Indian trade corridors with applicable rates */
  async getIndiaRoutes() {
    const response = await fetch(`${API_BASE_URL}/india/routes`, {
      headers: getAuthHeader(),
    });
    if (!response.ok) throw new Error('India routes fetch failed');
    return await response.json();
  },

  // ── SLA Contract Pipeline ─────────────────────────────────────────────────

  /** POST /sla/analyze — full pipeline: parse + extract + penalty + score */
  async analyzeSLAContract(file: File, params: {
    order_value?: number;
    contract_type?: string;
    customer_tier?: string;
    predicted_delay_days?: number;
    otif_actual_pct?: number;
    use_llm?: boolean;
    tenant_id?: string;
  } = {}) {
    const qs = new URLSearchParams({
      order_value:           String(params.order_value          ?? 0),
      contract_type:         params.contract_type               ?? 'standard',
      customer_tier:         params.customer_tier               ?? 'standard',
      predicted_delay_days:  String(params.predicted_delay_days ?? 0),
      otif_threshold_pct:    '95',
      use_llm:               String(params.use_llm              ?? false),
      tenant_id:             params.tenant_id                   ?? 'default_tenant',
      ...(params.otif_actual_pct != null ? { otif_actual_pct: String(params.otif_actual_pct) } : {}),
    });
    const fd = new FormData();
    fd.append('file', file);
    const response = await fetch(`${API_BASE_URL}/sla/analyze?${qs}`, {
      method: 'POST',
      headers: getAuthHeader(),
      body: fd,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'SLA analysis failed' }));
      throw new Error(err.detail || 'SLA analysis failed');
    }
    return await response.json();
  },

  /** POST /sla/parse — extract clauses only (no penalty calculation) */
  async parseSLAContract(file: File, useLlm = false, tenantId = 'default_tenant') {
    const fd = new FormData();
    fd.append('file', file);
    const response = await fetch(
      `${API_BASE_URL}/sla/parse?use_llm=${useLlm}&tenant_id=${tenantId}`,
      { method: 'POST', headers: getAuthHeader(), body: fd }
    );
    if (!response.ok) throw new Error('SLA parse failed');
    return await response.json();
  },

  /** POST /sla/negotiate — LLM negotiation strategy from supplier data + clauses */
  async generateSLANegotiation(supplierData: Record<string, any>, contractClauses?: any[], tenantId = 'default_tenant') {
    const response = await fetch(`${API_BASE_URL}/sla/negotiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ supplier_data: supplierData, contract_clauses: contractClauses, tenant_id: tenantId }),
    });
    if (!response.ok) throw new Error('SLA negotiate failed');
    return await response.json();
  },

  /** POST /api/v1/documents/upload — multipart document upload for vision analysis */
  async uploadDocument(file: File, shipmentId?: number) {
    const formData = new FormData();
    formData.append('file', file);
    const url = shipmentId
      ? `${API_BASE_URL}/api/v1/documents/upload?shipment_id=${shipmentId}`
      : `${API_BASE_URL}/api/v1/documents/upload`;
    const response = await fetch(url, {
      method: 'POST',
      headers: getAuthHeader(),
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Document upload failed');
    }
    return await response.json();
  },
};
