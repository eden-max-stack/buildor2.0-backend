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
from app.infrastructure.supabase_client import supabase

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


@router.post("/", status_code=201)
def submit_code(submission: SubmissionCreate): 
    """
    Submit code for a question and execute it against test cases.
    """
    try:
        # 1. Verify question exists
        q_res = supabase.table("questions").select("question_id").eq("question_id", submission.question_id).execute()
        if not q_res.data:
            raise HTTPException(status_code=404, detail="Question not found")

        # 2. Verify user exists
        u_res = supabase.table("users").select("user_id").eq("user_id", submission.user_id).execute()
        if not u_res.data:
            raise HTTPException(status_code=400, detail="Invalid user_id")
        
        # 3. Fetch test cases 
        tc_res = supabase.table("test_cases").select("tc_id, input, expected_output, is_sample").eq("question_id", submission.question_id).execute()
        test_cases = tc_res.data
        
        if not test_cases:
            raise HTTPException(status_code=400, detail="No test cases found for this question")
        
        # 4. Execute code against all test cases
        test_results = []
        passed_count = 0
        total_runtime = 0
        total_memory = 0
        overall_status = "accepted"
        error_message = None
        
        for tc in test_cases:
            tc_id = tc["tc_id"]
            tc_input = tc["input"] 
            tc_expected = tc["expected_output"]
            tc_is_sample = tc["is_sample"]
            
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
        
        # 5. Insert submission into database 
        sub_res = supabase.table("submissions").insert({
            "question_id": submission.question_id,
            "user_id": submission.user_id,
            "submitted_code": submission.code,
            # THE FIX: Add .upper() so it matches your Postgres ENUM!
            "status": overall_status.upper(), 
            "runtime_ms": avg_runtime,
            "memory_kb": avg_memory
        }).execute()
        
        sub_data = sub_res.data[0]
        
        return {
            "id": sub_data["submission_id"],
            "question_id": submission.question_id,
            "user_id": submission.user_id,
            "status": overall_status,
            "test_cases_passed": passed_count,
            "total_test_cases": len(test_cases),
            "runtime_ms": avg_runtime,
            "memory_kb": avg_memory,
            "test_results": test_results,
            "error_message": error_message,
            "submitted_at": sub_data["submitted_at"]
        }

    except Exception as e:
        # This will print the EXACT Supabase error dictionary to your terminal
        print(f"Failed to execute submission: {repr(e)}") 
        raise HTTPException(status_code=500, detail=str(e))