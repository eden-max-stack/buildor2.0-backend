import torch
import torch.nn as nn
from torch_geometric.data import Data
import os
import json

# Imports
from app.services.graph_service import GraphService
from core_engine.models.gnn_models import HintGeneratorGNN

# --- CONFIG ---
MODEL_PATH = "gnn_model_v3_ep50.pth"
VOCAB_PATH = "vocab.json" # <--- Load the map
EMBED_DIM = 64
MAX_VOCAB_SIZE = 500
BUG_TYPES = ["None", "Operator Error", "Logic Error", "Missing Return", "Syntax"]
BUG_MAP = {i: t for i, t in enumerate(BUG_TYPES)}

# Load Vocab
NODE_TYPE_MAP = {"UNK": 0}
if os.path.exists(VOCAB_PATH):
    with open(VOCAB_PATH, 'r') as f:
        NODE_TYPE_MAP = json.load(f)
    print(f"Loaded vocabulary with {len(NODE_TYPE_MAP)} types.")
else:
    print("WARNING: vocab.json not found! Inference will be random.")

def get_type_id(node_type):
    return NODE_TYPE_MAP.get(node_type, 0) # Default to UNK(0) if not seen during training

def graph_to_tensor(graph_dict):
    nodes = graph_dict['nodes']
    edges = graph_dict['edges']
    
    type_ids = []
    debug_types = []

    for node in nodes:
        n_type = node.get('type') or node.get('ast_node_type') or 'UNK'
        if n_type in ["+", "-", "*", "/", "binary_operator"]:
            debug_types.append(n_type)
        type_ids.append(get_type_id(str(n_type)))

    if debug_types:
        print(f"   [Vision Test] Found operators: {debug_types}")

    x = torch.tensor(type_ids, dtype=torch.long)
    
    if not edges:
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long))
        
    src = [e['source'] for e in edges]
    dst = [e['target'] for e in edges]
    edge_index = torch.tensor([src, dst], dtype=torch.long)
    return Data(x=x, edge_index=edge_index)

def predict(buggy_code, correct_code):
    print("\n--- ANALYZING CODE ---")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Load Model
    model = HintGeneratorGNN(MAX_VOCAB_SIZE, EMBED_DIM, 128, len(BUG_TYPES))
    try:
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        print("Model loaded successfully.")
    except FileNotFoundError:
        print(f"Error: Could not find {MODEL_PATH}")
        return

    model = model.to(device)
    model.eval()

    # Build Graphs
    try:
        u_graphs = GraphService(buggy_code).build_all_graphs()
        u_data = u_graphs['ast']
        
        o_graphs = GraphService(correct_code).build_all_graphs()
        o_data = o_graphs['ast']
        
        t_user = graph_to_tensor(u_data).to(device)
        t_opt = graph_to_tensor(o_data).to(device)
        
    except Exception as e:
        print(f"Graph Build Error: {e}")
        return

    # Predict
    with torch.no_grad():
        cls_logits, loc_logits, patch_logits = model(t_user, t_opt)

    # Reshape if needed
    if cls_logits.dim() == 1:
        cls_logits = cls_logits.unsqueeze(0)

    # Interpret Results
    pred_idx = torch.argmax(cls_logits).item()
    confidence = torch.softmax(cls_logits, dim=1)[0][pred_idx].item()
    print(f"\n[DIAGNOSIS]: {BUG_MAP[pred_idx]} ({confidence*100:.1f}% confidence)")

    # Localization Heatmap
    print("\n[SUSPICIOUS LINES]:")
    line_scores = {}
    
    for idx, score in enumerate(loc_logits):
        node_info = u_data['nodes'][idx]
        line = node_info.get('start_line', -1)
        prob = score.item()
        
        if line > 0:
            if line not in line_scores: line_scores[line] = 0
            line_scores[line] = max(line_scores[line], prob)

    sorted_lines = sorted(line_scores.items(), key=lambda x: x[1], reverse=True)
    
    source_lines = buggy_code.strip().split('\n')
    for line_num, score in sorted_lines[:3]:
        bar = "|" * int(score * 10)
        # Safe access to line content
        code_content = source_lines[line_num-1].strip() if 0 <= line_num-1 < len(source_lines) else "???"
        print(f"Line {line_num}: {bar} {score:.4f} >> {code_content}")

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