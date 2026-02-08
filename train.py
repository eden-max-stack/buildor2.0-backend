import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.data import Data
import json
import random
import sys
import os

from app.services.graph_service import GraphService
from core_engine.models.gnn_models import HintGeneratorGNN
from core_engine.mutator import generate_buggy_code

# --- Config ---
DATASET_PATH = 'human-eval-v2-20210705.jsonl'
LOG_FILE = 'train_output.txt'
VOCAB_FILE = 'vocab.json'   
EPOCHS = 50
LR = 0.001
EMBED_DIM = 64
BUG_TYPES = ["None", "Operator Error", "Logic Error", "Missing Return", "Syntax"]
TYPE_TO_IDX = {t: i for i, t in enumerate(BUG_TYPES)}
MAX_VOCAB_SIZE = 500

# --- VOCABULARY ---
NODE_TYPE_MAP = {"UNK": 0} 
NEXT_ID = 1

def get_type_id(node_type):
    global NEXT_ID
    if node_type not in NODE_TYPE_MAP:
        # If we exceed vocabulary, we clamp to UNK (0) or wrap around
        # For this prototype, we just cap it to avoid crash
        if NEXT_ID >= MAX_VOCAB_SIZE: return 0 
        NODE_TYPE_MAP[node_type] = NEXT_ID
        NEXT_ID += 1
    return NODE_TYPE_MAP[node_type]

def save_vocab():
    """Saves the learned vocabulary so inference uses the same IDs"""
    with open(VOCAB_FILE, 'w') as f:
        json.dump(NODE_TYPE_MAP, f)

def log_print(message):
    print(message)
    with open(LOG_FILE, 'a') as f:
        f.write(message + '\n')

def graph_to_tensor(graph_dict):
    nodes = graph_dict['nodes']
    edges = graph_dict['edges']
    
    type_ids = []
    for node in nodes:
        n_type = node.get('type') or node.get('ast_node_type') or 'UNK'
        type_ids.append(get_type_id(str(n_type)))

    x = torch.tensor(type_ids, dtype=torch.long)
    
    if not edges:
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long))
        
    src = [e['source'] for e in edges]
    dst = [e['target'] for e in edges]
    edge_index = torch.tensor([src, dst], dtype=torch.long)
    return Data(x=x, edge_index=edge_index)

def train():
    with open(LOG_FILE, 'w') as f:
        f.write("--- Starting V3 Training (Detect, Locate, Patch) ---\n")

    log_print("--- Starting V3 Training ---")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = HintGeneratorGNN(MAX_VOCAB_SIZE, EMBED_DIM, 128, len(BUG_TYPES))
    model = model.to(device)
    
    optimizer = optim.Adam(model.parameters(), lr=LR)
    
    class_weights = torch.tensor([1.0, 5.0, 5.0, 5.0, 5.0]).to(device)
    
    # LOSS FUNCTIONS
    criterion_cls = nn.CrossEntropyLoss()
    criterion_loc = nn.BCELoss() # Binary Cross Entropy for "Is this node buggy?"
    criterion_patch = nn.CrossEntropyLoss() # "What token ID belongs here?"

    problems = []
    with open(DATASET_PATH, 'r') as f:
        for line in f:
            problems.append(json.loads(line))
    log_print(f"Loaded {len(problems)} problems.")

    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        correct_cls = 0
        num_processed = 0 
        
        random.shuffle(problems)
        
        for i, prob in enumerate(problems[:100]): 
            optimizer.zero_grad()
            
            correct_code = prob['prompt'] + prob['canonical_solution']
            
            # 1. Generate Bug
            if random.random() < 0.6: # 60% Buggy
                buggy_code, metadata = generate_buggy_code(correct_code)
                if not buggy_code: continue 
                
                target_cls = TYPE_TO_IDX.get(metadata.bug_type, 0)
                is_buggy = True
            else:
                buggy_code = correct_code
                metadata = None
                target_cls = TYPE_TO_IDX["None"]
                is_buggy = False

            try:
                # 2. Build Graphs
                u_graphs = GraphService(buggy_code).build_all_graphs()
                o_graphs = GraphService(correct_code).build_all_graphs()
                
                u_data = u_graphs['ast'] if 'ast' in u_graphs else u_graphs['functions'][0]['cfg']
                o_data = o_graphs['ast'] if 'ast' in o_graphs else o_graphs['functions'][0]['cfg']

                t_user = graph_to_tensor(u_data).to(device)
                t_opt = graph_to_tensor(o_data).to(device)

                # 3. Forward Pass
                cls_out, loc_out, patch_out = model(t_user, t_opt)
                
                # 4. Compute Losses
                
                # A. Classification Loss (Always active)
                loss_cls = criterion_cls(cls_out.unsqueeze(0), torch.tensor([target_cls], device=device))
                
                loss_loc = 0
                loss_patch = 0
                
                if is_buggy and metadata:
                    # B. Localization Target
                    # Find the node in the graph that matches the bug's line number
                    bug_node_idx = -1
                    
                    # Heuristic: Find first node on the bug line
                    for idx, node in enumerate(u_data['nodes']):
                        # We use 'start_line' which we added to GraphService
                        if node.get('start_line') == metadata.lineno:
                            bug_node_idx = idx
                            break
                    
                    if bug_node_idx != -1:
                        # Target: All zeros, except 1.0 at bug index
                        target_loc = torch.zeros((t_user.x.shape[0], 1), device=device)
                        target_loc[bug_node_idx] = 1.0
                        loss_loc = criterion_loc(loc_out, target_loc)

                        target_token_str = metadata.original_token
                        target_token_id = get_type_id(str(target_token_str))

                        pred_logits = patch_out[bug_node_idx].unsqueeze(0) # [1, Vocab_Size]

                        loss_patch = criterion_patch(pred_logits, torch.tensor([target_token_id], device=device))

                
                # Combined Loss
                # We weight Localization lower because it's harder and sparse
                loss = loss_cls + (0.5 * loss_loc) + (0.5 * loss_patch)
                
                loss.backward()
                optimizer.step()
                
                num_processed += 1 
                total_loss += loss.item()
                
                if torch.argmax(cls_logits := cls_out).item() == target_cls:
                    correct_cls += 1

            except Exception as e:
                # log_print(f"[ERROR] {e}")
                continue

        if num_processed > 0:
            actual_acc = (correct_cls / num_processed) * 100
            avg_loss = total_loss / num_processed
            log_print(f"Epoch {epoch+1}: Loss={avg_loss:.4f} | Cls_Acc={actual_acc:.2f}%")
        else:
            log_print(f"Epoch {epoch+1}: Skipped all")
        
        if (epoch+1) % 10 == 0:
            torch.save(model.state_dict(), f"gnn_model_v3_ep{epoch+1}.pth")
            save_vocab() # <--- IMPORTANT
            log_print("Model and Vocab saved.")

if __name__ == "__main__":
    train()