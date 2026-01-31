import torch
from torch_geometric.data import HeteroData
from collections import defaultdict
from core_engine.models.ast_models import AST
from core_engine.models.cfg_models import CFG
from core_engine.models.dfg_models import DFG

class GraphToPyGConverter:
    def __init__(self):
        # Simple encoders (In prod, reuse these across calls to maintain vocab)
        self.type_encoder = defaultdict(lambda: len(self.type_encoder))
        self.text_encoder = defaultdict(lambda: len(self.text_encoder))
    
    def convert(self, raw_graphs: dict) -> HeteroData:
        """
        Takes the output of GraphService.get_raw_graphs() and returns HeteroData
        """
        data = HeteroData()
        ast_obj = raw_graphs['ast']
        functions = raw_graphs['functions']
        
        # --- 1. AST Processing ---
        ast_nodes = []
        ast_edges = []
        ast_id_to_idx = {} # Map ASTNode.id -> Tensor Index (0..N)
        
        def traverse_ast(node):
            if node.id not in ast_id_to_idx:
                idx = len(ast_nodes)
                ast_id_to_idx[node.id] = idx
                
                # Feature: [NodeType] (Simple integer encoding)
                ast_nodes.append([self.type_encoder[node.type]])
                
                for child in node.children:
                    traverse_ast(child)
                    child_idx = ast_id_to_idx[child.id]
                    ast_edges.append([idx, child_idx])

        traverse_ast(ast_obj.root)
        
        data['ast_node'].x = torch.tensor(ast_nodes, dtype=torch.float)
        data['ast_node', 'child', 'ast_node'].edge_index = torch.tensor(ast_edges, dtype=torch.long).t().contiguous()

        # --- 2. CFG & DFG Processing ---
        # (We assume multiple functions are merged into one large graph)
        cfg_feats, cfg_edges, cfg_map = [], [], []
        dfg_feats, dfg_edges, dfg_map = [], [], []
        
        cfg_offset, dfg_offset = 0, 0
        
        for func in functions:
            cfg: CFG = func['cfg']
            dfg: DFG = func['dfg']
            
            # --- CFG ---
            local_cfg_map = {} # CFGNode.id -> Tensor Index
            for i, node in enumerate(cfg.nodes):
                local_cfg_map[node.id] = i + cfg_offset
                cfg_feats.append([self.text_encoder[node.label]])
                
                # Link to AST
                if node.ast_node and node.ast_node.id in ast_id_to_idx:
                    ast_idx = ast_id_to_idx[node.ast_node.id]
                    cfg_map.append([i + cfg_offset, ast_idx])

            for node in cfg.nodes:
                src = local_cfg_map[node.id]
                for edge in node.outgoing:
                    dst = local_cfg_map[edge.target.id]
                    cfg_edges.append([src, dst])

            # --- DFG ---
            local_dfg_map = {} # DFGNode.id -> Tensor Index
            for i, node in enumerate(dfg.nodes):
                local_dfg_map[node.id] = i + dfg_offset
                # Feature: [Variable Name ID, Is Definition?]
                dfg_feats.append([
                    self.text_encoder[node.variable],
                    1.0 if node.is_definition else 0.0
                ])
                
                # Link to AST
                if node.ast_node and node.ast_node.id in ast_id_to_idx:
                    ast_idx = ast_id_to_idx[node.ast_node.id]
                    dfg_map.append([i + dfg_offset, ast_idx])

            for edge in dfg.edges:
                src = local_dfg_map[edge.source.id]
                dst = local_dfg_map[edge.target.id]
                dfg_edges.append([src, dst])

            cfg_offset += len(cfg.nodes)
            dfg_offset += len(dfg.nodes)

        # Final Tensors
        if cfg_feats:
            data['cfg_node'].x = torch.tensor(cfg_feats, dtype=torch.float)
            data['cfg_node', 'flow', 'cfg_node'].edge_index = torch.tensor(cfg_edges, dtype=torch.long).t().contiguous()
            data['cfg_node', 'maps_to', 'ast_node'].edge_index = torch.tensor(cfg_map, dtype=torch.long).t().contiguous()
            
        if dfg_feats:
            data['dfg_node'].x = torch.tensor(dfg_feats, dtype=torch.float)
            data['dfg_node', 'data_flow', 'dfg_node'].edge_index = torch.tensor(dfg_edges, dtype=torch.long).t().contiguous()
            data['dfg_node', 'maps_to', 'ast_node'].edge_index = torch.tensor(dfg_map, dtype=torch.long).t().contiguous()

        return data