import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.data import Data
import json
import random
import sys
import os

# Imports
from app.services.graph_service import GraphService
from core_engine.models.gnn_models import HintGeneratorGNN
from core_engine.mutator import generate_buggy_code

# --- Config ---
DATASET_PATH = 'human-eval-v2-20210705.jsonl'
LOG_FILE = 'train_output.txt'  # New Config
EPOCHS = 50
LR = 0.001
EMBED_DIM = 64
BUG_TYPES = ["None", "Operator Error", "Logic Error", "Missing Return", "Syntax"]
TYPE_TO_IDX = {t: i for i, t in enumerate(BUG_TYPES)}

# This acts as the model's "Vocabulary"
NODE_TYPE_VECTORS = {} 

def get_node_vector(node_type, dim):
    """Returns a STABLE random vector for a given node type"""
    if node_type not in NODE_TYPE_VECTORS:
        NODE_TYPE_VECTORS[node_type] = torch.randn(dim)
    return NODE_TYPE_VECTORS[node_type]

def log_print(message):
    """Helper: Prints to console AND appends to file"""
    print(message)
    with open(LOG_FILE, 'a') as f:
        f.write(message + '\n')

def graph_to_tensor(graph_dict):
    """Convert serialized graph dict to PyG Data object"""
    nodes = graph_dict['nodes']
    edges = graph_dict['edges']
    
    # 1. Create Semantic Node Features
    feature_list = []
    
    for node in nodes:
        # Try 'type' (AST) first, then 'ast_node_type' (CFG), then 'label'
        n_type = node.get('type') or node.get('ast_node_type')
        if not n_type:
            n_type = node.get('label', 'UNK')
            
        vec = get_node_vector(str(n_type), EMBED_DIM)
        feature_list.append(vec)

    x = torch.stack(feature_list)
    
    # 2. Create Edge Index
    if not edges:
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long))
        
    src = [e['source'] for e in edges]
    dst = [e['target'] for e in edges]
    edge_index = torch.tensor([src, dst], dtype=torch.long)
    
    return Data(x=x, edge_index=edge_index)

def train():
    # Initialize Log File (Clear previous run)
    with open(LOG_FILE, 'w') as f:
        f.write("--- Starting GNN Training Log ---\n")

    log_print("--- Starting GNN Training (With Logic Fixes) ---")
    
    # 1. Initialize Model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    log_print(f"Device: {device}")
    
    model = HintGeneratorGNN(input_dim=EMBED_DIM, hidden_dim=128, num_classes=len(BUG_TYPES))
    model = model.to(device)
    
    optimizer = optim.Adam(model.parameters(), lr=LR)
    cls_criterion = nn.CrossEntropyLoss()
    # loc_criterion = nn.BCELoss() # Disabled for now

    # 2. Load Data
    problems = []
    with open(DATASET_PATH, 'r') as f:
        for line in f:
            problems.append(json.loads(line))
    log_print(f"Loaded {len(problems)} training problems.")

    # 3. Training Loop
    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        correct_preds = 0
        num_processed = 0 
        
        # Shuffle for stochasticity
        random.shuffle(problems)
        
        # We try 100, but we might skip many if mutator fails
        for i, prob in enumerate(problems[:100]): 
            optimizer.zero_grad()
            
            # A. Prepare Data
            correct_code = prob['prompt'] + prob['canonical_solution']
            
            if random.random() < 0.5:
                # Bug Case
                buggy_code, bug_type, bug_line = generate_buggy_code(correct_code)
                if not buggy_code: 
                    continue # Skip if we couldn't generate a bug
                target_cls = TYPE_TO_IDX.get(bug_type, 0)
                is_buggy = True
            else:
                # Correct Case
                buggy_code = correct_code
                target_cls = TYPE_TO_IDX["None"]
                bug_line = -1
                is_buggy = False

            try:
                # B. Build Graphs
                user_service = GraphService(buggy_code)
                opt_service = GraphService(correct_code)
                
                u_graphs = user_service.build_all_graphs()
                o_graphs = opt_service.build_all_graphs()
                
                # Use AST for better accuracy
                if 'ast' in u_graphs and 'ast' in o_graphs:
                    u_data = u_graphs['ast']
                    o_data = o_graphs['ast']
                else:
                    # Fallback to function CFG
                    if not u_graphs['functions'] or not o_graphs['functions']: continue
                    u_data = u_graphs['functions'][0]['cfg']
                    o_data = o_graphs['functions'][0]['cfg']

                # Convert to Tensors
                t_user = graph_to_tensor(u_data).to(device)
                t_opt = graph_to_tensor(o_data).to(device)

                # C. Forward Pass
                cls_logits, loc_logits = model(t_user, t_opt)
                
                # D. Compute Loss
                loss_cls = cls_criterion(cls_logits.unsqueeze(0), torch.tensor([target_cls], device=device))
                
                loss = loss_cls 
                loss.backward()
                optimizer.step()
                
                num_processed += 1 
                total_loss += loss.item()
                
                pred_cls = torch.argmax(cls_logits).item()
                if pred_cls == target_cls:
                    correct_preds += 1

            except Exception as e:
                log_print(f"[CRITICAL ERROR] Failed on {prob['task_id']}: {str(e)}")
                import traceback
                traceback.print_exc() # This prints the full red error trace to your console
                continue

        # --- Report Stats ---
        if num_processed > 0:
            actual_acc = (correct_preds / num_processed) * 100
            avg_loss = total_loss / num_processed
            log_print(f"Epoch {epoch+1}: Loss = {avg_loss:.4f} | Acc = {actual_acc:.2f}% ({correct_preds}/{num_processed})")
        else:
            log_print(f"Epoch {epoch+1}: Skipped all samples (Mutator found nothing to break)")
        
        # Save Checkpoint
        if (epoch+1) % 10 == 0:
            torch.save(model.state_dict(), f"gnn_model_v1_ep{epoch+1}.pth")
            log_print("Model saved.")

if __name__ == "__main__":
    train()