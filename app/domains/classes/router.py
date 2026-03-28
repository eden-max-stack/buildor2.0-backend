import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.domains.profiles.models import get_current_user # Adjust import path
from app.domains.classes.models import ClassCreatePayload, ClassResponse # Adjust import path
from app.infrastructure.supabase_client import supabase

router = APIRouter(prefix="/api/classes", tags=["Classes"])

@router.post("/")
async def create_new_class(payload: ClassCreatePayload, current_user = Depends(get_current_user)):
    trainer_id = current_user.id

    try:
        # 1. Fetch the org_id for this trainer from the users table
        user_res = supabase.table("users").select("org_id").eq("user_id", trainer_id).execute()
        if not user_res.data:
            raise ValueError("User record not found to fetch org_id")
        org_id = user_res.data[0]["org_id"]

        # 2. Insert the Class
        class_res = supabase.table("classes").insert({
            "org_id": org_id,
            "trainer_id": trainer_id,
            "title": payload.title,
            "description": payload.description
        }).execute()
        class_id = class_res.data[0]["class_id"]

        # 3. Loop through Phases
        for phase in payload.phases:
            phase_res = supabase.table("class_phases").insert({
                "class_id": class_id,
                "title": phase.title,
                "description": phase.description,
                "order_index": phase.order_index
            }).execute()
            phase_id = phase_res.data[0]["phase_id"]

            # 4a. Insert Standard Materials (Videos/Articles)
            for mat in phase.materials:
                supabase.table("materials").insert({
                    "phase_id": phase_id,
                    "type": mat.type,
                    "title": mat.title,
                    "content_url": mat.content_url,
                    "order_index": mat.order_index
                }).execute()

            # 4b. Insert Questions & Link them as Materials
            for q_idx, q in enumerate(phase.questions):
                # Convert comma-separated tags string to a list for Postgres array
                tags_list = [tag.strip() for tag in q.tags.split(",")] if q.tags else []

                # --- NEW: Map the frontend string to your exact Postgres ENUM ---
                db_question_type = "MCQ" if q.type == "MCQ_QUESTION" else "DSA"

                question_res = supabase.table("questions").insert({
                    "trainer_id": trainer_id,
                    "type": db_question_type, # <-- "MCQ" or "DSA" goes here
                    "title": q.title,
                    "description": q.description,
                    "difficulty": q.difficulty,
                    "tags": tags_list,
                    "optimal_solution": q.optimalSolution,
                    "constraints": q.constraints
                }).execute()
                question_id = question_res.data[0]["question_id"]

                # Insert DSA Test Cases
                if q.type == "DSA_QUESTION" and q.testCases:
                    for tc in q.testCases:
                        try:
                            parsed_input = json.loads(tc.input)
                            parsed_output = json.loads(tc.expectedOutput)
                        except:
                            parsed_input = {"raw": tc.input}
                            parsed_output = {"raw": tc.expectedOutput}

                        supabase.table("test_cases").insert({
                            "question_id": question_id,
                            "input": parsed_input,
                            "expected_output": parsed_output,
                            "is_sample": tc.isSample
                        }).execute()

                # Insert MCQ Options
                if q.type == "MCQ_QUESTION" and q.options:
                    for opt in q.options:
                        supabase.table("mcq_options").insert({
                            "question_id": question_id,
                            "option_text": opt.text,
                            "is_correct": opt.isCorrect
                        }).execute()

                # Finally, link this Question to the Phase via the materials table!
                # NOTE: If materials.type also uses an ENUM, you may need to map it here as well.
                supabase.table("materials").insert({
                    "phase_id": phase_id,
                    "type": "QUESTION", # <-- EXACT MATCH to your material_type ENUM!
                    "title": q.title,
                    "question_id": question_id,
                    "order_index": len(phase.materials) + q_idx + 1 
                }).execute()
        return {"message": "Class created successfully!", "class_id": class_id}

    except Exception as e:
        print(f"Failed to create class sequence: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/{class_id}")
async def delete_class(class_id: str, current_user = Depends(get_current_user)):
    trainer_id = current_user.id

    try:
        # 1. Verify Ownership (Security Check)
        class_res = supabase.table("classes").select("trainer_id").eq("class_id", class_id).execute()
        
        if not class_res.data:
            raise HTTPException(status_code=404, detail="Class not found")
            
        if class_res.data[0]["trainer_id"] != trainer_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this class")

        # 2. Get all Phase IDs for this class
        phases_res = supabase.table("class_phases").select("phase_id").eq("class_id", class_id).execute()
        phase_ids = [p["phase_id"] for p in phases_res.data]

        question_ids = []
        if phase_ids:
            # 3. Get all Question IDs linked to these phases
            materials_res = supabase.table("materials").select("question_id").in_("phase_id", phase_ids).execute()
            
            # Extract valid question_ids (ignoring standard materials like VIDEO/ARTICLE which have null question_ids)
            question_ids = list(set([m["question_id"] for m in materials_res.data if m.get("question_id") is not None]))

        # 4. Explicitly delete Test Cases and MCQ Options to avoid Foreign Key constraint blocks
        if question_ids:
            supabase.table("test_cases").delete().in_("question_id", question_ids).execute()
            supabase.table("mcq_options").delete().in_("question_id", question_ids).execute()

        # 5. Delete the Class
        # Because of ON DELETE CASCADE, this automatically deletes all rows in `class_phases` and `materials`
        supabase.table("classes").delete().eq("class_id", class_id).execute()

        # 6. Delete the orphaned Questions
        # Now that the materials are gone, we can safely delete the questions themselves
        if question_ids:
            supabase.table("questions").delete().in_("question_id", question_ids).execute()

        return {"message": "Class and all associated materials, questions, and test cases deleted successfully"}

    except HTTPException:
        # Re-raise known HTTP exceptions (like 404 or 403)
        raise
    except Exception as e:
        print(f"Failed to delete class: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while deleting the class")
    

@router.get("/")
async def get_all_classes(current_user = Depends(get_current_user)) -> List[ClassResponse]:
    trainer_id = current_user.id

    try:
        classes = supabase.table("classes").select("*").eq("trainer_id", trainer_id).execute()

        if not classes.data:
            raise HTTPException(status_code=404, detail="Classes not found")
            
        if classes.data[0]["trainer_id"] != trainer_id:
            raise HTTPException(status_code=403, detail="Not authorized to get details on this class")

        classes_data = []
        for cl in classes.data:
            classes_data.append({
                "title": cl.get("title", "Class title"),
                "description": cl.get("description", "Class description"),
                "org_id": cl.get("org_id", "org iD"),
                "created_at": cl.get("created_at", "clreated at"),
                "trainer_id": cl.get("trainer_id", "trainer ID"),
                "class_id": cl.get("class_id", "CLASS iD"),
                "phases_count": 3, 
                "students_count": 7,
            })
        return classes_data
    
    except Exception as e:  
        print(f"Error fetching classes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching classes data"
        )
        

