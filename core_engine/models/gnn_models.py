import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv

class CodeEncoder(nn.Module):
    """Encodes AST/CFG with Learned Embeddings"""
    def __init__(self, num_node_types, embed_dim, hidden_dim, heads=4):
        super(CodeEncoder, self).__init__()
        self.node_embedding = nn.Embedding(num_node_types, embed_dim)
        self.conv1 = GATConv(embed_dim, hidden_dim, heads=heads, dropout=0.3)
        self.conv2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, dropout=0.3)
        self.dropout = nn.Dropout(0.5)
        
    def forward(self, x_type_ids, edge_index):
        x = self.node_embedding(x_type_ids)
        x = self.dropout(F.elu(self.conv1(x, edge_index)))
        x = self.dropout(F.elu(self.conv2(x, edge_index)))
        return x

class HintGeneratorGNN(nn.Module):
    def __init__(self, num_node_types, embed_dim=64, hidden_dim=128, num_classes=5, num_patch_classes=39):
        super(HintGeneratorGNN, self).__init__()
        
        # 1. ENCODER
        self.encoder = CodeEncoder(num_node_types, embed_dim, hidden_dim)
        
        # 2. CROSS-ATTENTION (For Localization only)
        self.cross_attn = nn.MultiheadAttention(hidden_dim, num_heads=4, batch_first=True)
        self.norm = nn.LayerNorm(hidden_dim)

        # --- HEAD 1: BUG CLASSIFIER ---
        # Uses BOTH global diff + localizer-attended embedding
        # Input: hidden_dim (global diff) + hidden_dim (attended local) = 2*hidden_dim
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(64, num_classes)
        )
        
        # --- HEAD 2: LOCALIZER (Path B: Attention) ---
        # Outputs raw logits (no sigmoid) — use BCEWithLogitsLoss for stability
        self.localizer = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1)
        )
        
        # --- HEAD 3: PATCH PROPOSAL ---
        self.patch_decoder = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_patch_classes) 
        )

    def forward(self, user_data, opt_data):
        # A. Encode both graphs
        u_emb = self.encoder(user_data.x, user_data.edge_index) # [N_user, H]
        o_emb = self.encoder(opt_data.x, opt_data.edge_index)   # [N_opt, H]
        
        # B. Cross-attention: align user nodes against optimal code
        u_seq = u_emb.unsqueeze(0) 
        o_seq = o_emb.unsqueeze(0)
        context, _ = self.cross_attn(u_seq, o_seq, o_seq) 
        combined = self.norm(u_seq + context).squeeze(0) # [N_user, H]
        
        # C. LOCALIZATION — compute first so classifier can use it
        loc_logits = self.localizer(combined)             # [N_user, 1]
        
        # D. CLASSIFICATION — use localizer attention to focus on bug region
        # Global signal: mean-pool difference (detects IF code differs)
        u_pool = torch.mean(u_emb, dim=0)                # [H]
        o_pool = torch.mean(o_emb, dim=0)                # [H]
        diff_vec = torch.abs(u_pool - o_pool)             # [H]
        
        # Local signal: attention-weighted pooling (focuses on WHERE)
        loc_weights = torch.softmax(loc_logits.squeeze(-1), dim=0)  # [N_user]
        attended_vec = (loc_weights.unsqueeze(-1) * combined).sum(dim=0)  # [H]
        
        # Concatenate global + local for classification
        cls_input = torch.cat([diff_vec, attended_vec], dim=0)  # [2*H]
        cls_logits = self.classifier(cls_input)
        
        # E. PATCH PROPOSAL
        patch_logits = self.patch_decoder(combined)
        
        return cls_logits, loc_logits, patch_logits