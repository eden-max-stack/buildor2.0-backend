import json
import pandas as pd
import sys
import os
import traceback

# --- Setup Paths ---
# Ensure we can import from 'app' and 'core_engine'
sys.path.append(os.getcwd())

try:
    from app.services.graph_service import GraphService
except ImportError:
    print("Error: Could not import GraphService. Make sure you are running this from the project root.")
    sys.exit(1)

# --- Configuration ---
DATASET_PATH = 'human-eval-v2-20210705.jsonl'
OUTPUT_FILE = 'humaneval_graph_analysis.csv'

def process_dataset():
    print(f"--- Starting Evaluation on {DATASET_PATH} ---")
    
    if not os.path.exists(DATASET_PATH):
        print(f"File not found: {DATASET_PATH}")
        return

    results = []
    success_count = 0
    error_count = 0

    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total = len(lines)
    print(f"Found {total} problems.")

    for i, line in enumerate(lines):
        data = json.loads(line)
        task_id = data['task_id']
        
        # 1. Construct Full Code
        # HumanEval splits the function signature (prompt) and body (canonical_solution)
        full_code = data['prompt'] + data['canonical_solution']
        
        entry = {
            'task_id': task_id,
            'status': 'Pending',
            'error_type': None,
            'error_msg': None,
            'ast_nodes': 0,
            'cfg_nodes': 0,
            'dfg_nodes': 0,
            'dfg_edges': 0,
            # We save the JSON strings to CSV for inspection
            'ast_json': '', 
            'cfg_json': '',
            'dfg_json': '',
            'code_snippet': full_code[:100] + "..." # Just for reference
        }

        try:
            # 2. Run Graph Service
            service = GraphService(full_code)
            graphs = service.build_all_graphs() 
            
            # 3. Extract Metrics
            ast_data = graphs.get('ast', {})
            functions = graphs.get('functions', [])
            
            entry['ast_nodes'] = ast_data.get('node_count', 0)
            entry['ast_json'] = json.dumps(ast_data)

            if functions:
                # HumanEval usually has 1 main function
                main_func = functions[0]
                
                cfg_data = main_func.get('cfg', {})
                dfg_data = main_func.get('dfg', {})
                
                # Metrics
                entry['cfg_nodes'] = len(cfg_data.get('nodes', []))
                entry['dfg_nodes'] = len(dfg_data.get('nodes', []))
                entry['dfg_edges'] = len(dfg_data.get('edges', []))
                
                # Serialized Data
                entry['cfg_json'] = json.dumps(cfg_data)
                entry['dfg_json'] = json.dumps(dfg_data)
                
                # Check for "Empty Graph" issues (Parser failure usually results in 0 nodes)
                if entry['cfg_nodes'] < 2:
                    entry['status'] = 'Warning: Empty CFG'
                elif entry['dfg_nodes'] == 0:
                    entry['status'] = 'Warning: Empty DFG'
                else:
                    entry['status'] = 'Success'
                    success_count += 1
            else:
                entry['status'] = 'Warning: No Function Found'
                
        except Exception as e:
            entry['status'] = 'Error'
            entry['error_msg'] = str(e)
            entry['error_type'] = type(e).__name__
            error_count += 1
            # Optional: Print first few errors to debug
            if error_count <= 3:
                print(f"\n[!] Failed on {task_id}: {e}")
                # traceback.print_exc()

        results.append(entry)
        
        # Progress Bar
        if (i + 1) % 20 == 0:
            print(f"Processed {i + 1}/{total}...")

    # --- Save & Report ---
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False)
    
    print("\n" + "="*40)
    print(" SUMMARY OF RESULTS")
    print("="*40)
    print(f"Total Tasks: {total}")
    print(f"Success:     {success_count}")
    print(f"Errors:      {error_count}")
    print(f"Empty Graphs:{len(df[df['status'].str.contains('Warning')])}")
    print("-" * 40)
    print("Error Breakdown:")
    print(df[df['status'] == 'Error']['error_type'].value_counts())
    print("-" * 40)
    print(f"Detailed results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_dataset()