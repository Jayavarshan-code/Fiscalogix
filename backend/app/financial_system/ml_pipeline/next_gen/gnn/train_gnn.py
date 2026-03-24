import torch
import torch.nn.functional as F
from app.financial_system.ml_pipeline.next_gen.gnn.model import RiskGNN
from app.financial_system.ml_pipeline.next_gen.gnn.data_builder import build_graph_data
from pathlib import Path
import pandas as pd
import os

MODEL_PATH = Path(__file__).parent / "models" / "gnn_risk_model.pt"
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

def train_gnn(shipment_df, node_df, epochs=100):
    """
    Trains the GraphSAGE model on warehouse data.
    """
    # 1. Prepare Graph Data
    data = build_graph_data(shipment_df, node_df)
    
    # 2. Define labels (this is just for demonstration, real labels would come from dw_risk_events)
    # Binary classification: High Risk (1) vs Low Risk (0)
    # We'll use a mock target for now based on some node features
    data.y = (data.x[:, 0] > 100).long() # If demand > 100, mark as risky
    
    # 3. Model Setup
    model = RiskGNN(in_channels=data.num_node_features, hidden_channels=16, out_channels=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        out = model(data.x, data.edge_index)
        loss = F.nll_loss(out, data.y)
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0:
            print(f"Epoch {epoch}, Loss: {loss.item():.4f}")
            
    # 4. Save model state
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"GNN Model saved to {MODEL_PATH}")
    return model

if __name__ == "__main__":
    # Mock data for initial training test
    s_df = pd.DataFrame([{"origin": "NYC", "destination": "LON", "order_value": 50000, "total_cost": 5000}])
    n_df = pd.DataFrame([{"node_id": "NYC", "avg_daily_demand": 150, "safety_stock": 20},
                         {"node_id": "LON", "avg_daily_demand": 80, "safety_stock": 10}])
    train_gnn(s_df, n_df)
