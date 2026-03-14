from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.infrastructure.database import get_db, engine
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from uuid import UUID
import json

router = APIRouter(prefix="/questions", tags=["Questions"])

# ============================================
# PYDANTIC MODELS
# ============================================

class TestCaseResponse(BaseModel):
    id: str
    input: Dict[str, Any]
    expected_output: Any
    is_sample: bool
    is_hidden: bool
    difficulty: Optional[str]
    order_index: int

class QuestionDetailResponse(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    tags: List[str]
    constraints: List[str]
    acceptance_rate: Optional[float]
    total_submissions: int
    successful_submissions: int
    optimal_solution: Optional[str]
    time_complexity: Optional[str]
    space_complexity: Optional[str]
    test_cases: List[TestCaseResponse]

class QuestionListItem(BaseModel):
    id: str
    title: str
    difficulty: str
    tags: List[str]
    acceptance_rate: Optional[float]

# ============================================
# ENDPOINTS
# ============================================

@router.get("/{question_id}", response_model=QuestionDetailResponse)
def get_question_details(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Get complete question details including test cases for the sandbox page.
    """
    # Check SQLite guard
    dialect = str(getattr(getattr(engine, "url", None), "drivername", ""))
    if dialect.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Resolve question identifier (UUID or numeric index)
    resolved_question_id: Optional[str] = None
    try:
        resolved_question_id = str(UUID(str(question_id)))
    except Exception:
        if str(question_id).isdigit():
            idx = int(str(question_id))
            if idx <= 0:
                raise HTTPException(status_code=422, detail="question_id must be a UUID or a positive integer")
            resolve_query = text("""
                SELECT id
                FROM public.questions
                WHERE is_active = true
                ORDER BY created_at ASC
                LIMIT 1 OFFSET :offset
            """)
            resolved = db.execute(resolve_query, {"offset": idx - 1}).fetchone()
            if not resolved:
                raise HTTPException(status_code=404, detail="Question not found")
            resolved_question_id = str(resolved[0])
        else:
            raise HTTPException(status_code=422, detail="question_id must be a UUID or a positive integer")

    # Fetch question details
    query = text("""
        SELECT 
            id,
            title,
            description,
            difficulty,
            tags,
            constraints,
            acceptance_rate,
            total_submissions,
            successful_submissions,
            optimal_solution,
            time_complexity,
            space_complexity
        FROM public.questions
        WHERE id = :question_id AND is_active = true
    """)
    
    result = db.execute(query, {"question_id": resolved_question_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Fetch test cases
    test_cases_query = text("""
        SELECT 
            id,
            input,
            expected_output,
            is_sample,
            is_hidden,
            difficulty,
            order_index
        FROM public.test_cases
        WHERE question_id = :question_id
        ORDER BY order_index ASC, created_at ASC
    """)
    
    test_cases_result = db.execute(test_cases_query, {"question_id": resolved_question_id}).fetchall()
    
    # Build test cases list
    test_cases = []
    for tc in test_cases_result:
        test_cases.append({
            "id": str(tc[0]),
            "input": tc[1],
            "expected_output": tc[2],
            "is_sample": tc[3],
            "is_hidden": tc[4],
            "difficulty": tc[5],
            "order_index": tc[6]
        })
    
    return {
        "id": str(result[0]),
        "title": result[1],
        "description": result[2],
        "difficulty": result[3],
        "tags": result[4] or [],
        "constraints": result[5] or [],
        "acceptance_rate": float(result[6]) if result[6] else None,
        "total_submissions": result[7],
        "successful_submissions": result[8],
        "optimal_solution": result[9],
        "time_complexity": result[10],
        "space_complexity": result[11],
        "test_cases": test_cases
    }

@router.get("/", response_model=List[QuestionListItem])
def list_questions(
    difficulty: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all active questions with optional filtering.
    """
    # Check SQLite guard
    dialect = str(getattr(getattr(engine, "url", None), "drivername", ""))
    if dialect.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Build query with optional difficulty filter
    where_clause = "WHERE is_active = true"
    params = {"limit": limit, "offset": offset}
    
    if difficulty:
        where_clause += " AND difficulty = :difficulty"
        params["difficulty"] = difficulty
    
    query = text(f"""
        SELECT 
            id,
            title,
            difficulty,
            tags,
            acceptance_rate
        FROM public.questions
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    results = db.execute(query, params).fetchall()
    
    questions = []
    for row in results:
        questions.append({
            "id": str(row[0]),
            "title": row[1],
            "difficulty": row[2],
            "tags": row[3] or [],
            "acceptance_rate": float(row[4]) if row[4] else None
        })
    
    return questions