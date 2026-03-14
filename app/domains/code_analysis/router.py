from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.infrastructure.database import get_db, engine
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import sys
import os

# Import submission execution functions
from app.domains.submission.router import execute_python_code, compare_outputs

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from full_hint_pipeline import generate_hint_pipeline
    HINT_ENGINE_AVAILABLE = True
except ImportError:
    HINT_ENGINE_AVAILABLE = False
    print("⚠ WARNING: Hint engine not available. Install dependencies or check full_hint_pipeline.py")

router = APIRouter(prefix="/analysis", tags=["Code Analysis"])

# ============================================
# PYDANTIC MODELS
# ============================================

class HintRequest(BaseModel):
    question_id: str
    user_id: str
    user_code: str
    skill_level: str = "medium"  # low, medium, high

class HintResponse(BaseModel):
    hint: str
    analysis: Optional[dict]
    hints_used: int

# ============================================
# ENDPOINTS
# ============================================

@router.post("/hint", response_model=HintResponse)
def get_hint(
    request: HintRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a hint for the user's code using the 5-layer hint engine.
    First runs code against test cases - if all pass, returns success message.
    Otherwise, generates AI hint. Tracks hints used per user per question.
    """
    # Check SQLite guard
    dialect = str(getattr(getattr(engine, "url", None), "drivername", ""))
    if dialect.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify question exists and get optimal solution
    question_query = text("""
        SELECT id, optimal_solution FROM public.questions 
        WHERE id = :question_id AND is_active = true
    """)
    question = db.execute(question_query, {"question_id": request.question_id}).fetchone()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    optimal_solution = question[1]
    
    if not optimal_solution:
        raise HTTPException(
            status_code=400, 
            detail="No optimal solution available for this question"
        )
    
    # ============================================
    # STEP 1: Run code against test cases first
    # ============================================
    
    # Fetch test cases
    test_cases_query = text("""
        SELECT id, input, expected_output, is_sample, is_hidden
        FROM public.test_cases
        WHERE question_id = :question_id
        ORDER BY order_index ASC
    """)
    test_cases = db.execute(test_cases_query, {"question_id": request.question_id}).fetchall()
    
    if not test_cases:
        raise HTTPException(status_code=400, detail="No test cases found for this question")
    
    # Execute code against all test cases
    all_tests_passed = True
    passed_count = 0
    
    for tc in test_cases:
        tc_id, tc_input, tc_expected, tc_is_sample, tc_is_hidden = tc
        
        # Execute code
        exec_result = execute_python_code(request.user_code, tc_input)
        
        if exec_result["success"]:
            # Compare output
            passed = compare_outputs(exec_result["output"], tc_expected)
            if passed:
                passed_count += 1
            else:
                all_tests_passed = False
                break
        else:
            # Runtime error
            all_tests_passed = False
            break
    
    # If all tests passed, return success message instead of hint
    if all_tests_passed and passed_count == len(test_cases):
        # Still update hints_used for tracking
        update_query = text("""
            INSERT INTO public.user_question_progress (
                user_id, question_id, status, attempts, hints_used_total,
                first_attempted_at, last_attempted_at
            )
            VALUES (
                :user_id, :question_id, 'attempted', 1, 1,
                NOW(), NOW()
            )
            ON CONFLICT (user_id, question_id)
            DO UPDATE SET
                hints_used_total = user_question_progress.hints_used_total + 1,
                last_attempted_at = NOW()
            RETURNING hints_used_total
        """)
        
        result = db.execute(update_query, {
            "user_id": request.user_id,
            "question_id": request.question_id
        }).fetchone()
        
        db.commit()
        
        updated_hints_used = result[0] if result else 1
        
        return {
            "hint": "All your test cases have passed. Your solution is correct!",
            "analysis": {
                "bug_type": "None",
                "confidence": 1.0,
                "tests_passed": passed_count,
                "total_tests": len(test_cases)
            },
            "hints_used": updated_hints_used
        }
    
    # ============================================
    # STEP 2: Tests failed - generate hint
    # ============================================
    
    # Get user's current progress to calculate tests_failed_ratio
    progress_query = text("""
        SELECT attempts, hints_used_total FROM public.user_question_progress
        WHERE user_id = :user_id AND question_id = :question_id
    """)
    progress = db.execute(progress_query, {
        "user_id": request.user_id,
        "question_id": request.question_id
    }).fetchone()
    
    current_hints_used = progress[1] if progress else 0
    attempts = progress[0] if progress else 0
    
    # Calculate tests_failed_ratio based on attempts (heuristic)
    # More attempts = likely more tests failing
    tests_failed_ratio = min(0.9, attempts * 0.2) if attempts > 0 else 0.5
    
    # Generate hint using the full pipeline
    if not HINT_ENGINE_AVAILABLE:
        # Fallback hint if engine not available
        hint_result = {
            "hint": "Review your logic carefully. Check edge cases and boundary conditions.",
            "analysis": {
                "bug_type": "Unknown",
                "confidence": 0.0,
                "note": "Hint engine not available"
            }
        }
    else:
        try:
            hint_result = generate_hint_pipeline(
                buggy_code=request.user_code,
                correct_code=optimal_solution,
                tests_failed_ratio=tests_failed_ratio,
                skill_level=request.skill_level
            )
            
            if "error" in hint_result:
                # If hint generation failed, provide generic hint
                hint_result = {
                    "hint": "Check your code for syntax errors and logical issues. Review the problem constraints.",
                    "analysis": {
                        "error": hint_result.get("error"),
                        "bug_type": "Unknown"
                    }
                }
        except Exception as e:
            print(f"Hint generation error: {e}")
            hint_result = {
                "hint": "Review your algorithm and check for common mistakes like off-by-one errors or incorrect operators.",
                "analysis": {
                    "error": str(e),
                    "bug_type": "Unknown"
                }
            }
    
    # Update hints_used in user_question_progress
    update_query = text("""
        INSERT INTO public.user_question_progress (
            user_id, question_id, status, attempts, hints_used_total,
            first_attempted_at, last_attempted_at
        )
        VALUES (
            :user_id, :question_id, 'attempted', 1, 1,
            NOW(), NOW()
        )
        ON CONFLICT (user_id, question_id)
        DO UPDATE SET
            hints_used_total = user_question_progress.hints_used_total + 1,
            last_attempted_at = NOW()
        RETURNING hints_used_total
    """)
    
    result = db.execute(update_query, {
        "user_id": request.user_id,
        "question_id": request.question_id
    }).fetchone()
    
    db.commit()
    
    updated_hints_used = result[0] if result else current_hints_used + 1
    
    return {
        "hint": hint_result.get("hint", "No hint available"),
        "analysis": hint_result.get("analysis"),
        "hints_used": updated_hints_used
    }