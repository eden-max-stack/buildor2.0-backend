import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv, GlobalAttention

class CodeEncoder(nn.Module):
    """
    Encodes a code graph (AST+CFG+DFG) into node embeddings.
    """
    def __init__(self, input_dim, hidden_dim, heads=4):
        super(CodeEncoder, self).__init__()
        # GAT allows the model to weigh DFG edges differently from AST edges
        self.conv1 = GATConv(input_dim, hidden_dim, heads=heads, dropout=0.2)
        self.conv2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, dropout=0.2)
        
    def forward(self, x, edge_index):
        # x: Node features [Num_Nodes, Input_Dim]
        # edge_index: Graph connectivity [2, Num_Edges]
        x = F.elu(self.conv1(x, edge_index))
        x = F.elu(self.conv2(x, edge_index))
        return x

class CrossGraphAttention(nn.Module):
    """
    Aligns 'User Code' nodes with 'Optimal Code' nodes.
    Query = User Nodes, Key/Value = Optimal Nodes
    """
    def __init__(self, embed_dim):
        super(CrossGraphAttention, self).__init__()
        self.attn = nn.MultiheadAttention(embed_dim, num_heads=4, batch_first=True)
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, user_emb, optimal_emb):
        # user_emb: [Batch, User_Nodes, Dim]
        # optimal_emb: [Batch, Opt_Nodes, Dim]
        
        # Standard Attention: Q=User, K=Opt, V=Opt
        context, _ = self.attn(user_emb, optimal_emb, optimal_emb)
        return self.norm(user_emb + context)

class HintGeneratorGNN(nn.Module):
    def __init__(self, input_dim=64, hidden_dim=128, num_classes=5):
        super(HintGeneratorGNN, self).__init__()
        
        self.encoder = CodeEncoder(input_dim, hidden_dim)
        self.cross_attn = CrossGraphAttention(hidden_dim)
        
        # Task 1: Bug Classification (Global Graph Level)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes) # e.g., Logic Error, Syntax, etc.
        )
        
        # Task 2: Error Localization (Node Level)
        # Prob(Node is buggy)
        self.localizer = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, user_data, opt_data):
        # 1. Encode both graphs independently
        u_emb = self.encoder(user_data.x, user_data.edge_index) # [N_u, Dim]
        o_emb = self.encoder(opt_data.x, opt_data.edge_index)   # [N_o, Dim]
        
        # 2. Cross Attention (Simplified for batching)
        # For V1, we simply pool the Optimal Graph to get a "Context Vector"
        # and append it to every User Node. This is computationally cheaper.
        o_context = torch.mean(o_emb, dim=0, keepdim=True) # [1, Dim]
        combined_emb = u_emb + o_context # Broadcasting
        
        # 3. Predictions
        
        # A. Where is the bug? (Node Level)
        loc_logits = self.localizer(combined_emb)
        
        # B. What type of bug? (Graph Level)
        # Pool user nodes into a single graph vector
        graph_emb = torch.mean(combined_emb, dim=0)
        cls_logits = self.classifier(graph_emb)
        
        return cls_logits, loc_logits