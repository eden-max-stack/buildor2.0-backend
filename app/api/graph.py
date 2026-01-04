from fastapi import APIRouter
from app.schemas.graph import GraphRequest, GraphResponse
from app.services.ast_builder import build_ast
from app.services.graph_builder import ast_to_graph
from app.services.graph_compare import compare_graphs
from app.services.error_localizer import classify_error

router = APIRouter()

@router.post("/analyze", response_model=GraphResponse)
def analyze_graph(req: GraphRequest):
    student_ast = build_ast(req.student_code)
    ref_ast = build_ast(req.reference_code)

    student_nodes, student_edges = ast_to_graph(student_ast)
    ref_nodes, _ = ast_to_graph(ref_ast)

    error_nodes = compare_graphs(student_nodes, ref_nodes)
    error_type, confidence = classify_error(error_nodes)

    return {
        "graph": {
            "nodes": student_nodes,
            "edges": student_edges
        },
        "error_nodes": error_nodes,
        "error_type": error_type,
        "confidence": confidence
    }
