import ast

def ast_to_graph(ast_tree):
    nodes = []
    edges = []

    node_id = 0

    def visit(node, parent_id=None):
        nonlocal node_id
        curr_id = f"n{node_id}"
        node_id += 1

        nodes.append({
            "id": curr_id,
            "type": type(node).__name__,
            "label": type(node).__name__,
            "line": getattr(node, "lineno", -1),
            "status": "normal"
        })

        if parent_id:
            edges.append({
                "source": parent_id,
                "target": curr_id,
                "type": "AST"
            })

        for child in ast.iter_child_nodes(node):
            visit(child, curr_id)

    visit(ast_tree)
    return nodes, edges
