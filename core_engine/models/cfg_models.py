from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from .ast_models import ASTNode


@dataclass
class CFGNode:
    id: int
    ast_node: Optional[ASTNode]
    label: str
    outgoing: List["CFGEdge"] = field(default_factory=list)


@dataclass
class CFGEdge:
    source: CFGNode
    target: CFGNode
    condition: Optional[str] = None 


class CFG:
    def __init__(self, entry: CFGNode, exit: CFGNode):
        self.entry = entry
        self.exit = exit
        self.nodes: List[CFGNode] = [entry, exit]
    
    def add_node(self, node: CFGNode):
        """Centralized method for adding nodes"""
        self.nodes.append(node)

    def print_pretty(self):
        print("Control Flow Graph:\n")

        for node in self.nodes:
            print(f"[{node.id}] {node.label}")

            for edge in node.outgoing:
                cond = f" [{edge.condition}]" if edge.condition else ""
                print(f"   └──> [{edge.target.id}] {edge.target.label}{cond}")

            print()


class CFGBuilder:
    def __init__(self):
        self.node_id = 0
        self.current_cfg: Optional[CFG] = None  # Track which CFG we're building

    def new_node(self, ast_node: Optional[ASTNode], label: str) -> CFGNode:
        """Create a new CFG node and add it to current CFG"""
        node = CFGNode(
            id=self.node_id,
            ast_node=ast_node,
            label=label
        )
        self.node_id += 1
        
        # Add to current CFG if one is being built
        if self.current_cfg:
            self.current_cfg.add_node(node)
        
        return node

    def build_block(self, statements: List[ASTNode], exit_node: CFGNode = None) -> Tuple[Optional[CFGNode], Optional[CFGNode]]:
        """Build CFG for a sequence of statements
        
        Returns:
            (entry_node, exit_node) - both can be None if block is empty
        """
        if not statements:
            return None, None
        
        first = None
        prev = None

        for stmt in statements:
            # Handle different statement types
            if stmt.type == "if_statement":
                entry, exit = self.build_if(stmt)
            elif stmt.type == "while_statement":
                entry, exit = self.build_while(stmt)
            elif stmt.type == "for_statement":        # <--- ADD THIS BLOCK
                entry, exit = self.build_for(stmt)
            elif stmt.type == "with_statement":     # <--- ADD THIS
                entry, exit = self.build_with(stmt)
            elif stmt.type == "return_statement":
                entry = exit = self.new_node(stmt, "return")

                if exit_node:
                    entry.outgoing.append(CFGEdge(entry, exit_node))
                # Return short-circuits - don't connect to next statement
                if first is None:
                    first = entry
                else:
                    prev.outgoing.append(CFGEdge(prev, entry))
                # Don't update prev - this breaks the chain
                return first, exit
            else:
                # Regular statement
                entry = exit = self.new_node(stmt, stmt.type)

            if first is None:
                first = entry
            elif prev is not None:
                prev.outgoing.append(CFGEdge(prev, entry))

            prev = exit

        return first, prev
    
    def build(self, ast_root: ASTNode) -> CFG:
        """Build CFG for entire function/module
        
        This is the main entry point - it sets up the CFG context
        and then builds the body within that context.
        """
        # Create entry and exit nodes first (before CFG exists)
        entry = CFGNode(
            id=self.node_id,
            ast_node=ast_root,
            label="ENTRY"
        )
        self.node_id += 1
        
        exit = CFGNode(
            id=self.node_id,
            ast_node=ast_root,
            label="EXIT"
        )
        self.node_id += 1
        
        # Now create CFG with proper entry/exit
        cfg = CFG(entry, exit)
        
        # Set current CFG context for all subsequent node creation
        self.current_cfg = cfg
        
        try:
            # Extract and build function body statements
            statements = self.extract_statements(ast_root)
            
            if statements:
                body_entry, body_exit = self.build_block(statements, exit)
                if body_entry:
                    entry.outgoing.append(CFGEdge(entry, body_entry))
                
                # Only connect to exit if body_exit exists and isn't a return
                if body_exit and body_exit.label != "return":
                    body_exit.outgoing.append(CFGEdge(body_exit, exit))
            else:
                # Empty body - connect entry directly to exit
                entry.outgoing.append(CFGEdge(entry, exit))
        
        finally:
            # Clear CFG context when done
            self.current_cfg = None
        
        return cfg

    def extract_statements(self, ast_node: ASTNode) -> List[ASTNode]:
        """Extract statement nodes from AST node"""
        # For function definitions, get children of function_body
        if ast_node.type == "function_definition":
            body = ast_node.get_child_by_role("function_body")
            if body:
                return [child for child in body.children 
                       if child.role in ["statement", "return"] or 
                       child.type in ["if_statement", "while_statement", "return_statement", "for_statement", "return_statement"]]
        
        # For blocks, get all statement children
        return [child for child in ast_node.children
                if child.role in ["statement", "return"] or 
                child.type in ["if_statement", "while_statement", "return_statement", "for_statement", "return_statement"]]

    def build_if(self, if_node: ASTNode) -> Tuple[CFGNode, CFGNode]:
        """Build CFG for if statement
        
        Returns:
            (condition_node, merge_node)
        """

        condition_ast = if_node.get_child_by_role("condition")
        if not condition_ast:
            # Fallback if tree-sitter didn't tag it, usually first child is 'if', second is condition
            condition_ast = if_node.children[1] if len(if_node.children) > 1 else if_node
            
        cond = self.new_node(if_node, "if_cond")

        # Get then and else branches
        then_branch = if_node.get_child_by_role("then_branch")
        else_clause = if_node.get_child_by_type("else_clause")

        if else_clause:
            else_branch = else_clause.get_child_by_role("else_branch")
        else:
            else_branch = None

        # Build then branch
        if then_branch:
            then_stmts = self.extract_statements(then_branch)
            then_entry, then_exit = self.build_block(then_stmts)
        else:
            then_entry = then_exit = None

        # Build else branch
        if else_branch:
            else_stmts = self.extract_statements(else_branch)
            else_entry, else_exit = self.build_block(else_stmts)
        else:
            else_entry = else_exit = None

        if not else_branch:

            if then_entry:
                cond.outgoing.append(CFGEdge(cond, then_entry, "true"))

            return cond, cond

        # Merge point
        merge = self.new_node(if_node, "merge")

        # Connect condition to branches (or directly to merge if branch is empty)
        if then_entry:
            cond.outgoing.append(CFGEdge(cond, then_entry, "true"))
        else:
            cond.outgoing.append(CFGEdge(cond, merge, "true"))
            
        if else_entry:
            cond.outgoing.append(CFGEdge(cond, else_entry, "false"))
        else:
            cond.outgoing.append(CFGEdge(cond, merge, "false"))

        # Connect branches to merge (unless they're returns)
        if then_exit and then_exit.label != "return":
            then_exit.outgoing.append(CFGEdge(then_exit, merge))
        if else_exit and else_exit.label != "return":
            else_exit.outgoing.append(CFGEdge(else_exit, merge))

        return cond, merge

    def build_while(self, while_node: ASTNode) -> Tuple[CFGNode, CFGNode]:
        """Build CFG for while loop
        
        Returns:
            (condition_node, loop_exit_node)
        """
        # Condition node
        cond = self.new_node(while_node, "while_cond")

        # Get loop body
        loop_body = while_node.get_child_by_role("loop_body")
        
        if loop_body:
            body_stmts = self.extract_statements(loop_body)
            body_entry, body_exit = self.build_block(body_stmts)
        else:
            body_entry = body_exit = None

        # Exit node (for after loop)
        loop_exit = self.new_node(while_node, "loop_exit")

        # Connect: cond -> body (true), cond -> exit (false)
        if body_entry:
            cond.outgoing.append(CFGEdge(cond, body_entry, "true"))
        else:
            # Empty body - loop back to condition immediately
            cond.outgoing.append(CFGEdge(cond, cond, "true"))
            
        cond.outgoing.append(CFGEdge(cond, loop_exit, "false"))

        # Back edge: body -> cond (unless body ends with return)
        if body_exit and body_exit.label != "return":
            body_exit.outgoing.append(CFGEdge(body_exit, cond))

        return cond, loop_exit
    
    def build_for(self, for_node: ASTNode) -> Tuple[CFGNode, CFGNode]:
        """Build CFG for for-loop"""
        
        # 1. The Iterator Node 
        # In "for x in nums", this acts as the assignment/condition check
        iterator_ast = for_node.get_child_by_role("loop_iterator")
        # Fallback if roles aren't perfectly set yet
        if not iterator_ast:
             # Usually the 1st or 2nd child in tree-sitter structure
             iterator_ast = for_node
             
        loop_header = self.new_node(iterator_ast, "for_iter")
        
        # 2. The Body
        loop_body = for_node.get_child_by_role("loop_body")
        if loop_body:
            body_stmts = self.extract_statements(loop_body)
            body_entry, body_exit = self.build_block(body_stmts)
        else:
            body_entry = body_exit = None

        # 3. The Exit Node
        loop_exit = self.new_node(for_node, "for_exit")

        # 4. Connect Edges
        if body_entry:
            # Header -> Body (Next item exists)
            loop_header.outgoing.append(CFGEdge(loop_header, body_entry, "next"))
            
            # Body -> Header (Loop back)
            if body_exit.label != "return":
                body_exit.outgoing.append(CFGEdge(body_exit, loop_header))
        else:
            # Empty body loops back to self until done
            loop_header.outgoing.append(CFGEdge(loop_header, loop_header, "next"))

        # Header -> Exit (StopIteration / Done)
        loop_header.outgoing.append(CFGEdge(loop_header, loop_exit, "done"))

        return loop_header, loop_exit
    
    def build_with(self, with_node: ASTNode) -> Tuple[CFGNode, CFGNode]:
        """Build CFG for 'with' statement (Context Manager)"""
        
        # 1. The Context Entry (e.g., "with open(...) as f")
        # We treat the context expression as the entry point
        # Note: Tree-sitter structure varies, but usually first child is 'with', then 'with_clause' or expressions
        context_expr = with_node.children[1] if len(with_node.children) > 1 else with_node
        
        with_entry = self.new_node(context_expr, "with_enter")
        
        # 2. The Body
        body_node = with_node.get_child_by_role("body") # or check for block child
        if not body_node:
            # Fallback search for block
            for child in with_node.children:
                if child.type == "block":
                    body_node = child
                    break
        
        if body_node:
            body_stmts = self.extract_statements(body_node)
            body_entry, body_exit = self.build_block(body_stmts)
        else:
            body_entry = body_exit = None

        # 3. The Context Exit (Synthetic node representing __exit__)
        with_exit = self.new_node(with_node, "with_exit")

        # 4. Connect
        if body_entry:
            with_entry.outgoing.append(CFGEdge(with_entry, body_entry))
            
            if body_exit and body_exit.label != "return":
                body_exit.outgoing.append(CFGEdge(body_exit, with_exit))
        else:
            with_entry.outgoing.append(CFGEdge(with_entry, with_exit))

        return with_entry, with_exit