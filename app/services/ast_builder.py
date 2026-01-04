import ast

def build_ast(code: str):
    tree = ast.parse(code)
    return tree
