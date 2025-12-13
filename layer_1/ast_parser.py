import tree_sitter_python as tsp
from tree_sitter import Language, Parser, Tree, Node
from typing import Generator

PY_LANGUAGE = Language(tsp.language())

parser = Parser(PY_LANGUAGE)
parser.language = PY_LANGUAGE

some_random_code = """
def hello_world():
    print('Hello, world!')
    if 1 + 1 == 2:
        return True
    else:
        i = 0
        while (i < 5):
            print("Counting:", i)

        return False
hello_world()
"""

def parse_source(sample_code: str):
    """Return the Tree and root node for a source string."""
    tree = parser.parse(bytes(sample_code, "utf8"))
    return tree, tree.root_node

def node_text(node, source: bytes):
    """Return the exact source text for a node."""
    return source[node.start_byte:node.end_byte].decode('utf8')

def print_pretty(node, source: bytes, indent=0):
    print('  ' * indent + f'{node.type}  [{node.start_point} - {node.end_point}]')
    for c in node.children:
        print_pretty(c, source, indent+1)

def traverse_nodes(node):
    """Generator — preorder traversal of nodes."""
    yield node
    for c in node.children:
        yield from traverse_nodes(c)

def collect_functions(root, source_bytes: bytes):
    """Return list of (name_node, func_node) for top-level functions (Python example)."""
    funcs = []
    for node in root.children:
        if node.type == 'function_definition':
            name_node = None
            for c in node.children:
                if c.type == 'identifier' or c.type == 'name':
                    name_node = c
                    break
            funcs.append((name_node, node))
    return funcs

def traverse_tree(tree: Tree) -> Generator[Node, None, None]:
    cursor = tree.walk()

    visited_children = False

    while True:
        if not visited_children:
            yield cursor.node
            if not cursor.goto_first_child():
                visited_children = True

        elif cursor.goto_next_sibling():
            visited_children = False

        elif not cursor.goto_parent():
            break

tree, root = parse_source(some_random_code)
print_pretty(root, bytes(some_random_code, "utf8"))

node_names = map(lambda node : node.type, traverse_tree(tree))

# print(list(node_names))
# print(tree.root_node.sexp())