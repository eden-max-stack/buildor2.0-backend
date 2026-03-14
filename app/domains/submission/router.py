from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.infrastructure.database import get_db, engine
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
import json
import sys
import io
import traceback
import time
import psutil
import os
import inspect

router = APIRouter(prefix="/submissions", tags=["Submissions"])

# ============================================
# PYDANTIC MODELS
# ============================================

class SubmissionCreate(BaseModel):
    question_id: str
    user_id: str
    code: str
    language: str = "python"

class TestCaseResult(BaseModel):
    test_case_id: str
    passed: bool
    input: dict
    expected_output: Any
    actual_output: Optional[Any]
    error_message: Optional[str]
    is_sample: bool

class SubmissionResponse(BaseModel):
    id: str
    question_id: str
    user_id: str
    status: str
    test_cases_passed: int
    total_test_cases: int
    runtime_ms: Optional[int]
    memory_kb: Optional[int]
    test_results: List[TestCaseResult]
    error_message: Optional[str]
    submitted_at: str

# ============================================
# CODE EXECUTION SERVICE
# ============================================

def execute_python_code(code: str, test_input: dict, timeout: int = 5) -> dict:
    """
    Execute Python code with given input and return output, runtime, and memory usage.
    """
    try:
        # Prepare execution environment
        exec_globals = {}
        exec_locals = {}
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        # Track memory before execution
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024  # KB
        
        # Track runtime
        start_time = time.perf_counter()
        
        # Execute the code
        exec(code, exec_globals, exec_locals)
        
        # Get the solution function.
        # Prefer a function explicitly named 'solution' for consistency with the sandbox UI.
        solution_func = exec_locals.get("solution")
        if not callable(solution_func):
            solution_func = None
            for name, obj in exec_locals.items():
                if callable(obj) and not name.startswith('_'):
                    solution_func = obj
                    break
        
        if not solution_func:
            return {
                "success": False,
                "error": "No solution function found in code",
                "output": None,
                "runtime_ms": 0,
                "memory_kb": 0
            }
        
        # Call the function with test input
        # Prefer mapping by function signature (kwargs) when possible.
        sig = inspect.signature(solution_func)
        param_names = [p.name for p in sig.parameters.values()]

        # Filter out obvious metadata keys (seed data has input1/input2... as descriptive strings)
        cleaned_input = {}
        for k, v in (test_input or {}).items():
            if isinstance(k, str) and k.lower().startswith("input") and isinstance(v, str):
                continue
            cleaned_input[k] = v

        result = None
        if cleaned_input and all(name in cleaned_input for name in param_names):
            kwargs = {name: cleaned_input[name] for name in param_names}
            result = solution_func(**kwargs)
        else:
            # Build positional args.
            # If inputs look like param1/param2/... order by numeric suffix.
            keys = list(cleaned_input.keys()) if cleaned_input else []
            param_keys = [k for k in keys if isinstance(k, str) and k.lower().startswith("param") and k[5:].isdigit()]
            if param_keys:
                param_keys_sorted = sorted(param_keys, key=lambda x: int(str(x)[5:]))
                args = [cleaned_input[k] for k in param_keys_sorted]
            else:
                args = [cleaned_input[k] for k in sorted(keys)]

            # Truncate/adjust to expected arity if possible
            expected_arity = len(param_names)
            if expected_arity >= 0 and len(args) > expected_arity:
                args = args[:expected_arity]

            result = solution_func(*args) if args else solution_func()
        
        # Calculate runtime and memory
        end_time = time.perf_counter()
        runtime_ms = int((end_time - start_time) * 1000)
        
        mem_after = process.memory_info().rss / 1024  # KB
        memory_kb = int(max(0, mem_after - mem_before))
        
        # Restore stdout
        sys.stdout = old_stdout
        
        return {
            "success": True,
            "output": result,
            "runtime_ms": runtime_ms,
            "memory_kb": memory_kb,
            "error": None
        }
        
    except Exception as e:
        sys.stdout = old_stdout
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "output": None,
            "runtime_ms": 0,
            "memory_kb": 0
        }

def compare_outputs(actual: Any, expected: Any) -> bool:
    """
    Compare actual output with expected output.
    Handles different data types and nested structures.
    """
    if type(actual) != type(expected):
        # Try converting if types don't match
        try:
            if isinstance(expected, (int, float)):
                actual = type(expected)(actual)
            elif isinstance(expected, str):
                actual = str(actual)
        except:
            return False
    
    if isinstance(expected, float):
        # For floats, use approximate comparison
        return abs(actual - expected) < 1e-6
    elif isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            return False
        return all(compare_outputs(a, e) for a, e in zip(actual, expected))
    elif isinstance(expected, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(compare_outputs(actual[k], expected[k]) for k in expected.keys())
    else:
        return actual == expected

# ============================================
# ENDPOINTS
# ============================================

@router.post("/", response_model=SubmissionResponse, status_code=201)
def submit_code(
    submission: SubmissionCreate,
    db: Session = Depends(get_db)
):
    """
    Submit code for a question and execute it against test cases.
    Returns results including pass/fail status, runtime, and memory usage.
    """
    # Check SQLite guard
    dialect = str(getattr(getattr(engine, "url", None), "drivername", ""))
    if dialect.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify question exists
    question_query = text("""
        SELECT id, optimal_solution FROM public.questions 
        WHERE id = :question_id AND is_active = true
    """)
    question = db.execute(question_query, {"question_id": submission.question_id}).fetchone()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Fetch test cases
    test_cases_query = text("""
        SELECT id, input, expected_output, is_sample, is_hidden
        FROM public.test_cases
        WHERE question_id = :question_id
        ORDER BY order_index ASC
    """)
    test_cases = db.execute(test_cases_query, {"question_id": submission.question_id}).fetchall()
    
    if not test_cases:
        raise HTTPException(status_code=400, detail="No test cases found for this question")
    
    # Execute code against all test cases
    test_results = []
    passed_count = 0
    total_runtime = 0
    total_memory = 0
    overall_status = "accepted"
    error_message = None
    
    for tc in test_cases:
        tc_id, tc_input, tc_expected, tc_is_sample, tc_is_hidden = tc
        
        # Execute code
        exec_result = execute_python_code(submission.code, tc_input)
        
        if exec_result["success"]:
            # Compare output
            passed = compare_outputs(exec_result["output"], tc_expected)
            
            if passed:
                passed_count += 1
            else:
                overall_status = "wrong_answer"
            
            test_results.append({
                "test_case_id": str(tc_id),
                "passed": passed,
                "input": tc_input,
                "expected_output": tc_expected,
                "actual_output": exec_result["output"],
                "error_message": None,
                "is_sample": tc_is_sample
            })
            
            total_runtime += exec_result["runtime_ms"]
            total_memory += exec_result["memory_kb"]
        else:
            # Runtime error
            overall_status = "runtime_error"
            error_message = exec_result["error"]
            
            test_results.append({
                "test_case_id": str(tc_id),
                "passed": False,
                "input": tc_input,
                "expected_output": tc_expected,
                "actual_output": None,
                "error_message": exec_result["error"],
                "is_sample": tc_is_sample
            })
            break  # Stop on first error
    
    # Calculate average runtime and memory
    avg_runtime = total_runtime // len(test_results) if test_results else 0
    avg_memory = total_memory // len(test_results) if test_results else 0
    
    # Insert submission into database
    insert_query = text("""
        INSERT INTO public.submissions (
            question_id, user_id, code, language, status,
            test_cases_passed, total_test_cases,
            runtime_ms, memory_kb, error_message, submitted_at
        )
        VALUES (
            :question_id, :user_id, :code, :language, :status,
            :test_cases_passed, :total_test_cases,
            :runtime_ms, :memory_kb, :error_message, NOW()
        )
        RETURNING id, submitted_at
    """)
    
    result = db.execute(insert_query, {
        "question_id": submission.question_id,
        "user_id": submission.user_id,
        "code": submission.code,
        "language": submission.language,
        "status": overall_status,
        "test_cases_passed": passed_count,
        "total_test_cases": len(test_cases),
        "runtime_ms": avg_runtime,
        "memory_kb": avg_memory,
        "error_message": error_message
    }).fetchone()
    
    db.commit()
    
    submission_id = str(result[0])
    submitted_at = result[1].isoformat()
    
    # Update user_question_progress
    if overall_status == "accepted":
        # Update progress to solved
        progress_query = text("""
            INSERT INTO public.user_question_progress (
                user_id, question_id, status, attempts,
                best_runtime_ms, best_memory_kb,
                first_attempted_at, solved_at, last_attempted_at
            )
            VALUES (
                :user_id, :question_id, 'solved', 1,
                :runtime_ms, :memory_kb,
                NOW(), NOW(), NOW()
            )
            ON CONFLICT (user_id, question_id)
            DO UPDATE SET
                status = 'solved',
                attempts = user_question_progress.attempts + 1,
                best_runtime_ms = LEAST(user_question_progress.best_runtime_ms, :runtime_ms),
                best_memory_kb = LEAST(user_question_progress.best_memory_kb, :memory_kb),
                solved_at = COALESCE(user_question_progress.solved_at, NOW()),
                last_attempted_at = NOW()
        """)
    else:
        # Update progress to attempted
        progress_query = text("""
            INSERT INTO public.user_question_progress (
                user_id, question_id, status, attempts,
                first_attempted_at, last_attempted_at
            )
            VALUES (
                :user_id, :question_id, 'attempted', 1,
                NOW(), NOW()
            )
            ON CONFLICT (user_id, question_id)
            DO UPDATE SET
                attempts = user_question_progress.attempts + 1,
                last_attempted_at = NOW()
        """)
    
    db.execute(progress_query, {
        "user_id": submission.user_id,
        "question_id": submission.question_id,
        "runtime_ms": avg_runtime,
        "memory_kb": avg_memory
    })
    db.commit()
    
    return {
        "id": submission_id,
        "question_id": submission.question_id,
        "user_id": submission.user_id,
        "status": overall_status,
        "test_cases_passed": passed_count,
        "total_test_cases": len(test_cases),
        "runtime_ms": avg_runtime,
        "memory_kb": avg_memory,
        "test_results": test_results,
        "error_message": error_message,
        "submitted_at": submitted_at
    }