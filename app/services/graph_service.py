"""
Service layer for building and serializing AST, CFG, and DFG
"""
from typing import Dict, List, Any, Tuple
from core_engine.models.ast_models import TreeSitterParser, ASTBuilder, AST, ASTNode
from core_engine.models.cfg_models import CFGBuilder, CFG, CFGNode, CFGEdge
from core_engine.models.dfg_models import DFGBuilder, DFG, DFGNode, DFGEdge


class GraphService:
    """Service for building and serializing all graph representations"""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
    
    def build_all_graphs(self) -> Dict[str, Any]:
        """
        Build AST, CFG, and DFG from source code
        
        Returns:
            Dictionary containing serialized AST, CFG, and DFG
        """
        # Step 1: Parse and build AST
        parser = TreeSitterParser()
        tree = parser.parse(self.source_code)
        ast_builder = ASTBuilder(self.source_code)
        ast_root = ast_builder.build(tree.root_node)
        ast = AST(ast_root)
        
        # Step 2: Build CFG from AST
        cfg_builder = CFGBuilder()
        cfg = cfg_builder.build(ast_root)
        
        # Step 3: Build DFG from AST and CFG
        dfg_builder = DFGBuilder(self.source_code)
        dfg = dfg_builder.build(ast_root, cfg)
        
        # Step 4: Serialize all graphs to JSON-friendly format
        return {
            "ast": self._serialize_ast(ast),
            "cfg": self._serialize_cfg(cfg),
            "dfg": self._serialize_dfg(dfg)
        }
    
    def _serialize_ast(self, ast: AST) -> Dict[str, Any]:
        """Convert AST to JSON-serializable format"""
        
        def serialize_node(node: ASTNode) -> Dict[str, Any]:
            return {
                "id": node.id,
                "type": node.type,
                "role": node.role,
                "symbol": node.symbol,
                "operator": node.operator,
                "text": node.get_text(self.source_code),
                "source_span": node.source_span,
                "children": [serialize_node(child) for child in node.children]
            }
        
        return {
            "root": serialize_node(ast.root),
            "node_count": len(list(ast.traverse()))
        }
    
    def _serialize_cfg(self, cfg: CFG) -> Dict[str, Any]:
        """Convert CFG to JSON-serializable format for D3.js"""
        
        nodes = []
        edges = []
        
        # Serialize nodes
        for node in cfg.nodes:
            nodes.append({
                "id": node.id,
                "label": node.label,
                "ast_node_id": node.ast_node.id if node.ast_node else None,
                "ast_node_type": node.ast_node.type if node.ast_node else None
            })
        
        # Serialize edges
        for node in cfg.nodes:
            for edge in node.outgoing:
                edges.append({
                    "source": edge.source.id,
                    "target": edge.target.id,
                    "condition": edge.condition
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "entry_id": cfg.entry.id,
            "exit_id": cfg.exit.id
        }
    
    def _serialize_dfg(self, dfg: DFG) -> Dict[str, Any]:
        """Convert DFG to JSON-serializable format for D3.js"""
        
        nodes = []
        edges = []
        
        # Serialize nodes
        for node in dfg.nodes:
            nodes.append({
                "id": node.id,
                "variable": node.variable,
                "is_definition": node.is_definition,
                "cfg_node_id": node.cfg_node.id,
                "ast_node_id": node.ast_node.id,
                "ast_node_type": node.ast_node.type
            })
        
        # Serialize edges
        for edge in dfg.edges:
            edges.append({
                "source": edge.source.id,
                "target": edge.target.id,
                "variable": edge.variable
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "definitions": {
                var: [n.id for n in nodes_list] 
                for var, nodes_list in dfg.definitions.items()
            },
            "uses": {
                var: [n.id for n in nodes_list] 
                for var, nodes_list in dfg.uses.items()
            }
        }