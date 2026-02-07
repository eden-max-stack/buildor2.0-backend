from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/analysis", tags=["Code Analysis"])

class CodeInput(BaseModel):
    code: str

@router.post("/run")
def analyze_code(data: CodeInput):
    return {
        "ast_nodes": 15,
        "complexity": "O(n)",
        "suggestion": "Consider optimizing loop."
    }
