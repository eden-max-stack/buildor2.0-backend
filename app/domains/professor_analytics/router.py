from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.infrastructure.supabase_client import supabase

router = APIRouter(prefix="/classes/{class_id}/reports", tags=["Reports"])

# ... (Assume standard Pydantic models for the response) ...
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.infrastructure.supabase_client import supabase

# Make sure this matches how you include routers in your main app
router = APIRouter(prefix="/classes/{class_id}/reports", tags=["Reports"])
@router.get("/{student_id}")
def get_student_report(class_id: str, student_id: str):
    try:
        # 1. Fetch Category Skills
        skills_res = supabase.table("student_category_skills") \
            .select("tag_name, skill_level, total_solved, score") \
            .eq("user_id", student_id) \
            .execute()
        
        # Ensure skills is at least an empty list if no data
        skills_data = skills_res.data if skills_res.data else []

        # 2. Fetch Questions belonging to this class via Phases
        class_question_ids = []
        try:
             # Step A: Get all phases for this class
             phases_res = supabase.table("class_phases") \
                .select("phase_id") \
                .eq("class_id", class_id) \
                .execute()
                
             phase_ids = [p["phase_id"] for p in phases_res.data] if phases_res.data else []

             # Step B: Get all materials linked to those phases
             if phase_ids:
                 materials_res = supabase.table("materials") \
                    .select("question_id") \
                    .in_("phase_id", phase_ids) \
                    .not_.is_("question_id", "null") \
                    .execute()
                    
                 class_question_ids = [m["question_id"] for m in materials_res.data if m.get("question_id")]
                 
        except Exception as material_err:
             print(f"Error fetching materials via phases: {material_err}")

        
        submissions_data = []
        telemetry_data = []

        # Only fetch submissions and telemetry if there are questions in the class
        if class_question_ids:
            # 3. Fetch Submissions & Feedback
            subs_res = supabase.table("submissions") \
                .select("submission_id, status, runtime_ms, memory_kb, submitted_at, question_id, questions(title, tags), submission_feedback(content, created_at)") \
                .eq("user_id", student_id) \
                .in_("question_id", class_question_ids) \
                .order("submitted_at", desc=True) \
                .execute()
            submissions_data = subs_res.data if subs_res.data else []

            # 4. Fetch Hint Telemetry
            telemetry_res = supabase.table("student_question_telemetry") \
                .select("question_id, hints_used, is_solved") \
                .eq("user_id", student_id) \
                .in_("question_id", class_question_ids) \
                .execute()
            telemetry_data = telemetry_res.data if telemetry_res.data else []

        return {
            "skills": skills_data,
            "submissions": submissions_data,
            "telemetry": telemetry_data
        }

    except Exception as e:
        print(f"CRITICAL Report generation error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))