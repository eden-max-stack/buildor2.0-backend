import torch
import torch.nn as nn
from torch_geometric.data import Data
import os
import json

from app.services.graph_service import GraphService
from core_engine.models.gnn_models import HintGeneratorGNN

# --- CONFIG ---
MODEL_PATH = "gnn_model_best.pth"
VOCAB_PATH = "vocab.json"
EMBED_DIM = 64
MAX_VOCAB_SIZE = 500
BUG_TYPES = ["None", "Operator Error", "Logic Error"]
BUG_MAP = {i: t for i, t in enumerate(BUG_TYPES)}

# Load Vocab
NODE_TYPE_MAP = {"UNK": 0}
if os.path.exists(VOCAB_PATH):
    with open(VOCAB_PATH, 'r') as f:
        NODE_TYPE_MAP = json.load(f)
    print(f"Loaded vocabulary with {len(NODE_TYPE_MAP)} types.")
else:
    print("WARNING: vocab.json not found! Inference will be random.")

# Reverse map: ID -> token name (for patch predictions)
ID_TO_TOKEN = {v: k for k, v in NODE_TYPE_MAP.items()}

def get_type_id(node_type):
    return NODE_TYPE_MAP.get(node_type, 0)


def build_cpg_tensor(graphs_dict):
    """Build merged CPG tensor from AST+CFG+DFG (mirrors prepare_data.py logic)."""
    ast_data = graphs_dict['ast']
    nodes = ast_data.get('nodes', [])
    if not nodes:
        x = torch.tensor([0], dtype=torch.long)
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long)), nodes

    id_to_idx = {}
    type_ids = []
    for i, node in enumerate(nodes):
        id_to_idx[node['id']] = i
        n_type = node.get('type') or 'UNK'
        type_ids.append(get_type_id(str(n_type)))

    x = torch.tensor(type_ids, dtype=torch.long)
    all_src, all_dst = [], []

    for e in ast_data.get('edges', []):
        s, d = id_to_idx.get(e['source']), id_to_idx.get(e['target'])
        if s is not None and d is not None:
            all_src.append(s); all_dst.append(d)

    for func in graphs_dict.get('functions', []):
        cfg = func.get('cfg', {})
        cfg_to_ast = {n['id']: n.get('ast_node_id') for n in cfg.get('nodes', [])}
        for e in cfg.get('edges', []):
            a_s, a_d = cfg_to_ast.get(e['source']), cfg_to_ast.get(e['target'])
            if a_s is not None and a_d is not None:
                s, d = id_to_idx.get(a_s), id_to_idx.get(a_d)
                if s is not None and d is not None:
                    all_src.append(s); all_dst.append(d)

    for func in graphs_dict.get('functions', []):
        dfg = func.get('dfg', {})
        dfg_to_ast = {n['id']: n.get('ast_node_id') for n in dfg.get('nodes', [])}
        for e in dfg.get('edges', []):
            a_s, a_d = dfg_to_ast.get(e['source']), dfg_to_ast.get(e['target'])
            if a_s is not None and a_d is not None:
                s, d = id_to_idx.get(a_s), id_to_idx.get(a_d)
                if s is not None and d is not None:
                    all_src.append(s); all_dst.append(d)

    if not all_src:
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long)), nodes
    edge_index = torch.tensor([all_src, all_dst], dtype=torch.long)
    return Data(x=x, edge_index=edge_index), nodes


def predict(buggy_code, correct_code):
    print("\n--- ANALYZING CODE ---")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = HintGeneratorGNN(MAX_VOCAB_SIZE, EMBED_DIM, 128, len(BUG_TYPES), num_patch_classes=39)
    try:
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        print("Model loaded successfully.")
    except FileNotFoundError:
        print(f"Error: Could not find {MODEL_PATH}")
        return

    model = model.to(device)
    model.eval()

    # Build CPG (AST+CFG+DFG merged)
    try:
        u_graphs = GraphService(buggy_code).build_all_graphs()
        o_graphs = GraphService(correct_code).build_all_graphs()
        t_user, u_nodes = build_cpg_tensor(u_graphs)
        t_opt, _ = build_cpg_tensor(o_graphs)
        t_user = t_user.to(device)
        t_opt = t_opt.to(device)
    except Exception as e:
        print(f"Graph Build Error: {e}")
        return

    with torch.no_grad():
        cls_logits, loc_logits, patch_logits = model(t_user, t_opt)

    if cls_logits.dim() == 1:
        cls_logits = cls_logits.unsqueeze(0)

    # Classification
    pred_idx = torch.argmax(cls_logits).item()
    confidence = torch.softmax(cls_logits, dim=1)[0][pred_idx].item()
    print(f"\n[DIAGNOSIS]: {BUG_MAP.get(pred_idx, '?')} ({confidence*100:.1f}% confidence)")

    # Localization — apply sigmoid since model outputs raw logits
    loc_probs = torch.sigmoid(loc_logits).squeeze(-1)
    pred_bug_node = torch.argmax(loc_probs).item()

    print("\n[SUSPICIOUS LINES]:")
    line_scores = {}
    for idx, node in enumerate(u_nodes):
        line = node.get('start_line', -1)
        prob = loc_probs[idx].item()
        if line > 0:
            line_scores[line] = max(line_scores.get(line, 0), prob)

    sorted_lines = sorted(line_scores.items(), key=lambda x: x[1], reverse=True)
    source_lines = buggy_code.strip().split('\n')
    for line_num, score in sorted_lines[:5]:
        bar = "|" * int(score * 20)
        code_content = source_lines[line_num-1].strip() if 0 <= line_num-1 < len(source_lines) else "???"
        print(f"  Line {line_num}: {bar} {score:.4f} >> {code_content}")

    # Patch suggestion at top bug node
    if pred_idx != 0:
        patch_pred = torch.argmax(patch_logits[pred_bug_node]).item()
        suggested_token = ID_TO_TOKEN.get(patch_pred, "?")
        bug_line = u_nodes[pred_bug_node].get('start_line', '?') if pred_bug_node < len(u_nodes) else '?'
        print(f"\n[PATCH SUGGESTION]: Replace token on line {bug_line} with `{suggested_token}`")

    return {
        "bug_type": BUG_MAP.get(pred_idx, "?"),
        "confidence": confidence,
        "bug_line": sorted_lines[0][0] if sorted_lines else -1,
        "patch_token": ID_TO_TOKEN.get(torch.argmax(patch_logits[pred_bug_node]).item(), "?") if pred_idx != 0 else None,
    }


if __name__ == "__main__":
    correct_sample = """
def add(a, b):
    return a + b
"""
    buggy_sample = """
def add(a, b):
    return a - b
"""
    predict(buggy_sample, correct_sample)