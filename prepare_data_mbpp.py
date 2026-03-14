"""
Pre-generate training data from MBPP: multiple mutations per problem, cached CPG tensors.
Run once, then train_mbpp.py loads from cache for fast, consistent training.
"""
import torch
from torch_geometric.data import Data
import json, random, pickle, os

from app.services.graph_service import GraphService
from core_engine.mutator import generate_buggy_code

DATASET_PATH = 'mbpp.jsonl'
CACHE_FILE = 'training_cache_mbpp.pkl'
VOCAB_FILE = 'vocab_mbpp.json'
MUTATIONS_PER_PROBLEM = 15
VAL_RATIO = 0.15
MAX_VOCAB_SIZE = 500
BUG_TYPES = ["None", "Operator Error", "Logic Error"]
TYPE_TO_IDX = {t: i for i, t in enumerate(BUG_TYPES)}

NODE_TYPE_MAP = {"UNK": 0}
NEXT_ID = 1


def get_type_id(node_type):
    global NEXT_ID
    if node_type not in NODE_TYPE_MAP:
        if NEXT_ID >= MAX_VOCAB_SIZE:
            return 0
        NODE_TYPE_MAP[node_type] = NEXT_ID
        NEXT_ID += 1
    return NODE_TYPE_MAP[node_type]


def _seed_mutation_tokens():
    """Pre-register all tokens that the mutator can produce as original_token.
    Without this, tokens like 'True', 'False', integers are missing from the
    vocabulary and the patch head can never learn them (maps to UNK=0)."""
    mutation_tokens = [
        "+", "-", "*", "/", "%", "**",
        "==", "!=", "<", ">", "<=", ">=",
        "and", "or",
        "True", "False",
    ]
    for i in range(-2, 20):
        mutation_tokens.append(str(i))
    for tok in mutation_tokens:
        get_type_id(tok)


def build_cpg_tensor(graphs_dict):
    ast_data = graphs_dict['ast']
    nodes = ast_data.get('nodes', [])
    if not nodes:
        x = torch.tensor([0], dtype=torch.long)
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long)), []

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
            all_src.append(s)
            all_dst.append(d)

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
        return Data(x=x, edge_index=torch.empty((2, 0), dtype=torch.long)), nodes

    edge_index = torch.tensor([all_src, all_dst], dtype=torch.long)
    return Data(x=x, edge_index=edge_index), nodes


def main():
    _seed_mutation_tokens()
    print("Loading MBPP problems...")

    problems = []
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            problems.append(json.loads(line))

    print(f"  {len(problems)} problems loaded.")

    samples = []
    skipped = 0

    for pi, prob in enumerate(problems):
        correct_code = prob.get('code')
        if not correct_code or not isinstance(correct_code, str):
            skipped += 1
            continue

        problem_idx = prob.get('task_id', pi)

        # Build optimal graph once
        try:
            o_graphs = GraphService(correct_code).build_all_graphs()
            t_opt, _ = build_cpg_tensor(o_graphs)
        except Exception as e:
            print(f"  Skip problem {problem_idx}: can't build optimal graph: {e}")
            skipped += 1
            continue

        # Clean sample (no bug)
        try:
            t_user, u_nodes = build_cpg_tensor(o_graphs)
            samples.append({
                't_user': t_user,
                't_opt': t_opt,
                'u_nodes': u_nodes,
                'target_cls': 0,
                'is_buggy': False,
                'metadata': None,
                'problem_idx': problem_idx,
            })
        except Exception:
            pass

        # Generate multiple mutations
        mutations_done = 0
        attempts = 0
        while mutations_done < MUTATIONS_PER_PROBLEM and attempts < MUTATIONS_PER_PROBLEM * 5:
            attempts += 1
            buggy_code, metadata = generate_buggy_code(correct_code)
            if not buggy_code:
                continue

            target_cls = TYPE_TO_IDX.get(metadata.bug_type, 0)

            try:
                u_graphs = GraphService(buggy_code).build_all_graphs()
                t_user, u_nodes = build_cpg_tensor(u_graphs)

                bug_line_indices = [
                    idx for idx, node in enumerate(u_nodes)
                    if node.get('start_line') == metadata.lineno
                ]
                if not bug_line_indices:
                    continue

                samples.append({
                    't_user': t_user,
                    't_opt': t_opt,
                    'u_nodes': u_nodes,
                    'target_cls': target_cls,
                    'is_buggy': True,
                    'metadata': {
                        'lineno': metadata.lineno,
                        'original_token': metadata.original_token,
                        'buggy_token': metadata.buggy_token,
                        'bug_type': metadata.bug_type,
                    },
                    'bug_line_indices': bug_line_indices,
                    'problem_idx': problem_idx,
                })
                mutations_done += 1
            except Exception:
                continue

        if (pi + 1) % 200 == 0:
            print(f"  Processed {pi+1}/{len(problems)}, samples so far: {len(samples)}")

    print(f"\nTotal samples: {len(samples)} (skipped {skipped} problems)")

    # Split by problem_idx to avoid leakage
    all_pids = list(set(s['problem_idx'] for s in samples))
    random.shuffle(all_pids)
    split = int(len(all_pids) * (1 - VAL_RATIO))
    train_pids = set(all_pids[:split])
    val_pids = set(all_pids[split:])

    train_samples = [s for s in samples if s['problem_idx'] in train_pids]
    val_samples = [s for s in samples if s['problem_idx'] in val_pids]
    print(f"Train: {len(train_samples)}, Val: {len(val_samples)}")

    cache = {
        'train': train_samples,
        'val': val_samples,
        'vocab': NODE_TYPE_MAP,
        'next_id': NEXT_ID,
        'bug_types': BUG_TYPES,
        'dataset': 'mbpp',
        'dataset_path': DATASET_PATH,
    }

    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache, f)

    print(f"Saved to {CACHE_FILE} ({os.path.getsize(CACHE_FILE) / 1024 / 1024:.1f} MB)")

    with open(VOCAB_FILE, 'w', encoding='utf-8') as f:
        json.dump(NODE_TYPE_MAP, f)

    print("Vocab saved.")


if __name__ == '__main__':
    main()
