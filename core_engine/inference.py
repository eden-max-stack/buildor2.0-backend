import torch
import torch.nn.functional as F
from app.services.graph_service import GraphService
from core_engine.gnn.converter import GraphToPyGConverter
from core_engine.gnn.model import CrossAttentionHintGNN

# --- 1. Setup Data ---

# The User's submission (Has a bug: Uses '*' instead of '+')
user_code = """
def example(x):
    y = x + 1
    if x > 0:
        z = y * 2 # Bug here?
        print(z)
    result = z * y # BUG: Should be +
    return result
"""

# The "Reference Bank" - Different valid ways to solve it
optimal_solutions = [
    # Variant A: Standard
    """
    def example(x):
        y = x + 1
        if x > 0:
            z = y * 2
            print(z)
        else:
            z = y * 3
            print(z)
        result = z + y
        return result
    """,
    # Variant B: Maybe a different variable name or slight logic shift
    """
    def example(val):
        a = val + 1
        b = 0
        if val > 0:
            b = a * 2
            print(b)
        else:
            b = a * 3
            print(b)
        res = b + a
        return res
    """
]

# --- 2. Helper Function ---
def process_code_to_tensor(code_str, converter):
    service = GraphService(code_str)
    raw_graphs = service.get_raw_graphs()
    data = converter.convert(raw_graphs)
    return data

# --- 3. Pipeline Execution ---

print("--- Initializing Pipeline ---")
converter = GraphToPyGConverter()

# A. Process User Code
print("Processing User Code...")
user_data = process_code_to_tensor(user_code, converter)

# B. Process Reference Bank
print(f"Processing {len(optimal_solutions)} Reference Solutions...")
opt_dataset = []
for code in optimal_solutions:
    opt_dataset.append(process_code_to_tensor(code, converter))

# C. Initialize Model
# Note: We use user_data.metadata() to tell the HeteroConv what edge types exist
model = CrossAttentionHintGNN(
    hidden_channels=32,
    num_bug_types=5,
    num_patch_types=10,
    metadata=user_data.metadata()
)
model.eval() # Set to inference mode

# D. Find Best Match (Graph Similarity Search)
print("\n--- Searching for Best Reference Match ---")
best_score = -1.0
best_reference = None

with torch.no_grad():
    # 1. Get User Graph Embedding (Mean pool of AST nodes)
    user_node_emb = model.encode_graph(user_data.x_dict, user_data.edge_index_dict)
    user_graph_emb = torch.mean(user_node_emb, dim=0, keepdim=True)

    for i, opt_data in enumerate(opt_dataset):
        # 2. Get Opt Graph Embedding
        opt_node_emb = model.encode_graph(opt_data.x_dict, opt_data.edge_index_dict)
        opt_graph_emb = torch.mean(opt_node_emb, dim=0, keepdim=True)
        
        # 3. Calculate Cosine Similarity
        score = F.cosine_similarity(user_graph_emb, opt_graph_emb).item()
        print(f"  > Similarity with Reference {i}: {score:.4f}")
        
        if score > best_score:
            best_score = score
            best_reference = opt_data

# E. Generate Hints using Best Match
if best_score < 0.6: # Threshold
    print("\n[!] Warning: User strategy does not match any known reference.")
else:
    print(f"\n[+] Selected Best Reference (Score: {best_score:.4f})")
    
    with torch.no_grad():
        bug_logits, loc_logits, patch_logits, attn = model(user_data, best_reference)
        
        # --- Interpret Results ---
        
        # 1. Bug Type
        bug_type_id = torch.argmax(bug_logits).item()
        print(f"\nPredicted Bug Type ID: {bug_type_id}")
        
        # 2. Localization (Find max prob)
        loc_probs = torch.sigmoid(loc_logits)
        buggy_node_idx = torch.argmax(loc_probs).item()
        confidence = loc_probs[buggy_node_idx].item()
        
        print(f"Potential Bug Location (AST Node Index): {buggy_node_idx} (Confidence: {confidence:.2f})")
        
        # 3. Explainability (Attention)
        # Get the attention weights for the buggy node to see what it mapped to
        node_attn = attn[0, buggy_node_idx, :] # [1, Num_Opt_Nodes]
        top_match_idx = torch.argmax(node_attn).item()
        print(f"User Node {buggy_node_idx} aligns most with Reference Node {top_match_idx}")