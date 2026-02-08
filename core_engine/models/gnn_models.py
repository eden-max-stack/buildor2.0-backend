import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv

class CodeEncoder(nn.Module):
    """Encodes AST/CFG with Learned Embeddings"""
    def __init__(self, num_node_types, embed_dim, hidden_dim, heads=4):
        super(CodeEncoder, self).__init__()
        self.node_embedding = nn.Embedding(num_node_types, embed_dim)
        self.conv1 = GATConv(embed_dim, hidden_dim, heads=heads, dropout=0.2)
        self.conv2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, dropout=0.2)
        
    def forward(self, x_type_ids, edge_index):
        x = self.node_embedding(x_type_ids)
        x = F.elu(self.conv1(x, edge_index))
        x = F.elu(self.conv2(x, edge_index))
        return x

class HintGeneratorGNN(nn.Module):
    def __init__(self, num_node_types, embed_dim=64, hidden_dim=128, num_classes=5):
        super(HintGeneratorGNN, self).__init__()
        
        # 1. ENCODER
        self.encoder = CodeEncoder(num_node_types, embed_dim, hidden_dim)
        
        # 2. CROSS-ATTENTION (For Localization only)
        self.cross_attn = nn.MultiheadAttention(hidden_dim, num_heads=4, batch_first=True)
        self.norm = nn.LayerNorm(hidden_dim)

        # --- HEAD 1: BUG CLASSIFIER (Path A: Subtraction) ---
        # "Find the DIFFERENCE between the graphs"
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes)
        )
        
        # --- HEAD 2: LOCALIZER (Path B: Attention) ---
        # "Find the ALIGNMENT between the graphs"
        self.localizer = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
        # --- HEAD 3: PATCH PROPOSAL ---
        self.patch_decoder = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_node_types) 
        )

    def forward(self, user_data, opt_data):
        # A. Encode
        u_emb = self.encoder(user_data.x, user_data.edge_index) # [N_user, H]
        o_emb = self.encoder(opt_data.x, opt_data.edge_index)   # [N_opt, H]
        
        # --- PATH 1: CLASSIFICATION (The Detector) ---
        # Explicitly subtract the global vectors.
        # This makes "Operator Error" pop out immediately because "+" != "-"
        u_pool = torch.sum(u_emb, dim=0)
        o_pool = torch.sum(o_emb, dim=0)
        diff_vec = torch.abs(u_pool - o_pool)
        
        cls_logits = self.classifier(diff_vec)
        
        # --- PATH 2: LOCALIZATION (The Surgeon) ---
        # Use Attention to map context for finding WHERE the bug is
        u_seq = u_emb.unsqueeze(0) 
        o_seq = o_emb.unsqueeze(0)
        
        context, _ = self.cross_attn(u_seq, o_seq, o_seq) 
        combined = self.norm(u_seq + context).squeeze(0) # [N_user, H]
        
        loc_logits = self.localizer(combined)
        patch_logits = self.patch_decoder(combined)
        
        return cls_logits, loc_logits, patch_logits