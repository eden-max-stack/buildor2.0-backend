from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.infrastructure.database import get_db, engine
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import sys
import os
import datetime
from app.infrastructure.supabase_client import supabase

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
@router.post("/hint", response_model=HintResponse)
def get_hint(request: HintRequest):
    """
    Generate a hint for the user's code using the 5-layer hint engine.
    """
    try:
        # 1. Verify question exists and get optimal solution
        q_res = supabase.table("questions").select("question_id, optimal_solution").eq("question_id", request.question_id).execute()
        
        if not q_res.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        optimal_solution = q_res.data[0].get("optimal_solution")
        if not optimal_solution:
            raise HTTPException(
                status_code=400, 
                detail="No optimal solution available for this question"
            )
        
        # 2. Fetch test cases 
        tc_res = supabase.table("test_cases").select("*").eq("question_id", request.question_id).execute()
        test_cases = tc_res.data
        
        if not test_cases:
            raise HTTPException(status_code=400, detail="No test cases found for this question")
        
        # 3. Execute code against all test cases
        all_tests_passed = True
        passed_count = 0
        
        for tc in test_cases:
            tc_input = tc.get("input", {})
            tc_expected = tc.get("expected_output")
            
            # Execute code
            exec_result = execute_python_code(request.user_code, tc_input)
            
            if exec_result["success"]:
                passed = compare_outputs(exec_result["output"], tc_expected)
                if passed:
                    passed_count += 1
                else:
                    all_tests_passed = False
                    break
            else:
                all_tests_passed = False
                break
        
        # 4. Calculate "attempts" by counting rows in the submissions table
        subs_res = supabase.table("submissions").select("submission_id", count="exact").eq("user_id", request.user_id).eq("question_id", request.question_id).execute()
        attempts = subs_res.count if subs_res.count is not None else 0

        # 5. Generate Hint or Success Message
        if all_tests_passed and passed_count == len(test_cases):
            hint_result = {
                "hint": "All your test cases have passed. Your solution is correct!",
                "analysis": {
                    "bug_type": "None",
                    "confidence": 1.0,
                    "tests_passed": passed_count,
                    "total_tests": len(test_cases)
                }
            }
        else:
            # Calculate tests_failed_ratio based on past submission attempts
            tests_failed_ratio = min(0.9, attempts * 0.2) if attempts > 0 else 0.5
            
            if not HINT_ENGINE_AVAILABLE:
                hint_result = {
                    "hint": "Review your logic carefully. Check edge cases and boundary conditions.",
                    "analysis": {"bug_type": "Unknown", "confidence": 0.0, "note": "Hint engine not available"}
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
                        hint_result = {
                            "hint": "Check your code for syntax errors and logical issues. Review the problem constraints.",
                            "analysis": {"error": hint_result.get("error"), "bug_type": "Unknown"}
                        }
                except Exception as e:
                    print(f"Hint generation error: {e}")
                    hint_result = {
                        "hint": "Review your algorithm and check for common mistakes like off-by-one errors or incorrect operators.",
                        "analysis": {"error": str(e), "bug_type": "Unknown"}
                    }
        
        # 6. Return response (Skipping the DB upsert since you don't have the progress schema)
        return {
            "hint": hint_result.get("hint", "No hint available"),
            "analysis": hint_result.get("analysis"),
            "hints_used": 1 # Hardcoded to 1 so the frontend UI doesn't break
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in hint endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))