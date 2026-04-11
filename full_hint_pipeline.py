"""
Full 5-Layer Hint Generation Pipeline
======================================

This script demonstrates how to use the trained MBPP model with the complete
hint generation system, integrating all 5 layers:

Layer 1: Code Property Graph (AST + CFG + DFG)
Layer 2: GNN Encoder
Layer 3: Multi-Task Heads (Classification, Localization, Patch)
Layer 4: Fuzzy Inference (Hint Aggressiveness)
Layer 5: Natural Language Hint Generation

Usage:
    python full_hint_pipeline.py
"""

import torch
import json
import os
import re
from app.services.graph_service import GraphService
from core_engine.models.gnn_models import HintGeneratorGNN
from core_engine.fuzzy_inference import fuzzy_infer, build_hint_context
from core_engine.hint_generator import generate_hint as generate_nl_hint

# --- Configuration ---
MODEL_PATH = 'gnn_model_mbpp_best_new.pth'
VOCAB_PATH = 'vocab_mbpp.json'
EMBED_DIM = 64
MAX_VOCAB_SIZE = 500
BUG_TYPES = ["None", "Operator Error", "Logic Error"]
BUG_MAP = {i: t for i, t in enumerate(BUG_TYPES)}

# Load vocabulary
NODE_TYPE_MAP = {"UNK": 0}
if os.path.exists(VOCAB_PATH):
    with open(VOCAB_PATH, 'r') as f:
        NODE_TYPE_MAP = json.load(f)
    print(f"Loaded vocabulary with {len(NODE_TYPE_MAP)} types.")
else:
    print(f"⚠ WARNING: {VOCAB_PATH} not found! Using default vocab.")

ID_TO_TOKEN = {v: k for k, v in NODE_TYPE_MAP.items()}


def get_type_id(node_type):
    """Map AST node type to vocabulary ID"""
    return NODE_TYPE_MAP.get(node_type, 0)


def build_cpg_tensor(graphs_dict):
    """
    Build merged CPG (Code Property Graph) tensor from AST+CFG+DFG.
    This is Layer 1 output prepared for the GNN.
    """
    ast_data = graphs_dict['ast']
    nodes = ast_data.get('nodes', [])
    if not nodes:
        x = torch.tensor([0], dtype=torch.long)
        from torch_geometric.data import Data
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long)), nodes

    # Map AST node IDs to tensor indices
    id_to_idx = {}
    type_ids = []
    for i, node in enumerate(nodes):
        id_to_idx[node['id']] = i
        n_type = node.get('type') or 'UNK'
        type_ids.append(get_type_id(str(n_type)))

    x = torch.tensor(type_ids, dtype=torch.long)
    all_src, all_dst = [], []

    # Add AST edges
    for e in ast_data.get('edges', []):
        s, d = id_to_idx.get(e['source']), id_to_idx.get(e['target'])
        if s is not None and d is not None:
            all_src.append(s)
            all_dst.append(d)

    # Add CFG edges (mapped through AST node IDs)
    for func in graphs_dict.get('functions', []):
        cfg = func.get('cfg', {})
        cfg_to_ast = {n['id']: n.get('ast_node_id') for n in cfg.get('nodes', [])}
        for e in cfg.get('edges', []):
            a_s, a_d = cfg_to_ast.get(e['source']), cfg_to_ast.get(e['target'])
            if a_s is not None and a_d is not None:
                s, d = id_to_idx.get(a_s), id_to_idx.get(a_d)
                if s is not None and d is not None:
                    all_src.append(s)
                    all_dst.append(d)

    # Add DFG edges (mapped through AST node IDs)
    for func in graphs_dict.get('functions', []):
        dfg = func.get('dfg', {})
        dfg_to_ast = {n['id']: n.get('ast_node_id') for n in dfg.get('nodes', [])}
        for e in dfg.get('edges', []):
            a_s, a_d = dfg_to_ast.get(e['source']), dfg_to_ast.get(e['target'])
            if a_s is not None and a_d is not None:
                s, d = id_to_idx.get(a_s), id_to_idx.get(a_d)
                if s is not None and d is not None:
                    all_src.append(s)
                    all_dst.append(d)

    if not all_src:
        from torch_geometric.data import Data
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long)), nodes
    
    edge_index = torch.tensor([all_src, all_dst], dtype=torch.long)
    
    # Create PyTorch Geometric Data object
    from torch_geometric.data import Data
    return Data(x=x, edge_index=edge_index), nodes


def _extract_buggy_token_from_line(line: str) -> str:
    # Minimal heuristic: try to find a likely operator/comparison token in the suspicious line.
    # If none found, return a placeholder.
    candidates = [
        "<=", ">=", "==", "!=",
        "+", "-", "*", "/",
        ">", "<",
        "True", "False",
    ]
    for tok in candidates:
        if tok in line:
            return tok
    # fallback: last non-whitespace symbol-ish chunk
    m = re.findall(r"[+\-*/<>!=]=?|True|False", line)
    return m[-1] if m else "?"


def generate_hint_pipeline(buggy_code, correct_code=None, tests_failed_ratio=0.5, skill_level="medium"):
    """
    Complete 5-layer hint generation pipeline.
    
    Args:
        buggy_code: Student's buggy submission
        correct_code: Optional reference solution (for training-style analysis)
        tests_failed_ratio: Fraction of test cases that failed (0.0 to 1.0)
        skill_level: Student skill level ("low", "medium", "high")
    
    Returns:
        dict with hint text, bug analysis, and metadata
    """
    print("FULL 5-LAYER HINT GENERATION PIPELINE")

    print("\nUser (buggy) code:")
    print("-" * 60)
    print(buggy_code.strip() or "<empty>")
    print("-" * 60)

    if correct_code is not None:
        print("\nOptimal/reference (correct) code:")
        print("-" * 60)
        print(correct_code.strip() or "<empty>")
        print("-" * 60)
    else:
        print("\nOptimal/reference (correct) code: <not provided>")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    
    # ========== LAYER 1: Build Code Property Graph ==========
    print("\n[Layer 1] Building Code Property Graph (AST + CFG + DFG)...")
    try:
        u_graphs = GraphService(buggy_code).build_all_graphs()
        t_user, u_nodes = build_cpg_tensor(u_graphs)
        t_user = t_user.to(device)
        print(f"  Built graph with {t_user.x.shape[0]} nodes, {t_user.edge_index.shape[1]} edges")
        
        # If correct code provided, build its graph too
        if correct_code:
            o_graphs = GraphService(correct_code).build_all_graphs()
            t_opt, _ = build_cpg_tensor(o_graphs)
            t_opt = t_opt.to(device)
        else:
            # Use buggy code as reference (model will detect no bug)
            t_opt = t_user
            
    except Exception as e:
        return {
            "error": f"Graph construction failed: {e}",
            "hint": "Unable to analyze code structure. Please check for syntax errors."
        }
    
    # ========== LAYER 2-3: GNN Inference ==========
    print("\n[Layer 2-3] Running GNN (Encoder + Multi-Task Heads)...")
    
    # Load trained model
    model = HintGeneratorGNN(
        MAX_VOCAB_SIZE, 
        EMBED_DIM, 
        128, 
        len(BUG_TYPES), 
        num_patch_classes=39
    ).to(device)
    
    try:
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        print(f"  Loaded model from {MODEL_PATH}")
    except FileNotFoundError:
        return {
            "error": f"Model file not found: {MODEL_PATH}",
            "hint": "Model not trained yet. Please run training first."
        }
    
    model.eval()
    
    with torch.no_grad():
        cls_logits, loc_logits, patch_logits, edit_logits = model(t_user, t_opt)
    
    if cls_logits.dim() == 1:
        cls_logits = cls_logits.unsqueeze(0)
    
    # Parse outputs
    pred_idx = torch.argmax(cls_logits).item()
    confidence = torch.softmax(cls_logits, dim=1)[0][pred_idx].item()
    bug_type = BUG_MAP.get(pred_idx, "Unknown")
    
    print(f"  Bug Classification: {bug_type} ({confidence*100:.1f}% confidence)")
    
    # Localization
    loc_probs = torch.sigmoid(loc_logits).squeeze(-1)
    pred_bug_node = torch.argmax(loc_probs).item()
    
    line_scores = {}
    for idx, node in enumerate(u_nodes):
        line = node.get('start_line', -1)
        prob = loc_probs[idx].item()
        if line > 0:
            line_scores[line] = max(line_scores.get(line, 0), prob)
    
    sorted_lines = sorted(line_scores.items(), key=lambda x: x[1], reverse=True)
    bug_line = sorted_lines[0][0] if sorted_lines else -1
    bug_line_confidence = sorted_lines[0][1] if sorted_lines else 0.0
    
    print(f"  Bug Localization: Line {bug_line} ({bug_line_confidence*100:.1f}% suspiciousness)")
    
    # Patch suggestion
    patch_token = None
    if pred_idx != 0 and pred_bug_node < len(u_nodes):
        patch_pred = torch.argmax(patch_logits[pred_bug_node]).item()
        patch_token = ID_TO_TOKEN.get(patch_pred, "?")
        print(f"  Patch Suggestion: Replace with `{patch_token}`")
    
    fuzzy_result = fuzzy_infer(
        tests_failed_ratio=tests_failed_ratio,
        model_confidence=confidence,
        skill_level=skill_level,
    )

    hint_style = fuzzy_result.hint_style
    hint_detail = fuzzy_result.hint_detail

    print(f"  Hint Style: {hint_style} (detail level: {hint_detail:.2f})")
    print(f"  Inputs: tests_failed={tests_failed_ratio:.1%}, confidence={confidence:.1%}, skill={skill_level}")

    source_lines = buggy_code.strip().split('\n')
    bug_line_content = source_lines[bug_line-1].strip() if 0 <= bug_line-1 < len(source_lines) else "???"

    buggy_token = _extract_buggy_token_from_line(bug_line_content)
    original_token = patch_token or "?"

    hint_context = build_hint_context(
        bug_type=bug_type,
        bug_line=bug_line,
        original_token=original_token,
        buggy_token=buggy_token,
        fuzzy=fuzzy_result,
        code_snippet=bug_line_content,
    )

    hint_payload = generate_nl_hint(hint_context, max_words=40)
    hint_text = hint_payload.get("hint_text", "")

    print(f"  Generated hint ({len(hint_text.split())} words)")
    
    # ========== Final Output ==========
    print("HINT FOR STUDENT:")
    print(f"\n{hint_text}\n")
    
    return {
        "hint": hint_text,
        "analysis": {
            "bug_type": bug_type,
            "confidence": confidence,
            "bug_line": bug_line,
            "bug_line_confidence": bug_line_confidence,
            "patch_suggestion": patch_token,
            "hint_style": hint_style,
            "hint_detail": hint_detail,
        },
        "inputs": {
            "tests_failed_ratio": tests_failed_ratio,
            "skill_level": skill_level,
        }
    }


# ========== Example Usage ==========
if __name__ == "__main__":
    print("EXAMPLE 1: Operator Error (- instead of +)")
    
    buggy_code_1 = """
def add(a, b):
    return a - b
"""
    
    correct_code_1 = """
def add(a, b):
    return a + b
"""
    
    result1 = generate_hint_pipeline(
        buggy_code=buggy_code_1,
        correct_code=correct_code_1,
        tests_failed_ratio=1.0,  # All tests failed
        skill_level="medium"
    )
    
    print("EXAMPLE 2: Logic Error (wrong comparison)")
    
    buggy_code_2 = """
def is_positive(x):
    if x < 0:
        return True
    return False
"""
    
    correct_code_2 = """
def is_positive(x):
    if x > 0:
        return True
    return False
"""
    
    result2 = generate_hint_pipeline(
        buggy_code=buggy_code_2,
        correct_code=correct_code_2,
        tests_failed_ratio=0.5,  # Half tests failed
        skill_level="low"
    )
    
    print("EXAMPLE 3: No Reference Code (Real-world scenario)")
    
    buggy_code_3 = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n + 1)  # Bug: should be n-1
"""

    correct_code_3 = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)  # Bug: should be n-1
"""
    
    result3 = generate_hint_pipeline(
        buggy_code=buggy_code_3,
        correct_code=correct_code_3,
        tests_failed_ratio=0.8,
        skill_level="high"
    )
    
    print("Pipeline demonstration complete!")
