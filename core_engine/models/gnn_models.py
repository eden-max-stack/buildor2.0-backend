import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv

NUM_EDIT_TYPES = 6  # none, replace_operator, replace_comparison, replace_logical, replace_boolean, replace_constant


class AttentionPooling(nn.Module):
    """Learned attention pooling — weights important nodes over uniform mean pooling."""
    def __init__(self, hidden_dim):
        super().__init__()
        self.attn = nn.Linear(hidden_dim, 1)

    def forward(self, x):  # x: [N, H]
        w = torch.softmax(self.attn(x), dim=0)  # [N, 1]
        return (w * x).sum(dim=0)               # [H]


class CodeEncoder(nn.Module):
    """5-layer GAT with pre-norm residuals and Jumping Knowledge concat (layers 2, 4, 5)."""
    def __init__(self, num_node_types, embed_dim, hidden_dim, heads=4, num_layers=5):
        super().__init__()
        self.node_embedding = nn.Embedding(num_node_types, embed_dim)
        self.input_proj = nn.Linear(embed_dim, hidden_dim)

        self.convs = nn.ModuleList([
            GATConv(hidden_dim, hidden_dim, heads=heads, dropout=0.3, concat=False)
            for _ in range(num_layers)
        ])
        self.norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers)])
        self.dropout = nn.Dropout(0.3)

        # JK: concat outputs from layers 2, 4, 5 (0-indexed: 1, 3, 4) — shallow + mid + deep
        self.jk_proj = nn.Linear(hidden_dim * 3, hidden_dim)

    def forward(self, x_type_ids, edge_index):
        x = F.elu(self.input_proj(self.node_embedding(x_type_ids)))  # [N, H]
        h = x
        layer_outs = []
        for conv, norm in zip(self.convs, self.norms):
            h_new = F.elu(conv(norm(h), edge_index))  # pre-norm GAT
            h_new = self.dropout(h_new)
            h = h + h_new                              # residual connection
            layer_outs.append(h)
        # Jumping Knowledge: combine shallow syntactic + mid + deep semantic features
        jk = torch.cat([layer_outs[1], layer_outs[3], layer_outs[4]], dim=-1)
        return self.jk_proj(jk)  # [N, H]


class HintGeneratorGNN(nn.Module):
    def __init__(self, num_node_types, embed_dim=64, hidden_dim=128, num_classes=3,
                 num_patch_classes=39, num_edit_types=NUM_EDIT_TYPES):
        super().__init__()

        # 1. ENCODER — 5-layer JK-GNN
        self.encoder = CodeEncoder(num_node_types, embed_dim, hidden_dim)

        # 2. CROSS-ATTENTION
        self.cross_attn = nn.MultiheadAttention(hidden_dim, num_heads=4, batch_first=True)
        self.norm = nn.LayerNorm(hidden_dim)

        # 3. ATTENTION POOLING (replaces mean pooling)
        self.attn_pool = AttentionPooling(hidden_dim)

        # --- HEAD 1: BUG CLASSIFIER — global diff + localizer-attended vec ---
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(64, num_classes),
        )

        # --- HEAD 2: LOCALIZER — per-node suspicion score ---
        self.localizer = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
        )

        # --- HEAD 3: EDIT-TYPE — what kind of fix is needed ---
        self.edit_type_head = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_edit_types),
        )

        # --- HEAD 4: PATCH TOKEN — rich diff features [u | ctx | |u-ctx| | u*ctx] ---
        self.patch_decoder = nn.Sequential(
            nn.Linear(hidden_dim * 4, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_patch_classes),
        )

    def forward(self, user_data, opt_data):
        # A. Encode both graphs
        u_emb = self.encoder(user_data.x, user_data.edge_index)  # [N_u, H]
        o_emb = self.encoder(opt_data.x, opt_data.edge_index)    # [N_o, H]

        # B. Cross-attention: user queries against optimal keys/values
        u_seq = u_emb.unsqueeze(0)
        o_seq = o_emb.unsqueeze(0)
        context, _ = self.cross_attn(u_seq, o_seq, o_seq)
        context = context.squeeze(0)
        combined = self.norm(u_emb + context)  # [N_u, H]

        # C. LOCALIZATION
        loc_logits = self.localizer(combined)  # [N_u, 1]

        # D. ATTENTION POOLING for global signal
        u_pool = self.attn_pool(u_emb)                                           # [H]
        o_pool = self.attn_pool(o_emb)                                           # [H]
        diff_vec = torch.abs(u_pool - o_pool)                                    # [H]
        loc_weights = torch.softmax(loc_logits.squeeze(-1), dim=0)
        attended_vec = (loc_weights.unsqueeze(-1) * combined).sum(dim=0)         # [H]
        cls_input = torch.cat([diff_vec, attended_vec], dim=0)                   # [2H]

        # E. CLASSIFICATION
        cls_logits = self.classifier(cls_input)

        # F. EDIT-TYPE
        edit_logits = self.edit_type_head(cls_input)

        # G. PATCH — explicit user vs aligned-optimal diff features
        patch_input = torch.cat([
            u_emb,
            context,
            torch.abs(u_emb - context),
            u_emb * context,
        ], dim=-1)  # [N_u, 4H]
        patch_logits = self.patch_decoder(patch_input)

        return cls_logits, loc_logits, patch_logits, edit_logits