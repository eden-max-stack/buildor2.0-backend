from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.infrastructure.database import get_db

router = APIRouter(prefix="/classes", tags=["Class Questions"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class TestCaseCreate(BaseModel):
    input: dict
    expected_output: dict
    is_sample: bool = False
    is_hidden: bool = True
    difficulty: Optional[str] = "basic"
    order_index: int = 0


class QuestionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    difficulty: str = Field(..., pattern="^(Easy|Medium|Hard)$")
    tags: List[str] = Field(..., min_items=1)
    constraints: List[str] = []
    optimal_solution: str
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    test_cases: List[TestCaseCreate] = Field(..., min_items=1)


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    difficulty: Optional[str] = Field(None, pattern="^(Easy|Medium|Hard)$")
    tags: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    optimal_solution: Optional[str] = None
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    is_active: Optional[bool] = None


class TestCaseResponse(BaseModel):
    id: str
    input: dict
    expected_output: dict
    is_sample: bool
    is_hidden: bool
    difficulty: Optional[str]
    order_index: int


class QuestionResponse(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    tags: List[str]
    constraints: List[str]
    optimal_solution: str
    time_complexity: Optional[str]
    space_complexity: Optional[str]
    acceptance_rate: Optional[float]
    total_submissions: int
    successful_submissions: int
    created_by: str
    created_at: str
    updated_at: str
    is_active: bool
    test_cases: List[TestCaseResponse] = []


# ============================================
# ENDPOINTS
# ============================================

@router.post("/{class_id}/questions", response_model=QuestionResponse, status_code=201)
def create_class_question(
    class_id: str,
    question_data: QuestionCreate,
    trainer_id: UUID = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Create a new question for a specific class.
    
    **Requirements:**
    - Trainer must own the class
    - Question must have at least one test case
    - Title, description, difficulty, tags, and optimal solution are required
    
    **Returns:**
    - Created question with all details including test cases
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify trainer owns the class
    class_check = db.execute(
        text("SELECT id, trainer_id FROM classes WHERE id = :class_id"),
        {"class_id": class_id}
    ).fetchone()
    
    if not class_check:
        raise HTTPException(status_code=404, detail="Class not found")
    
    if str(class_check.trainer_id) != str(trainer_id):
        raise HTTPException(status_code=403, detail="Access denied: Not your class")
    
    # Insert question
    question_insert = text("""
        INSERT INTO questions (
            title, description, difficulty, tags, constraints,
            optimal_solution, time_complexity, space_complexity,
            created_by, is_active
        )
        VALUES (
            :title, :description, :difficulty, :tags, :constraints,
            :optimal_solution, :time_complexity, :space_complexity,
            :created_by, true
        )
        RETURNING id, created_at, updated_at
    """)
    
    question_result = db.execute(question_insert, {
        "title": question_data.title,
        "description": question_data.description,
        "difficulty": question_data.difficulty,
        "tags": question_data.tags,
        "constraints": question_data.constraints,
        "optimal_solution": question_data.optimal_solution,
        "time_complexity": question_data.time_complexity,
        "space_complexity": question_data.space_complexity,
        "created_by": str(trainer_id)
    }).fetchone()
    
    question_id = str(question_result.id)
    
    # Insert test cases
    test_case_responses = []
    for idx, tc in enumerate(question_data.test_cases):
        tc_insert = text("""
            INSERT INTO test_cases (
                question_id, input, expected_output, is_sample,
                is_hidden, difficulty, order_index
            )
            VALUES (
                :question_id, CAST(:input_json AS JSONB), CAST(:expected_output_json AS JSONB), :is_sample,
                :is_hidden, :difficulty, :order_index
            )
            RETURNING id
        """)
        
        tc_result = db.execute(tc_insert, {
            "question_id": question_id,
            "input_json": json.dumps(tc.input),
            "expected_output_json": json.dumps(tc.expected_output),
            "is_sample": tc.is_sample,
            "is_hidden": tc.is_hidden,
            "difficulty": tc.difficulty,
            "order_index": idx
        }).fetchone()
        
        test_case_responses.append(TestCaseResponse(
            id=str(tc_result.id),
            input=tc.input,
            expected_output=tc.expected_output,
            is_sample=tc.is_sample,
            is_hidden=tc.is_hidden,
            difficulty=tc.difficulty,
            order_index=idx
        ))
    
    db.commit()
    
    return QuestionResponse(
        id=question_id,
        title=question_data.title,
        description=question_data.description,
        difficulty=question_data.difficulty,
        tags=question_data.tags,
        constraints=question_data.constraints,
        optimal_solution=question_data.optimal_solution,
        time_complexity=question_data.time_complexity,
        space_complexity=question_data.space_complexity,
        acceptance_rate=None,
        total_submissions=0,
        successful_submissions=0,
        created_by=str(trainer_id),
        created_at=question_result.created_at.isoformat(),
        updated_at=question_result.updated_at.isoformat(),
        is_active=True,
        test_cases=test_case_responses
    )


@router.get("/{class_id}/questions", response_model=List[QuestionResponse])
def get_class_questions(
    class_id: str,
    trainer_id: Optional[UUID] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all questions for a specific class.
    
    **Query Parameters:**
    - `trainer_id` (optional): Verify trainer access
    - `include_inactive` (optional): Include inactive questions (default: false)
    
    **Returns:**
    - List of questions with test cases
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify class exists
    class_check = db.execute(
        text("SELECT id, trainer_id FROM classes WHERE id = :class_id"),
        {"class_id": class_id}
    ).fetchone()
    
    if not class_check:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Optional trainer verification
    if trainer_id and str(class_check.trainer_id) != str(trainer_id):
        raise HTTPException(status_code=403, detail="Access denied: Not your class")
    
    # Get questions created by the class trainer
    active_filter = "" if include_inactive else "AND q.is_active = true"
    
    questions_query = text(f"""
        SELECT 
            q.id, q.title, q.description, q.difficulty, q.tags,
            q.constraints, q.optimal_solution, q.time_complexity,
            q.space_complexity, q.acceptance_rate, q.total_submissions,
            q.successful_submissions, q.created_by, q.created_at,
            q.updated_at, q.is_active
        FROM questions q
        WHERE q.created_by = :trainer_id {active_filter}
        ORDER BY q.created_at DESC
    """)
    
    questions = db.execute(questions_query, {
        "trainer_id": str(class_check.trainer_id)
    }).fetchall()
    
    result = []
    for q in questions:
        # Get test cases for this question
        test_cases_query = text("""
            SELECT id, input, expected_output, is_sample, is_hidden,
                   difficulty, order_index
            FROM test_cases
            WHERE question_id = :question_id
            ORDER BY order_index ASC
        """)
        
        test_cases = db.execute(test_cases_query, {
            "question_id": str(q.id)
        }).fetchall()
        
        test_case_responses = [
            TestCaseResponse(
                id=str(tc.id),
                input=tc.input,
                expected_output=tc.expected_output,
                is_sample=tc.is_sample,
                is_hidden=tc.is_hidden,
                difficulty=tc.difficulty,
                order_index=tc.order_index
            )
            for tc in test_cases
        ]
        
        result.append(QuestionResponse(
            id=str(q.id),
            title=q.title,
            description=q.description,
            difficulty=q.difficulty,
            tags=q.tags,
            constraints=q.constraints,
            optimal_solution=q.optimal_solution,
            time_complexity=q.time_complexity,
            space_complexity=q.space_complexity,
            acceptance_rate=float(q.acceptance_rate) if q.acceptance_rate else None,
            total_submissions=q.total_submissions or 0,
            successful_submissions=q.successful_submissions or 0,
            created_by=str(q.created_by),
            created_at=q.created_at.isoformat(),
            updated_at=q.updated_at.isoformat(),
            is_active=q.is_active,
            test_cases=test_case_responses
        ))
    
    return result


@router.patch("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: UUID,
    question_update: QuestionUpdate,
    trainer_id: UUID = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Update an existing question.
    
    **Requirements:**
    - Trainer must be the creator of the question
    - Only provided fields will be updated
    
    **Returns:**
    - Updated question details
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify question exists and trainer owns it
    question_check = db.execute(
        text("SELECT id, created_by FROM questions WHERE id = :question_id"),
        {"question_id": str(question_id)}
    ).fetchone()
    
    if not question_check:
        raise HTTPException(status_code=404, detail="Question not found")
    
    if str(question_check.created_by) != str(trainer_id):
        raise HTTPException(status_code=403, detail="Access denied: Not your question")
    
    # Build update query dynamically
    update_fields = []
    params = {"question_id": str(question_id)}
    
    if question_update.title is not None:
        update_fields.append("title = :title")
        params["title"] = question_update.title
    
    if question_update.description is not None:
        update_fields.append("description = :description")
        params["description"] = question_update.description
    
    if question_update.difficulty is not None:
        update_fields.append("difficulty = :difficulty")
        params["difficulty"] = question_update.difficulty
    
    if question_update.tags is not None:
        update_fields.append("tags = :tags")
        params["tags"] = question_update.tags
    
    if question_update.constraints is not None:
        update_fields.append("constraints = :constraints")
        params["constraints"] = question_update.constraints
    
    if question_update.optimal_solution is not None:
        update_fields.append("optimal_solution = :optimal_solution")
        params["optimal_solution"] = question_update.optimal_solution
    
    if question_update.time_complexity is not None:
        update_fields.append("time_complexity = :time_complexity")
        params["time_complexity"] = question_update.time_complexity
    
    if question_update.space_complexity is not None:
        update_fields.append("space_complexity = :space_complexity")
        params["space_complexity"] = question_update.space_complexity
    
    if question_update.is_active is not None:
        update_fields.append("is_active = :is_active")
        params["is_active"] = question_update.is_active
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields.append("updated_at = NOW()")
    
    update_query = text(f"""
        UPDATE questions
        SET {', '.join(update_fields)}
        WHERE id = :question_id
        RETURNING id, title, description, difficulty, tags, constraints,
                  optimal_solution, time_complexity, space_complexity,
                  acceptance_rate, total_submissions, successful_submissions,
                  created_by, created_at, updated_at, is_active
    """)
    
    updated_question = db.execute(update_query, params).fetchone()
    
    # Get test cases
    test_cases_query = text("""
        SELECT id, input, expected_output, is_sample, is_hidden,
               difficulty, order_index
        FROM test_cases
        WHERE question_id = :question_id
        ORDER BY order_index ASC
    """)
    
    test_cases = db.execute(test_cases_query, {
        "question_id": str(question_id)
    }).fetchall()
    
    test_case_responses = [
        TestCaseResponse(
            id=str(tc.id),
            input=tc.input,
            expected_output=tc.expected_output,
            is_sample=tc.is_sample,
            is_hidden=tc.is_hidden,
            difficulty=tc.difficulty,
            order_index=tc.order_index
        )
        for tc in test_cases
    ]
    
    db.commit()
    
    return QuestionResponse(
        id=str(updated_question.id),
        title=updated_question.title,
        description=updated_question.description,
        difficulty=updated_question.difficulty,
        tags=updated_question.tags,
        constraints=updated_question.constraints,
        optimal_solution=updated_question.optimal_solution,
        time_complexity=updated_question.time_complexity,
        space_complexity=updated_question.space_complexity,
        acceptance_rate=float(updated_question.acceptance_rate) if updated_question.acceptance_rate else None,
        total_submissions=updated_question.total_submissions or 0,
        successful_submissions=updated_question.successful_submissions or 0,
        created_by=str(updated_question.created_by),
        created_at=updated_question.created_at.isoformat(),
        updated_at=updated_question.updated_at.isoformat(),
        is_active=updated_question.is_active,
        test_cases=test_case_responses
    )
