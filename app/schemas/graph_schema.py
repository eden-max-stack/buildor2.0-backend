"""
Pydantic schemas for graph analysis API
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union


class AnalyzeRequest(BaseModel):
    """Request schema for graph analysis"""
    source_code: str


# Forward declaration for recursive AST nodes
class ASTNode(BaseModel):
    id: int
    type: str
    role: Optional[str] = None
    symbol: Optional[str] = None
    operator: Optional[str] = None
    text: str
    source_span: Optional[List[int]] = None
    children: List['ASTNode']


# Update the forward reference
ASTNode.update_forward_refs()


class ASTResponse(BaseModel):
    """AST response schema"""
    root: ASTNode
    node_count: int


class CFGNodeSchema(BaseModel):
    """CFG Node schema"""
    id: int
    label: str
    ast_node_id: Optional[int] = None
    ast_node_type: Optional[str] = None


class CFGEdgeSchema(BaseModel):
    """CFG Edge schema"""
    source: int
    target: int
    condition: Optional[str] = None


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


class FunctionAnalysis(BaseModel):
    """Analysis for a single function"""
    name: str
    ast_node_id: int
    cfg: CFGResponse
    dfg: DFGResponse


class AnalyzeResponse(BaseModel):
    """Complete graph analysis response"""
    ast: Dict[str, Any]  # Using Dict for flexibility with nested structure
    functions: List[FunctionAnalysis]
    source_code: str