"""
API routes for graph analysis
"""
from fastapi import APIRouter, HTTPException
from app.schemas.graph import AnalyzeRequest, AnalyzeResponse, FunctionAnalysis
from app.services.graph_service import GraphService

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_code(req: AnalyzeRequest):
    """
    Analyze source code and return AST, CFG, and DFG representations
    """
    try:
        # Build all graphs using the service
        service = GraphService(req.source_code)
        graphs = service.build_all_graphs()
        
        # Debug output
        print(f"Found {len(graphs.get('functions', []))} functions")
        
        # Ensure functions list exists
        functions = graphs.get("functions", [])
        if not functions:
            print("WARNING: No functions found in analysis")
        
        return {
            "ast": graphs["ast"],
            "functions": functions,
            "source_code": req.source_code
        }
    
    except Exception as e:
        print(f"Error in analyze_code: {e}")
        import traceback
        traceback.print_exc()
        
        # Create error response
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing code: {str(e)}"
        )


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "graph-analysis"}