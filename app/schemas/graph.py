# from pydantic import BaseModel
# from typing import List

# class GraphRequest(BaseModel):
#     student_code: str
#     reference_code: str
#     language: str

# class GraphNode(BaseModel):
#     id: str
#     type: str
#     label: str
#     line: int
#     status: str  # normal | error

# class GraphEdge(BaseModel):
#     source: str
#     target: str
#     type: str

# class GraphResponse(BaseModel):
#     graph: dict
#     error_nodes: List[str]
#     error_type: str
#     confidence: float


"""
Pydantic schemas for graph analysis API
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class AnalyzeRequest(BaseModel):
    """Request schema for graph analysis"""
    source_code: str


class ASTNode(BaseModel):
    """AST Node schema"""
    id: int
    type: str
    role: Optional[str]
    symbol: Optional[str]
    operator: Optional[str]
    text: str
    source_span: Optional[tuple]
    children: List['ASTNode']


class ASTResponse(BaseModel):
    """AST response schema"""
    root: ASTNode
    node_count: int


class CFGNodeSchema(BaseModel):
    """CFG Node schema"""
    id: int
    label: str
    ast_node_id: Optional[int]
    ast_node_type: Optional[str]


class CFGEdgeSchema(BaseModel):
    """CFG Edge schema"""
    source: int
    target: int
    condition: Optional[str]


class CFGResponse(BaseModel):
    """CFG response schema"""
    nodes: List[CFGNodeSchema]
    edges: List[CFGEdgeSchema]
    entry_id: int
    exit_id: int


class DFGNodeSchema(BaseModel):
    """DFG Node schema"""
    id: int
    variable: str
    is_definition: bool
    cfg_node_id: int
    ast_node_id: int
    ast_node_type: str


class DFGEdgeSchema(BaseModel):
    """DFG Edge schema"""
    source: int
    target: int
    variable: str


class DFGResponse(BaseModel):
    """DFG response schema"""
    nodes: List[DFGNodeSchema]
    edges: List[DFGEdgeSchema]
    definitions: Dict[str, List[int]]
    uses: Dict[str, List[int]]


class AnalyzeResponse(BaseModel):
    """Complete graph analysis response"""
    ast: Dict[str, Any]  # Using Dict for flexibility with nested structure
    cfg: CFGResponse
    dfg: DFGResponse
    source_code: str