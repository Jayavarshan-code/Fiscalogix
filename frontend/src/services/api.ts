export const API_BASE_URL = 'http://localhost:8000'; // Assuming standard FastAPI local port

export const apiService = {
  /**
   * Fetch executive dashboard metrics
   */
  async getExecutiveOverview(tenantId: string = 'default_tenant') {
    try {
      const response = await fetch(`${API_BASE_URL}/financial-intelligence?tenant_id=${tenantId}`);
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
      const response = await fetch(`${API_BASE_URL}/predict/shipment/${shipmentId}/insights`);
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
    tenant_id: string;
    action_type: string;
    shipment_id: string;
    erp_target: string;
    confidence_score: number;
    mock_user_id: number;
    parameters?: any;
  }) {
    try {
      const response = await fetch(`${API_BASE_URL}/execution/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('Network response was not ok');
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
      // The router in main.py mounts v1_predict at /api/v1/predict
      const response = await fetch(`${API_BASE_URL}/api/v1/predict/cashflow/trajectory?tenant_id=${tenantId}`);
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error(`Failed to fetch cashflow trajectory:`, error);
      throw error;
    }
  }
};
