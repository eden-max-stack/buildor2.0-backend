import ast
import random
import os
import sys

# --- DEBUG PRINT: Shows exactly which file is being loaded ---
# print(f"\n[DEBUG] Mutator loaded from: {os.path.abspath(__file__)}")

# Try importing astor for code generation (Python < 3.9 compatibility)
try:
    import astor
except ImportError:
    astor = None 
    
class MutationMetadata:
    """
    Holds the 'Forensic Evidence' of a bug injection.
    This is the Ground Truth used to train the Localizer and Patcher heads.
    """
    def __init__(self, bug_type, lineno, col_offset, original_token, buggy_token):
        self.bug_type = bug_type          # e.g., "Operator Error"
        self.lineno = lineno              # Line number (1-based)
        self.col_offset = col_offset      # Column offset (0-based)
        self.original_token = original_token  # e.g., "+"
        self.buggy_token = buggy_token    # e.g., "-"

    def __repr__(self):
        return f"<Metadata: {self.bug_type} @ L{self.lineno}:{self.col_offset} ('{self.original_token}' -> '{self.buggy_token}')>"
    
class AdvancedBugInjector(ast.NodeTransformer):
    def __init__(self):
        self.metadata = None
        self.mutated = False

    def _inject(self, node, bug_type, original_token, buggy_token):
        """Helper to record the mutation details"""
        self.mutated = True
        self.metadata = MutationMetadata(
            bug_type=bug_type,
            lineno=getattr(node, 'lineno', -1),
            col_offset=getattr(node, 'col_offset', -1),
            original_token=original_token,
            buggy_token=buggy_token
        )

    def visit_BinOp(self, node):
        """Mutation: Swap math operators (+, -, *, /, %, **)"""
        if self.mutated: return node
        
        if random.random() < 0.4:
            op_map = {
                ast.Add: (ast.Sub, "+", "-"),
                ast.Sub: (ast.Add, "-", "+"),
                ast.Mult: (ast.Div, "*", "/"),
                ast.Div: (ast.Mult, "/", "*"),
                ast.Mod: (ast.Add, "%", "+"),
                ast.Pow: (ast.Mult, "**", "*")
            }
            
            curr_type = type(node.op)
            if curr_type in op_map:
                new_op_class, orig_str, new_str = op_map[curr_type]
                node.op = new_op_class()
                self._inject(node, "Operator Error", orig_str, new_str)
                
        return self.generic_visit(node)

    def visit_Compare(self, node):
        """Mutation: Swap comparisons (==, !=, <, >, <=, >=)"""
        if self.mutated: return node
        
        if random.random() < 0.4:
            # We only mutate the first operator for simplicity
            op = node.ops[0]
            op_type = type(op)
            
            op_map = {
                ast.Eq: (ast.NotEq, "==", "!="),
                ast.NotEq: (ast.Eq, "!=", "=="),
                ast.Lt: (ast.Gt, "<", ">"),
                ast.Gt: (ast.Lt, ">", "<"),
                ast.LtE: (ast.GtE, "<=", ">="),
                ast.GtE: (ast.LtE, ">=", "<=")
            }
            
            if op_type in op_map:
                new_op_class, orig_str, new_str = op_map[op_type]
                node.ops[0] = new_op_class()
                self._inject(node, "Logic Error", orig_str, new_str)
                
        return self.generic_visit(node)

    def visit_BoolOp(self, node):
        """Mutation: Swap boolean logic (and, or)"""
        if self.mutated: return node
        
        if random.random() < 0.4:
            op_type = type(node.op)
            op_map = {
                ast.And: (ast.Or, "and", "or"),
                ast.Or: (ast.And, "or", "and")
            }
            
            if op_type in op_map:
                new_op_class, orig_str, new_str = op_map[op_type]
                node.op = new_op_class()
                self._inject(node, "Logic Error", orig_str, new_str)
                
        return self.generic_visit(node)
    
    def visit_Constant(self, node):
        """Mutation: Flip Booleans and Off-By-One Integers"""
        if self.mutated: return node
        
        if random.random() < 0.25:
            val = node.value
            if isinstance(val, bool):
                # Flip Boolean
                node.value = not val
                self._inject(node, "Logic Error", str(val), str(not val))
            elif isinstance(val, int) and not isinstance(val, bool):
                # Integer Off-By-One
                new_val = val + 1
                node.value = new_val
                self._inject(node, "Logic Error", str(val), str(new_val))
                
        return node
    
    # Backwards compatibility for Python < 3.8 (Num/NameConstant/Str)
    def visit_Num(self, node):
        return self.visit_Constant(node)
    def visit_NameConstant(self, node):
        return self.visit_Constant(node)
    

class BugInjector(ast.NodeTransformer):
    def __init__(self):
        self.bug_type = None
        self.bug_line = -1
        self.mutated = False

    def visit_BinOp(self, node):
        """Mutation: Swap math operators"""
        if self.mutated: return node
        # FORCE MUTATION for debugging (100% chance if node exists)
        if random.random() < 1.0: 
            original_op = type(node.op)
            if isinstance(node.op, ast.Add): node.op = ast.Sub()
            elif isinstance(node.op, ast.Sub): node.op = ast.Add()
            elif isinstance(node.op, ast.Mult): node.op = ast.Div()
            elif isinstance(node.op, ast.Div): node.op = ast.Mult()
            
            if type(node.op) != original_op:
                self.bug_type = "Operator Error"
                self.bug_line = getattr(node, 'lineno', 0)
                self.mutated = True
                print(f"[MUTATOR] Swapped operator at line {self.bug_line}")
        return self.generic_visit(node)
    
    # ... (Include other visit methods if you wish, but BinOp is enough to test) ...

def generate_buggy_code(source_code):
    """
    Returns: (buggy_code, mutation_metadata)
    
    mutation_metadata is None if no mutation occurred.
    Otherwise, it is an instance of MutationMetadata.
    
    Uses targeted string replacement instead of ast.unparse() so that
    line numbers are preserved (critical for localizer ground truth).
    """
    try:
        tree = ast.parse(source_code)
        injector = AdvancedBugInjector()
        injector.visit(tree)
        
        if injector.mutated and injector.metadata:
            meta = injector.metadata
            lines = source_code.splitlines(keepends=True)
            
            if 1 <= meta.lineno <= len(lines):
                line = lines[meta.lineno - 1]
                # Search for original_token starting at/after col_offset
                idx = line.find(meta.original_token, meta.col_offset)
                if idx == -1:
                    # Fallback: search from beginning of line
                    idx = line.find(meta.original_token)
                if idx != -1:
                    new_line = (
                        line[:idx]
                        + meta.buggy_token
                        + line[idx + len(meta.original_token):]
                    )
                    lines[meta.lineno - 1] = new_line
                    new_code = ''.join(lines)
                    return new_code, meta
            
    except Exception as e:
        # Silently fail on parse errors (common in generated code)
        pass
        
    return None, None