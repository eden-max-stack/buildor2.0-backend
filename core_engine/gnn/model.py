import torch
import torch.nn.functional as F
from torch.nn import Linear, Sequential, ReLU, Dropout, MultiheadAttention
from torch_geometric.nn import HeteroConv, GCNConv, SAGEConv, global_mean_pool

class CrossAttentionHintGNN(torch.nn.Module):
    def __init__(self, hidden_channels, num_bug_types, num_patch_types, metadata):
        super().__init__()
        
        # --- 1. Graph Encoders (The Backbone) ---
        # We use two layers of Heterogeneous Convolution to learn node embeddings
        self.conv1 = HeteroConv({
            ('ast_node', 'child', 'ast_node'): GCNConv(-1, hidden_channels),
            ('cfg_node', 'flow', 'cfg_node'): SAGEConv(-1, hidden_channels),
            ('dfg_node', 'data_flow', 'dfg_node'): SAGEConv(-1, hidden_channels),
            # Cross-graph edges
            ('cfg_node', 'maps_to', 'ast_node'): SAGEConv(-1, hidden_channels),
            ('dfg_node', 'maps_to', 'ast_node'): SAGEConv(-1, hidden_channels),
        }, aggr='sum')
        
        self.conv2 = HeteroConv({
            ('ast_node', 'child', 'ast_node'): GCNConv(hidden_channels, hidden_channels),
            ('cfg_node', 'flow', 'cfg_node'): SAGEConv(hidden_channels, hidden_channels),
            ('dfg_node', 'data_flow', 'dfg_node'): SAGEConv(hidden_channels, hidden_channels),
            ('cfg_node', 'maps_to', 'ast_node'): SAGEConv(hidden_channels, hidden_channels),
            ('dfg_node', 'maps_to', 'ast_node'): SAGEConv(hidden_channels, hidden_channels),
        }, aggr='sum')

        # --- 2. Cross-Attention (Comparison Layer) ---
        # This allows the User Nodes to "attend" to the Optimal Nodes
        self.cross_attn = MultiheadAttention(
            embed_dim=hidden_channels, 
            num_heads=4, 
            batch_first=True
        )

        # --- 3. Task Heads ---
        # Input size is doubled because we concat (User_Emb + Context_Emb)
        
        # Head A: Global Bug Type (Is the logic wrong?)
        self.bug_type_head = Sequential(
            Linear(hidden_channels * 2, hidden_channels),
            ReLU(),
            Dropout(0.2),
            Linear(hidden_channels, num_bug_types)
        )

        # Head B: Error Localization (Which node is buggy?)
        self.localization_head = Sequential(
            Linear(hidden_channels * 2, hidden_channels),
            ReLU(),
            Linear(hidden_channels, 1) # Binary prob (0=Safe, 1=Bug)
        )

        # Head C: Patch Proposal (How to fix it?)
        self.patch_head = Sequential(
            Linear(hidden_channels * 2, hidden_channels),
            ReLU(),
            Linear(hidden_channels, num_patch_types)
        )

    def encode_graph(self, x_dict, edge_index_dict):
        """Passes a graph through the backbone to get node embeddings"""
        x_dict = self.conv1(x_dict, edge_index_dict)
        x_dict = {key: x.relu() for key, x in x_dict.items()}
        x_dict = self.conv2(x_dict, edge_index_dict)
        x_dict = {key: x.relu() for key, x in x_dict.items()}
        # We focus on AST nodes as the primary representation
        return x_dict['ast_node']

    def forward(self, user_data, opt_data):
        # 1. Encode both graphs independently
        user_node_emb = self.encode_graph(user_data.x_dict, user_data.edge_index_dict)
        opt_node_emb = self.encode_graph(opt_data.x_dict, opt_data.edge_index_dict)
        
        # 2. Cross-Attention
        # We treat User Nodes as Queries (Q) and Optimal Nodes as Keys/Values (K, V)
        # Add batch dimension [1, Num_Nodes, Hidden] since we processing one pair
        query = user_node_emb.unsqueeze(0)
        key = opt_node_emb.unsqueeze(0)
        value = opt_node_emb.unsqueeze(0)
        
        # aligned_context: For each user node, a weighted sum of relevant optimal nodes
        aligned_context, attn_weights = self.cross_attn(query, key, value)
        aligned_context = aligned_context.squeeze(0) # Remove batch dim

        # 3. Create "Context-Aware" Embeddings
        # Combine the User's reality with the Aligned Optimal expectation
        node_context_emb = torch.cat([user_node_emb, aligned_context], dim=1)

        # 4. Predictions
        
        # Localization & Patching (Node Level)
        loc_logits = self.localization_head(node_context_emb)
        patch_logits = self.patch_head(node_context_emb)
        
        # Bug Type (Graph Level)
        # We pool the node representations to get a whole-graph vector
        # Note: In a real batch, use the batch vector. For single inference, simple mean is fine.
        graph_context_emb = torch.mean(node_context_emb, dim=0, keepdim=True)
        bug_type_logits = self.bug_type_head(graph_context_emb)

        return bug_type_logits, loc_logits, patch_logits, attn_weights