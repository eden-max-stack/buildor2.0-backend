from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict
from .ast_models import ASTNode
from .cfg_models import CFG, CFGNode


@dataclass
class DFGNode:
    """Represents a variable definition or use in the data flow graph"""
    id: int
    variable: str
    ast_node: ASTNode
    cfg_node: CFGNode
    is_definition: bool  # True for writes, False for reads
    incoming: List["DFGEdge"] = field(default_factory=list)
    outgoing: List["DFGEdge"] = field(default_factory=list)


@dataclass
class DFGEdge:
    """Represents data flow from definition to use"""
    source: DFGNode  # Definition
    target: DFGNode  # Use
    variable: str


class DFG:
    """Data Flow Graph"""
    def __init__(self):
        self.nodes: List[DFGNode] = []
        self.edges: List[DFGEdge] = []
        self.definitions: Dict[str, List[DFGNode]] = {}  # variable -> definition nodes
        self.uses: Dict[str, List[DFGNode]] = {}  # variable -> use nodes
    
    def add_node(self, node: DFGNode):
        self.nodes.append(node)
        if node.is_definition:
            if node.variable not in self.definitions:
                self.definitions[node.variable] = []
            self.definitions[node.variable].append(node)
        else:
            if node.variable not in self.uses:
                self.uses[node.variable] = []
            self.uses[node.variable].append(node)
    
    def add_edge(self, edge: DFGEdge):
        self.edges.append(edge)
        edge.source.outgoing.append(edge)
        edge.target.incoming.append(edge)
    
    def print_pretty(self):
        print("Data Flow Graph:\n")
        
        print("Definitions:")
        for var, defs in self.definitions.items():
            for def_node in defs:
                print(f"  [{def_node.id}] {var} := ... (CFG node {def_node.cfg_node.id})")
        
        print("\nUses:")
        for var, uses in self.uses.items():
            for use_node in uses:
                print(f"  [{use_node.id}] {var} (CFG node {use_node.cfg_node.id})")
        
        print("\nData Flow Edges:")
        for edge in self.edges:
            print(f"  [{edge.source.id}] {edge.variable} -> [{edge.target.id}]")
        print()


class DFGBuilder:
    """Builds Data Flow Graph from AST and CFG"""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.node_id = 0
        self.dfg = DFG()
        # Track reaching definitions at each CFG node
        self.reaching_defs: Dict[int, Dict[str, Set[int]]] = {}  # CFG node id -> variable -> definition node IDs
    
    def build(self, ast_root: ASTNode, cfg: CFG) -> DFG:
        """Build DFG from AST and CFG"""

        # Step 0: Inject Parameter Definitions
        self._inject_parameters(ast_root, cfg)

        # Step 1: Extract all variable definitions and uses from AST
        self._extract_variables(cfg)
        
        # Step 2: Compute reaching definitions using CFG
        self._compute_reaching_definitions(cfg)
        
        # Step 3: Connect uses to their reaching definitions
        self._connect_def_use()
        
        return self.dfg
    
    def _extract_variables(self, cfg: CFG):
        """Extract variable definitions and uses from each CFG node"""
        for cfg_node in cfg.nodes:
            if cfg_node.ast_node is None:
                continue
            
            # Skip ENTRY/EXIT and structural nodes
            if cfg_node.label in ["ENTRY", "EXIT", "merge", "loop_exit"]:
                continue
            
            # For control flow condition nodes, only analyze the condition itself
            if cfg_node.label in ["if_cond", "while_cond"]:
                # Only look at the condition expression, not the whole if/while statement
                self._extract_from_condition(cfg_node)
                continue
            
            # For regular statements, analyze the statement node
            # Find definitions (assignments)
            defs = self._find_definitions(cfg_node.ast_node)
            for var_name in defs:
                dfg_node = DFGNode(
                    id=self.node_id,
                    variable=var_name,
                    ast_node=cfg_node.ast_node,
                    cfg_node=cfg_node,
                    is_definition=True
                )
                self.node_id += 1
                self.dfg.add_node(dfg_node)
            
            # Find uses (reads)
            uses = self._find_uses(cfg_node.ast_node)
            for var_name, is_sink in uses:
                dfg_node = DFGNode(
                    id=self.node_id,
                    variable=var_name,
                    ast_node=cfg_node.ast_node,
                    cfg_node=cfg_node,
                    is_definition=False
                )
                self.node_id += 1
                self.dfg.add_node(dfg_node)
    
    def _inject_parameters(self, ast_root: ASTNode, cfg: CFG):
        """Create definition nodes for function parameters at Entry"""
        if ast_root.type == "function_definition":
            params_node = ast_root.get_child_by_type("parameters")
            if params_node:
                for child in params_node.traverse_node():
                    if child.type == "identifier":
                        var_name = child.get_text(self.source_code)
                        
                        # Create a DFG definition node at CFG Entry
                        dfg_node = DFGNode(
                            id=self.node_id,
                            variable=var_name,
                            ast_node=child,
                            cfg_node=cfg.entry, # Attached to ENTRY
                            is_definition=True
                        )
                        self.node_id += 1
                        self.dfg.add_node(dfg_node)

    def _extract_from_condition(self, cfg_node: CFGNode):
        """Extract variables from a condition node (if_cond, while_cond)"""
        ast_node = cfg_node.ast_node
        
        # For if_statement, find the condition part
        if ast_node.type == "if_statement":
            # Look for comparison_operator or parenthesized_expression
            for child in ast_node.children:
                if child.type in ["comparison_operator", "parenthesized_expression", "binary_operator"]:
                    uses = self._find_uses_in_expression(child)
                    for var_name in uses:
                        dfg_node = DFGNode(
                            id=self.node_id,
                            variable=var_name,
                            ast_node=child,
                            cfg_node=cfg_node,
                            is_definition=False
                        )
                        self.node_id += 1
                        self.dfg.add_node(dfg_node)
                    break
        
        # For while_statement, similar logic
        elif ast_node.type == "while_statement":
            for child in ast_node.children:
                if child.type in ["comparison_operator", "parenthesized_expression", "binary_operator"]:
                    uses = self._find_uses_in_expression(child)
                    for var_name in uses:
                        dfg_node = DFGNode(
                            id=self.node_id,
                            variable=var_name,
                            ast_node=child,
                            cfg_node=cfg_node,
                            is_definition=False
                        )
                        self.node_id += 1
                        self.dfg.add_node(dfg_node)
                    break
    
    def _find_uses_in_expression(self, expr_node: ASTNode) -> Set[str]:
        """Find variable uses in an expression (no function names)"""
        uses = set()
        
        for node in expr_node.traverse_node():
            if node.type == "identifier":
                var_name = node.get_text(self.source_code)
                
                # Skip function calls
                parent = node.parent
                if parent and parent.type == "call":
                    call_func = parent.children[0] if parent.children else None
                    if call_func and call_func.id == node.id:
                        continue
                
                uses.add(var_name)
        
        return uses
    
    def _find_definitions(self, ast_node: ASTNode) -> Set[str]:
        """Find all variable definitions in an AST node"""
        definitions = set()
        
        # Look for assignment patterns
        if ast_node.type == "assignment":
            # Left side of assignment
            left = ast_node.get_child_by_type("identifier")
            if left:
                var_name = left.get_text(self.source_code)
                definitions.add(var_name)
        
        # Recursively check children
        for child in ast_node.children:
            # Don't recurse into nested blocks (they're separate CFG nodes)
            if child.type not in ["block", "function_definition"]:
                definitions.update(self._find_definitions(child))
        
        return definitions
    
    def _find_uses(self, ast_node: ASTNode) -> Set[str]:
        """Find all variable uses (reads) in an AST node (statement level)"""
        uses = set()
        
        # Find all identifiers in this statement
        for node in ast_node.traverse_node():
            if node.type == "identifier":
                var_name = node.get_text(self.source_code)
                
                parent = node.parent

                is_sink = False
                if parent:
                    # Skip if this is the left side of an assignment
                    if parent.type == "assignment":
                        left = parent.get_child_by_type("identifier")
                        if left and left.id == node.id:
                            continue  # This is a definition, not a use
                    
                    # Skip function calls - we don't track function names as variables
                    if parent.type == "call":
                        call_func = parent.children[0] if parent.children else None
                        if call_func and call_func.id == node.id:
                            continue  # This is a function name, not a variable use

                    if parent.type == "argument_list":
                        # Check the call function name
                        call_node = parent.parent
                        if call_node and call_node.type == "call":
                            func_name_node = call_node.get_child_by_type("identifier")
                            if func_name_node and func_name_node.get_text(self.source_code) == "print":
                                is_sink = True
                    
                uses.add((var_name, is_sink))
        
        return uses
    
    def _compute_reaching_definitions(self, cfg: CFG):
        """Compute reaching definitions using dataflow analysis"""
        # Initialize reaching definitions - use node.id as key instead of node object
        for node in cfg.nodes:
            self.reaching_defs[node.id] = {}
        
        # Worklist algorithm - use a proper fixed-point iteration
        changed = True
        iterations = 0
        max_iterations = 100  # Safety limit
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for cfg_node in cfg.nodes:
                # Get reaching definitions at entry to this node
                if cfg_node == cfg.entry:
                    in_defs = {}
                else:
                    # Union of reaching defs from all predecessors
                    in_defs = {}
                    for pred in self._get_predecessors(cfg_node, cfg):
                        for var, defs in self.reaching_defs[pred.id].items():
                            if var not in in_defs:
                                in_defs[var] = set()
                            in_defs[var].update(defs)
                
                # Compute OUT = (IN - KILL) ∪ GEN
                out_defs = {}
                
                # Start with IN
                for var, defs in in_defs.items():
                    out_defs[var] = set(defs)
                
                # GEN: Add definitions from this node
                defs_in_node = [d for d in self.dfg.nodes 
                              if d.cfg_node.id == cfg_node.id and d.is_definition]
                for def_node in defs_in_node:
                    # KILL: Replace previous definitions of this variable
                    out_defs[def_node.variable] = {def_node.id}  # Store node ID, not node object
                
                # Check if anything changed
                if out_defs != self.reaching_defs[cfg_node.id]:
                    self.reaching_defs[cfg_node.id] = out_defs
                    changed = True
    
    def _get_predecessors(self, node: CFGNode, cfg: CFG) -> List[CFGNode]:
        """Get all predecessor nodes in CFG"""
        predecessors = []
        for cfg_node in cfg.nodes:
            for edge in cfg_node.outgoing:
                if edge.target == node:
                    predecessors.append(cfg_node)
        return predecessors
    
    def _connect_def_use(self):
        """Connect each use to its reaching definitions"""
        # Create a map from DFG node ID to DFG node for quick lookup
        dfg_nodes_by_id = {node.id: node for node in self.dfg.nodes}
        
        for use_node in self.dfg.nodes:
            if not use_node.is_definition:
                # Get reaching definitions at this CFG node
                reaching = self.reaching_defs.get(use_node.cfg_node.id, {})
                var_def_ids = reaching.get(use_node.variable, set())
                
                # Create edges from each reaching definition to this use
                for def_id in var_def_ids:
                    def_node = dfg_nodes_by_id.get(def_id)
                    if def_node:
                        edge = DFGEdge(
                            source=def_node,
                            target=use_node,
                            variable=use_node.variable
                        )
                        self.dfg.add_edge(edge)