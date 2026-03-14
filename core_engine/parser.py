from core_engine.models.ast_models import AST, ASTNode, TreeSitterParser, ASTBuilder
from core_engine.models.cfg_models import CFGBuilder
from core_engine.models.dfg_models import DFGBuilder

source_code = """
def example(x):
    y = x + 1
    if x > 0:
        z = y * 2
        print(z)
    else:
        z = y * 3
        print(z)
    result = z + y
    return result
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
print("AST:")
ast.root.print_pretty()

functions = find_functions(ast.root)
print(f"Found {len(functions)} function(s) in the AST.")

cfg_builder = CFGBuilder()
dfg_builder = DFGBuilder(source_code)

for fn in functions:
    print("CFG:")
    cfg = cfg_builder.build(fn)
    cfg.print_pretty()

    print("DFG:")
    dfg = dfg_builder.build(fn, cfg)
    dfg.print_pretty()
