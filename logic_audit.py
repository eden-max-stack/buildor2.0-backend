import json
import sys
import os
import re

# Ensure imports work
sys.path.append(os.getcwd())
try:
    from app.services.graph_service import GraphService
except ImportError:
    print("Error: Run from project root.")
    sys.exit(1)

DATASET_PATH = 'human-eval-v2-20210705.jsonl'

# Features we suspect might be missing
FEATURES_TO_CHECK = {
    "List Comp": (r"\[.*for .* in .*\]", "list_comprehension"), # Source Regex -> Target CFG/AST Label
    "Try/Except": (r"\btry:", "try_statement"),
    "Yield": (r"\byield\b", "yield"),
    "Lambda": (r"\blambda\b", "lambda"),
    "Class": (r"\bclass\b", "class_definition"),
    "With": (r"\bwith\b", "with_statement"),
    "Raise": (r"\braise\b", "raise_statement")
}

def audit_dataset():
    print(f"--- Auditing Logic Coverage for {DATASET_PATH} ---")
    
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    failures = {k: [] for k in FEATURES_TO_CHECK.keys()}
    
    for i, line in enumerate(lines):
        data = json.loads(line)
        task_id = data['task_id']
        code = data['prompt'] + data['canonical_solution']
        
        # 1. Build Graph
        try:
            service = GraphService(code)
            graphs = service.get_raw_graphs() # Use raw method to check objects directly
            
            # Helper to get all node types found in AST/CFG
            found_node_types = set()
            
            # Check AST Nodes
            if 'ast' in graphs:
                for node in graphs['ast'].root.traverse_node():
                    found_node_types.add(node.type)
                    if node.role: found_node_types.add(node.role)
            
            # Check CFG Labels
            if 'functions' in graphs:
                for func in graphs['functions']:
                    for node in func['cfg'].nodes:
                        found_node_types.add(node.label)

            # 2. Logic Check
            for feature_name, (regex, target_label) in FEATURES_TO_CHECK.items():
                # If feature exists in TEXT but not in GRAPH
                if re.search(regex, code):
                    # We check if the parser recognized it (by label or type)
                    match_found = False
                    for found in found_node_types:
                        if target_label in found: 
                            match_found = True
                            break
                    
                    if not match_found:
                        failures[feature_name].append(task_id)

        except Exception as e:
            print(f"Skipping {task_id} due to crash: {e}")

    # --- Report ---
    print("\n" + "="*40)
    print(" LOGIC GAP REPORT")
    print(" (Features found in code but MISSING in CPG)")
    print("="*40)
    
    total_issues = 0
    for feature, task_ids in failures.items():
        if task_ids:
            print(f"\n[!] MISSING: {feature}")
            print(f"    Count: {len(task_ids)} problems")
            print(f"    Examples: {task_ids[:3]}...")
            total_issues += len(task_ids)
        else:
            print(f"[OK] {feature} - Covered correctly.")

    print("-"*40)
    if total_issues == 0:
        print("SUCCESS: Your CPG handles all checked Python features!")
    else:
        print(f"FAIL: Found {total_issues} logic gaps. Your CPG needs upgrades.")

if __name__ == "__main__":
    audit_dataset()