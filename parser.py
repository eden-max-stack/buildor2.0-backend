from models.ast_models import AST, ASTNode, TreeSitterParser, ASTBuilder
from models.cfg_models import CFGBuilder

source_code = """
def example(x):
    if x > 0:
        print("positive")
    else:
        print("negative")
    print("done")
"""

def find_functions(ast_root: ASTNode) -> list[ASTNode]:
    return [
        node for node in ast_root.traverse_node()
        if node.type == "function_definition"
    ]


parser = TreeSitterParser()
tree = parser.parse(source_code)

builder = ASTBuilder(source_code)
ast_root = builder.build(tree.root_node)

ast = AST(ast_root)
ast.root.print_pretty()

functions = find_functions(ast.root)
print(f"Found {len(functions)} function(s) in the AST.")

cfg_builder = CFGBuilder()
for fn in functions:
    cfg = cfg_builder.build(fn)
    cfg.print_pretty()