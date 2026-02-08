import ast
import random
import os
import sys

# --- DEBUG PRINT: Shows exactly which file is being loaded ---
print(f"\n[DEBUG] Mutator loaded from: {os.path.abspath(__file__)}")

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
    try:
        print("[MUTATOR] Attempting to mutate code...")
        tree = ast.parse(source_code)
        injector = BugInjector()
        new_tree = injector.visit(tree)
        
        if injector.mutated:
            print(f"[MUTATOR] Success! Type: {injector.bug_type}")
            # Try unparse
            if hasattr(ast, 'unparse'):
                return ast.unparse(new_tree), injector.bug_type, injector.bug_line
            else:
                import astor
                return astor.to_source(new_tree), injector.bug_type, injector.bug_line
        else:
            print("[MUTATOR] No suitable nodes found to mutate.")
            return None, None, None
            
    except Exception as e:
        print(f"[MUTATOR ERROR] {e}")
        return None, None, None