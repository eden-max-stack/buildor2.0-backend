"""
Service layer for building and serializing AST, CFG, and DFG
"""
from typing import Dict, List, Any, Tuple
from core_engine.models.ast_models import TreeSitterParser, ASTBuilder, AST, ASTNode
from core_engine.models.cfg_models import CFGBuilder, CFG, CFGNode, CFGEdge
from core_engine.models.dfg_models import DFGBuilder, DFG, DFGNode, DFGEdge

# In app/services/graph_service.py

def find_functions(ast_root: ASTNode) -> list[ASTNode]:
    """
    Find all functions, including methods inside classes.
    """
    functions = []
    
    # We use a stack for iterative traversal to find nested functions/methods
    stack = [ast_root]
    
    while stack:
        node = stack.pop()
        
        if node.type == "function_definition":
            functions.append(node)
            # We DON'T recurse into the function body to find nested functions
            # (unless you want to support closures/inner functions)
            continue
            
        # If it's a Class, we MUST look inside it
        if node.type == "class_definition":
            # Just add children to stack to keep searching
            stack.extend(node.children)
            continue
            
        # For modules/blocks, keep searching children
        stack.extend(node.children)
            
    return functions

class GraphService:
    """Service for building and serializing all graph representations"""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
    
    def build_all_graphs(self) -> Dict[str, Any]:
        """
        Build AST, CFG, and DFG from source code
        """
        try:
            # Step 1: Parse and build AST
            parser = TreeSitterParser()
            tree = parser.parse(self.source_code)
            ast_builder = ASTBuilder(self.source_code)
            ast_root = ast_builder.build(tree.root_node)
            ast = AST(ast_root)
            
            # Step 2: Find all functions
            functions = find_functions(ast_root)
            
            # Step 3: Build CFG and DFG for each function
            function_analyses = []
            
            for func_node in functions:
                try:
                    # Get function name
                    func_name = self._get_function_name(func_node)
                    
                    # Build CFG for this function
                    cfg_builder = CFGBuilder()
                    cfg = cfg_builder.build(func_node)
                    
                    # Build DFG for this function
                    dfg_builder = DFGBuilder(self.source_code)
                    dfg = dfg_builder.build(func_node, cfg)
                    
                    # Serialize CFG and DFG
                    cfg_serialized = self._serialize_cfg(cfg)
                    dfg_serialized = self._serialize_dfg(dfg)
                    
                    function_analyses.append({
                        "name": func_name,
                        "ast_node_id": func_node.id,
                        "cfg": cfg_serialized,
                        "dfg": dfg_serialized
                    })
                    
                except Exception as e:
                    print(f"Error building graphs for function: {e}")
                    # Create empty analysis for this failed function
                    func_name = self._get_function_name(func_node) if 'func_node' in locals() else "unknown"
                    function_analyses.append({
                        "name": func_name,
                        "ast_node_id": func_node.id if 'func_node' in locals() else 0,
                        "cfg": self._serialize_cfg(self._create_empty_cfg()),
                        "dfg": self._serialize_dfg(self._create_empty_dfg())
                    })
            
            # If no functions found, create analysis for the entire module
            if not functions:
                # Build CFG and DFG for entire module
                cfg_builder = CFGBuilder()
                cfg = cfg_builder.build(ast_root)
                
                dfg_builder = DFGBuilder(self.source_code)
                dfg = dfg_builder.build(ast_root, cfg)
                
                function_analyses.append({
                    "name": "module",
                    "ast_node_id": ast_root.id,
                    "cfg": self._serialize_cfg(cfg),
                    "dfg": self._serialize_dfg(dfg)
                })
            
            # Step 4: Serialize
            return {
                "ast": self._serialize_ast(ast),
                "functions": function_analyses,
                "source_code": self.source_code
            }
            
        except Exception as e:
            print(f"Error in GraphService: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "ast": self._create_empty_ast(),
                "functions": [],
                "source_code": self.source_code,
                "error": str(e)
            }

    def _create_empty_ast(self) -> Dict[str, Any]:
        """Create empty AST structure"""
        return {
            "root": {
                "id": 0,
                "type": "module",
                "role": None,
                "symbol": None,
                "operator": None,
                "text": self.source_code,
                "source_span": [0, len(self.source_code)],
                "children": []
            },
            "node_count": 1
        }
    
    def _create_empty_cfg(self) -> CFG:
        """Create empty CFG structure"""
        entry = CFGNode(id=0, ast_node=None, label="ENTRY")
        exit = CFGNode(id=1, ast_node=None, label="EXIT")
        cfg = CFG(entry, exit)
        entry.outgoing.append(CFGEdge(entry, exit))
        return cfg
    
    def _create_empty_dfg(self) -> DFG:
        """Create empty DFG structure"""
        return DFG()
    
    def _get_function_name(self, func_node: ASTNode) -> str:
        """Extract function name from AST node"""
        for child in func_node.children:
            if child.type == "identifier":
                return child.get_text(self.source_code)
        return "anonymous"
    
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
        
        print(f"\n=== DEBUG: CFG Serialization ===")
        print(f"Total nodes in cfg.nodes: {len(cfg.nodes)}")
        print("Nodes in cfg.nodes:", [f"{n.id}:{n.label}" for n in cfg.nodes])
        
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
        
        print(f"\nEdges found:")
        edge_count = 0
        # Serialize edges
        for node in cfg.nodes:
            for edge in node.outgoing:
                edge_count += 1
                print(f"  {edge.source.id}:{edge.source.label} -> {edge.target.id}:{edge.target.label} (cond: {edge.condition})")
                edges.append({
                    "source": edge.source.id,
                    "target": edge.target.id,
                    "condition": edge.condition
                })
        
        print(f"Total edges: {edge_count}")
        print("=== END DEBUG ===\n")
        
        return {
            "nodes": nodes,
            "edges": edges,
            "entry_id": cfg.entry.id,
            "exit_id": cfg.exit.id
        }

    def _serialize_dfg(self, dfg: DFG) -> Dict[str, Any]:
        """Convert DFG to JSON-serializable format for D3.js"""

        print(f"\n=== DEBUG: DFG Serialization ===")
        print(f"Total nodes in dfg.nodes: {len(dfg.nodes)}")

        node_debug_info = [
            f"{n.id}:{n.variable}({'DEF' if n.is_definition else 'USE'})" 
            for n in dfg.nodes
        ]
        print("Nodes in dfg.nodes:", node_debug_info)

        print(f"\nEdges found:")
        for edge in dfg.edges:
            print(f"  {edge.source.id} -> {edge.target.id} (var: {edge.variable})")
            
        print(f"Total edges: {len(dfg.edges)}")
        
        print(f"\nVariable Maps:")
        print(f"  Defined vars: {list(dfg.definitions.keys())}")
        print(f"  Used vars: {list(dfg.uses.keys())}")
        print("=== END DEBUG ===\n")
        
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

    def get_raw_graphs(self) -> Dict[str, Any]:
        """
        Returns raw object instances (AST, CFG, DFG) for internal processing (GNN).
        Does NOT perform JSON serialization.
        """
        # Step 1: Parse and build AST
        parser = TreeSitterParser()
        tree = parser.parse(self.source_code)
        ast_builder = ASTBuilder(self.source_code)
        ast_root = ast_builder.build(tree.root_node)
        ast = AST(ast_root)
        
        # Step 2: Find all functions
        functions = find_functions(ast_root)
        
        # Step 3: Build CFG and DFG for each function
        function_analyses = []
        
        for func_node in functions:
            try:
                func_name = self._get_function_name(func_node)
                
                cfg_builder = CFGBuilder()
                cfg = cfg_builder.build(func_node)
                
                dfg_builder = DFGBuilder(self.source_code)
                dfg = dfg_builder.build(func_node, cfg)
                
                # Store RAW OBJECTS, not serialized dicts
                function_analyses.append({
                    "name": func_name,
                    "ast_node": func_node, # Store the node object itself
                    "cfg": cfg,            # Store CFG object
                    "dfg": dfg             # Store DFG object
                })
            except Exception as e:
                print(f"Error building graphs for function: {e}")
                # Handle error...

        # Handle module level fallback... (same as before)

        return {
            "ast": ast,
            "functions": function_analyses,
            "source_code": self.source_code
        }

    def build_all_graphs(self) -> Dict[str, Any]:
        """
        Public API method: Builds graphs AND serializes them to JSON dicts.
        """
        raw_data = self.get_raw_graphs()
        
        # Convert raw objects to the JSON structure expected by the API
        serialized_functions = []
        for func in raw_data["functions"]:
            serialized_functions.append({
                "name": func["name"],
                "ast_node_id": func["ast_node"].id,
                "cfg": self._serialize_cfg(func["cfg"]),
                "dfg": self._serialize_dfg(func["dfg"])
            })
            
        return {
            "ast": self._serialize_ast(raw_data["ast"]),
            "functions": serialized_functions,
            "source_code": raw_data["source_code"]
        }