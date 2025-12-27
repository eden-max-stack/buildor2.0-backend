from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from tree_sitter import Language, Parser, Tree, Node
import tree_sitter_python as tsp
from typing import Generator

PY_LANGUAGE = Language(tsp.language())

class TreeSitterParser:
    def __init__(self):
        self.parser = Parser(PY_LANGUAGE)

    def parse(self, source_code: str) -> Tree:
        return self.parser.parse(source_code.encode("utf8"))

@dataclass
class ASTNode:
    """internal language-agnostic IR"""
    type: str 
    children: List["ASTNode"] = field(default_factory=list) # new list is created for each instance (callable executed each time)
    source_span: Optional[Tuple[int, int]] = None

    symbol: Optional[str] = None
    role: Optional[str] = None
    operator: Optional[str] = None

    def get_text(self, source_code: str) -> str:
        """lazily getting text for node instead of storing it directly -> prevents bloating the IR"""
        if self.source_span is None:
            return ""
        
        start, end = self.source_span
        return source_code[start:end]
    
    def print_pretty(self, indent=0):
        print('  ' * indent + self.type)
        for child in self.children:
            child.print_pretty(indent + 1)

    def traverse_node(self) -> Generator["ASTNode", None, None]:
        """Generator — preorder traversal of nodes."""
        yield self
        for c in self.children:
            yield from c.traverse_nodes()

class AST:
    """this is the AST as a whole graph"""
    def __init__(self, root: ASTNode):
        self.root = root

    def traverse(self):
        yield from self.root.traverse_node()

class ASTBuilder:
    """converts the TreeSitter parse tree into my AST representation"""
    def __init__(self, source_code: str):
        self.source_code = source_code

    def build(self, ts_node: Node) -> ASTNode:
        start = ts_node.start_byte
        end = ts_node.end_byte

        node = ASTNode(
            type=ts_node.type,
            source_span=(start, end),
        )

        for child in ts_node.children:
            node.children.append(self.build(child))

        return node
