import torch
from torch_geometric.nn import SAGEConv
import torch.nn.functional as F

class RiskGNN(torch.nn.Module):
    """
    Enterprise GraphSAGE Risk Architecture.
    Aggregates risk and financial features from neighbor nodes through the supply chain edges.
    """
    def __init__(self, in_channels, hidden_channels, out_channels):
        super(RiskGNN, self).__init__()
        # Layer 1: Learn patterns from immediate neighbors
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        # Layer 2: Learn patterns from neighbors of neighbors (Multi-Echelon Propagation)
        self.conv2 = SAGEConv(hidden_channels, hidden_channels)
        # Output: MLP for binary risk classification
        self.lin = torch.nn.Linear(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        # x: Node feature matrix [num_nodes, in_channels]
        # edge_index: Graph connectivity [2, num_edges]
        
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)
        
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        
        x = self.lin(x)
        return F.log_softmax(x, dim=1)
