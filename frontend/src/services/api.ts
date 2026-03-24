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
   * Fetch confidence studio explainability for a specific shipment
   */
  async getConfidenceExplainability(shipmentId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/confidence-studio/explain/${shipmentId}`);
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.error(`Failed to fetch explainability for ${shipmentId}:`, error);
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
  }
};
