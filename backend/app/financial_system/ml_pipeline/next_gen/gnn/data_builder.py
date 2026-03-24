import pandas as pd
from torch_geometric.data import Data
from sqlalchemy import create_engine, text
import os

DB_URL = f"postgresql://admin:password123@localhost:5433/fiscalogix"

def build_graph_data(shipment_df, node_df):
    """
    Converts Analytics Warehouse Dataframes into a PyTorch Geometric Graph Object.
    - Nodes: Locations/Origins/Destinations
    - Edges: Shipments/Routes
    - Features: Aggregated shipment metrics per node
    """
    # 1. Unique ID Mapping
    all_nodes = list(node_df["node_id"].unique())
    node_map = {node_id: i for i, node_id in enumerate(all_nodes)}
    
    # 2. Extract Node Features
    # Example: Safety Stock, Demand, etc.
    x = torch.tensor(node_df[["avg_daily_demand", "safety_stock"]].values, dtype=torch.float)
    
    # 3. Build Connectivity (Edges)
    # Origin -> Destination
    edge_list = []
    edge_attr = []
    
    for _, row in shipment_df.iterrows():
        try:
            u = node_map[row["origin"]]
            v = node_map[row["destination"]]
            edge_list.append([u, v])
            # Features on the edge (the shipment itself)
            edge_attr.append([row["order_value"], row["total_cost"]])
        except KeyError:
            continue
            
    edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
    edge_features = torch.tensor(edge_attr, dtype=torch.float)
    
    return Data(x=x, edge_index=edge_index, edge_attr=edge_features)

def build_from_db():
    """
    Connects to the Analytics Warehouse and returns a Graph Data object.
    """
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        shipment_df = pd.read_sql("SELECT * FROM dw_shipment_facts", conn)
        node_df = pd.read_sql("SELECT * FROM dw_node_dimensions", conn)
        
    return build_graph_data(shipment_df, node_df)

