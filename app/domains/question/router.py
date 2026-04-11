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
    tc_id: str
    input: Dict[str, Any]
    expected_output: Any
    is_sample: bool

class McqOptionResponse(BaseModel):
    option_id: str
    option_text: str
    is_correct: bool

class QuestionDetailResponse(BaseModel):
    question_id: str
    trainer_id: str
    type: str
    title: str
    description: str
    difficulty: Optional[str]
    tags: List[str]
    constraints: Optional[str]
    total_submissions: int
    successful_submissions: int
    optimal_solution: Optional[str]
    test_cases: List[TestCaseResponse]
    mcq_options: List[McqOptionResponse]

class QuestionListItem(BaseModel):
    question_id: str
    title: str
    difficulty: Optional[str]
    tags: List[str]

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
                SELECT question_id
                FROM public.questions
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
            question_id,
            trainer_id,
            type,
            title,
            description,
            difficulty,
            tags,
            constraints,
            total_submissions,
            successful_submissions,
            optimal_solution
        FROM public.questions
        WHERE question_id = :question_id
    """)
    
    result = db.execute(query, {"question_id": resolved_question_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Fetch test cases
    test_cases_query = text("""
        SELECT 
            tc_id,
            input,
            expected_output,
            is_sample
        FROM public.test_cases
        WHERE question_id = :question_id
        ORDER BY tc_id ASC
    """)
    
    test_cases_result = db.execute(test_cases_query, {"question_id": resolved_question_id}).fetchall()
    
    # Build test cases list
    test_cases = []
    for tc in test_cases_result:
        test_cases.append({
            "tc_id": str(tc[0]),
            "input": tc[1],
            "expected_output": tc[2],
            "is_sample": tc[3]
        })

    # Fetch MCQ options
    mcq_options_query = text("""
        SELECT 
            option_id,
            option_text,
            is_correct
        FROM public.mcq_options
        WHERE question_id = :question_id
        ORDER BY option_id ASC
    """)
    
    mcq_options_result = db.execute(mcq_options_query, {"question_id": resolved_question_id}).fetchall()
    
    mcq_options = []
    for opt in mcq_options_result:
        mcq_options.append({
            "option_id": str(opt[0]),
            "option_text": opt[1],
            "is_correct": opt[2]
        })
    
    return {
        "question_id": str(result[0]),
        "trainer_id": str(result[1]),
        "type": result[2],
        "title": result[3],
        "description": result[4],
        "difficulty": result[5],
        "tags": result[6] or [],
        "constraints": result[7],
        "total_submissions": result[8],
        "successful_submissions": result[9],
        "optimal_solution": result[10],
        "test_cases": test_cases,
        "mcq_options": mcq_options
    }

@router.get("/", response_model=List[QuestionListItem])
def list_questions(
    difficulty: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all questions with optional filtering.
    """
    # Check SQLite guard
    dialect = str(getattr(getattr(engine, "url", None), "drivername", ""))
    if dialect.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Build query with optional difficulty filter
    where_clause = "WHERE 1=1"
    params = {"limit": limit, "offset": offset}
    
    if difficulty:
        where_clause += " AND difficulty = :difficulty"
        params["difficulty"] = difficulty
    
    query = text(f"""
        SELECT 
            question_id,
            title,
            difficulty,
            tags
        FROM public.questions
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    results = db.execute(query, params).fetchall()
    
    questions = []
    for row in results:
        questions.append({
            "question_id": str(row[0]),
            "title": row[1],
            "difficulty": row[2],
            "tags": row[3] or []
        })
    
    return questions