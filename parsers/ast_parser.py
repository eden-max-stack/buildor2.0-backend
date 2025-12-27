from models.ast_models import AST, TreeSitterParser, ASTBuilder

source_code = """
def add(a, b):
    return a + b
"""

parser = TreeSitterParser()
tree = parser.parse(source_code)

builder = ASTBuilder(source_code    )
ast_root = builder.build(tree.root_node)

ast = AST(ast_root)
ast.root.print_pretty()