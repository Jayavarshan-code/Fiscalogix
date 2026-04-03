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
  }
};
