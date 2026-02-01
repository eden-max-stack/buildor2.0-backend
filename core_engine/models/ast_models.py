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
    id: Optional[int] = None
    children: List["ASTNode"] = field(default_factory=list)
    source_span: Optional[Tuple[int, int]] = None

    symbol: Optional[str] = None
    role: Optional[str] = None
    operator: Optional[str] = None

    parent: Optional["ASTNode"] = None

    def get_text(self, source_code: str) -> str:
        """lazily getting text for node instead of storing it directly -> prevents bloating the IR"""
        if self.source_span is None:
            return ""
        
        start, end = self.source_span
        return source_code[start:end]

    def print_pretty(self, indent=0):
        label = self.type
        if self.role:
            label += f" ({self.role})"

        print('  ' * indent + label)
        for child in self.children:
            child.print_pretty(indent + 1)

    def traverse_node(self) -> Generator["ASTNode", None, None]:
        """Generator – preorder traversal of nodes."""
        yield self
        for c in self.children:
            yield from c.traverse_node()
    
    def get_children_by_role(self, role: str) -> List["ASTNode"]:
        """Helper method for CFG building - get children with specific role"""
        return [child for child in self.children if child.role == role]
    
    def get_child_by_role(self, role: str) -> Optional["ASTNode"]:
        """Get first child with specific role"""
        children = self.get_children_by_role(role)
        return children[0] if children else None
    
    def get_child_by_type(self, node_type: str) -> Optional["ASTNode"]:
        """Get first child with specific type"""
        children = self.get_children_by_type(node_type)
        return children[0] if children else None
    
    def get_children_by_type(self, node_type: str) -> List["ASTNode"]:
        """Get children with specific type"""
        return [child for child in self.children if child.type == node_type]

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
        self._id_counter = 0

    def build(self, ts_node: Node, parent: Optional[ASTNode] = None) -> ASTNode:

        start, end = ts_node.start_byte, ts_node.end_byte
        node = ASTNode(
            id=self._id_counter,
            type=ts_node.type,
            source_span=(start, end),
        )

        self._id_counter += 1

        # Assign roles AFTER children are built
        if parent:
            if parent.type == "function_definition":
                if node.type == "block":
                    node.role = "function_body"

            elif parent.type == "if_statement":
                if ts_node.type == "comparison_operator":
                    node.role = "condition"
                elif ts_node.type == "block":
                    # FIXED: Count existing block children before this one
                    existing_blocks = sum(1 for c in parent.children if c.type == "block")
                    node.role = "then_branch" if existing_blocks == 0 else "else_branch"

            elif parent.type == "else_clause":  # ← ADD THIS
                if ts_node.type == "block":
                    node.role = "else_branch"

            elif parent.type == "while_statement":
                if ts_node.type == "parenthesized_expression":
                    node.role = "loop_condition"
                elif ts_node.type == "block":
                    node.role = "loop_body"

            elif parent.type == "for_statement":
                if ts_node.type == "block":
                    node.role = "loop_body"
                elif ts_node.type in ["pattern_list", "tuple_pattern", "identifier"]:
                    # This captures "x, y" in "for x, y in ..."
                    node.role = "loop_iterator" 
                elif node.role is None and ts_node.type not in ["in", "for", ":"]:
                    # This captures "enumerate(nums)" in "for ... in enumerate(nums)"
                    node.role = "loop_iterable"

            elif parent.type == "typed_parameter":
                if ts_node.type == "identifier":
                    node.role = "parameter_name"

            elif node.type == "return_statement":
                node.role = "return"
            else:
                # Only mark as statement if it's a statement-like node
                if node.type.endswith("_statement") or node.type in ["expression_statement", "assignment"]:
                    node.role = "statement"


        # Build children 
        for child in ts_node.children:
            child_node = self.build(child, parent=node)
            child_node.parent = node
            node.children.append(child_node)

        return node