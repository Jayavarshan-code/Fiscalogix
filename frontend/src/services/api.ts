export const API_BASE_URL = 'http://localhost:8000';

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
  async getExecutiveOverview(tenantId: string = 'default_tenant') {
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
   * customers: array of { customer_id, order_value, credit_days, historical_defaults?, macro_economic_index? }
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
  }
};
