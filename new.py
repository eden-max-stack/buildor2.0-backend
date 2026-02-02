import pandas as pd
import json

# Load the results
df = pd.read_csv('humaneval_graph_analysis.csv')

# Get HumanEval/0
row = df[df['task_id'] == 'HumanEval/0'].iloc[0]

print(f"Task: {row['task_id']}")
print("-" * 20)
print(f"Code Snippet:\n{row['code_snippet']}")
print("-" * 20)

# Parse JSON to inspect structure
cfg = json.loads(row['cfg_json'])
dfg = json.loads(row['dfg_json'])

print(f"CFG Nodes: {len(cfg['nodes'])}")
print(f"CFG Edges: {len(cfg['edges'])}")
print(f"DFG Definitions: {len([n for n in dfg['nodes'] if n['is_definition']])}")

# Check for "Nested Loop" signature in CFG
# We look for two nodes with label 'for_iter'
loop_headers = [n for n in cfg['nodes'] if n['label'] == 'for_iter']
print(f"Detected Loops: {len(loop_headers)}")

# Check loop edges
for edge in cfg['edges']:
    src = next(n for n in cfg['nodes'] if n['id'] == edge['source'])
    tgt = next(n for n in cfg['nodes'] if n['id'] == edge['target'])
    if src['label'] == 'for_iter':
        print(f"Loop Header Edge: {src['id']} -> {tgt['id']} ({tgt['label']})")