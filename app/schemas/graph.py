from pydantic import BaseModel
from typing import List

class GraphRequest(BaseModel):
    student_code: str
    reference_code: str
    language: str

class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    line: int
    status: str  # normal | error

class GraphEdge(BaseModel):
    source: str
    target: str
    type: str

class GraphResponse(BaseModel):
    graph: dict
    error_nodes: List[str]
    error_type: str
    confidence: float
