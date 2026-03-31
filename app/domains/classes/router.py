import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.domains.profiles.models import get_current_user # Adjust import path
from app.domains.classes.models import ClassCreatePayload, ClassResponse, ClassUpdatePayload, MaterialAddPayload, MaterialUpdatePayload, PhaseUpdatePayload, QuestionUpdatePayload, QuizCreatePayload, QuizQuestionAddPayload, QuizQuestionsUpdatePayload # Adjust import path
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
        
@router.get("/browse")
async def browse_all_classes(current_user = Depends(get_current_user)) -> List[ClassResponse]:
    try:
        # Fetch ALL classes from the table, no .eq() filter needed
        res = supabase.table("classes").select("*").execute()

        if not res.data:
            # For a browse route, returning an empty list is often better than a 404
            return []

        classes_data = []
        for cl in res.data:
            # Note: We can include the trainer's name if you link the 'profiles' table later
            classes_data.append({
                "title": cl.get("title", "Unnamed Class"),
                "description": cl.get("description", ""),
                "org_id": cl.get("org_id"),
                "created_at": cl.get("created_at"),
                "trainer_id": cl.get("trainer_id"),
                "class_id": cl.get("class_id"),
                # You might want to calculate these dynamically in the future
                "phases_count": 0, 
                "students_count": 0,
            })
            
        return classes_data

    except Exception as e:
        print(f"Error browsing classes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching the class catalog"
        )

# --- 1. Fetch the Entire Class Tree for the Editor ---
@router.get("/{class_id}/editor")
async def get_class_for_editor(class_id: str, current_user = Depends(get_current_user)):
    try:
        # We extend the nested syntax to include test_cases and mcq_options under questions
        res = supabase.table("classes").select("""
            *,
            class_phases (
                *, 
                materials (
                    *, 
                    questions (
                        *, 
                        test_cases(*), 
                        mcq_options(*)
                    )
                )
            ),
            quizzes (
                *, 
                quiz_questions (
                    *, 
                    questions (
                        *, 
                        test_cases(*), 
                        mcq_options(*)
                    )
                )
            )
        """).eq("class_id", class_id).eq("trainer_id", current_user.id).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Class not found or unauthorized")

        class_data = res.data[0]
        
        # Sort phases and materials by order_index so they appear correctly in the UI
        if "class_phases" in class_data:
            class_data["class_phases"].sort(key=lambda x: x.get("order_index", 0))
            for phase in class_data["class_phases"]:
                if "materials" in phase:
                    phase["materials"].sort(key=lambda x: x.get("order_index", 0))

        return class_data

    except Exception as e:
        print(f"Error fetching class editor data: {e}")
        raise HTTPException(status_code=500, detail="Failed to load class editor")

# --- 2. Update a Single Material (Fast & Lightweight) ---
@router.put("/materials/{material_id}")
async def update_material(material_id: str, payload: MaterialUpdatePayload, current_user = Depends(get_current_user)):
    try:
        # Update only the fields that were provided
        update_data = payload.model_dump(exclude_unset=True)
        res = supabase.table("materials").update(update_data).eq("material_id", material_id).execute()
        return {"message": "Material updated", "data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update material")


# 2. The PUT Route
@router.put("/phases/{phase_id}")
async def update_phase(
    phase_id: str, 
    payload: PhaseUpdatePayload, 
    current_user = Depends(get_current_user)
):
    try:
        # exclude_unset=True ensures we only update fields the frontend actually sent
        update_data = payload.model_dump(exclude_unset=True)
        
        if not update_data:
            return {"message": "Nothing to update"}

        res = supabase.table("class_phases") \
            .update(update_data) \
            .eq("phase_id", phase_id) \
            .execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Phase not found")
            
        return {"message": "Phase updated successfully!", "phase": res.data[0]}

    except Exception as e:
        print(f"Error updating phase: {e}")
        raise HTTPException(status_code=500, detail="Failed to update phase")
        

@router.post("/phases/{phase_id}/materials")
async def add_material_to_phase(
    phase_id: str, 
    payload: MaterialAddPayload, 
    current_user = Depends(get_current_user)
):
    try:
        question_id = None
        
        # If the material is a question, create a stub in the questions table first
        if payload.type == "QUESTION":
            q_res = supabase.table("questions").insert({
                "trainer_id": current_user.id,
                "type": "MCQ", # Default stub, user will edit it later via the modal
                "title": payload.title,
                "difficulty": "Medium"
            }).execute()
            question_id = q_res.data[0]["question_id"]

        # Insert the material
        mat_res = supabase.table("materials").insert({
            "phase_id": phase_id,
            "type": payload.type, 
            "title": payload.title,
            "content_url": payload.content_url,
            "order_index": payload.order_index,
            "question_id": question_id
        }).execute()

        return mat_res.data[0]

    except Exception as e:
        print(f"Error adding material: {e}")
        raise HTTPException(status_code=500, detail="Failed to add material")
    
@router.put("/questions/{question_id}")
async def update_question(
    question_id: str, 
    payload: QuestionUpdatePayload, 
    current_user = Depends(get_current_user)
):
    try:
        # 1. Update the core question details
        db_question_type = "MCQ" if "MCQ" in payload.type else "DSA"
        
        supabase.table("questions").update({
            "title": payload.title,
            "description": payload.description,
            "difficulty": payload.difficulty,
            "optimal_solution": payload.optimal_solution,
            "constraints": payload.constraints,
            "type": db_question_type
        }).eq("question_id", question_id).execute()

        if payload.points is not None:
            # Update points in quiz_questions if this question is linked to any quizzes
            supabase.table("quiz_questions").update({
                "points": payload.points
            }).eq("question_id", question_id).execute()

        # 2. Overwrite MCQ Options
        if db_question_type == "MCQ" and payload.options:
            # Wipe existing options
            supabase.table("mcq_options").delete().eq("question_id", question_id).execute()
            # Insert new options
            opt_data = [
                {"question_id": question_id, "option_text": o.text, "is_correct": o.isCorrect} 
                for o in payload.options
            ]
            supabase.table("mcq_options").insert(opt_data).execute()

        # 3. Overwrite DSA Test Cases
        if db_question_type == "DSA" and payload.testCases:
            # Wipe existing test cases
            supabase.table("test_cases").delete().eq("question_id", question_id).execute()
            tc_data = []
            for tc in payload.testCases:
                try:
                    parsed_input = json.loads(tc.input)
                    parsed_output = json.loads(tc.expectedOutput)
                except:
                    parsed_input = {"raw": tc.input}
                    parsed_output = {"raw": tc.expectedOutput}
                
                tc_data.append({
                    "question_id": question_id,
                    "input": parsed_input,
                    "expected_output": parsed_output,
                    "is_sample": tc.isSample
                })
            supabase.table("test_cases").insert(tc_data).execute()

        return {"message": "Question updated successfully"}

    except Exception as e:
        print(f"Error updating question: {e}")
        raise HTTPException(status_code=500, detail="Failed to update question")
    
@router.put("/{class_id}")
async def update_class_settings(
    class_id: str, 
    payload: ClassUpdatePayload, 
    current_user = Depends(get_current_user)
):
    try:
        # We verify trainer_id to ensure only the owner can edit settings
        res = supabase.table("classes").update({
            "title": payload.title,
            "description": payload.description
        }).eq("class_id", class_id).eq("trainer_id", current_user.id).execute()
        
        if not res.data:
             raise HTTPException(status_code=403, detail="Not authorized to edit this class")

        return {"message": "Class settings updated"}
    except Exception as e:
        print(f"Error updating class settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update class settings")


# Assuming QuestionUpdatePayload is already defined from the previous step
@router.post("/quizzes/{quiz_id}/questions")
async def add_full_question_to_quiz(
    quiz_id: str, 
    payload: QuestionUpdatePayload, 
    current_user = Depends(get_current_user)
):
    try:
        db_question_type = "MCQ" if "MCQ" in payload.type else "DSA"

        # 1. Insert the Question
        q_res = supabase.table("questions").insert({
            "trainer_id": current_user.id,
            "type": db_question_type,
            "title": payload.title,
            "description": payload.description,
            "difficulty": payload.difficulty,
            "optimal_solution": payload.optimal_solution,
            "constraints": payload.constraints
        }).execute()
        
        question_data = q_res.data[0]
        question_id = question_data["question_id"]

        # 2. Insert Options if MCQ
        if db_question_type == "MCQ" and payload.options:
            opt_data = [
                {"question_id": question_id, "option_text": o.text, "is_correct": o.isCorrect} 
                for o in payload.options
            ]
            supabase.table("mcq_options").insert(opt_data).execute()
            question_data["mcq_options"] = opt_data # Attach to response

        # 3. Insert Test Cases if DSA
        if db_question_type == "DSA" and payload.testCases:
            tc_data = []
            for tc in payload.testCases:
                try:
                    parsed_input = json.loads(tc.input)
                    parsed_output = json.loads(tc.expectedOutput)
                except:
                    parsed_input = {"raw": tc.input}
                    parsed_output = {"raw": tc.expectedOutput}
                
                tc_data.append({
                    "question_id": question_id,
                    "input": parsed_input,
                    "expected_output": parsed_output,
                    "is_sample": tc.isSample
                })
            supabase.table("test_cases").insert(tc_data).execute()
            question_data["test_cases"] = tc_data # Attach to response

        # 4. Link the new question directly to the Quiz
        supabase.table("quiz_questions").insert({
            "quiz_id": quiz_id,
            "question_id": question_id,
            "points": getattr(payload, 'points', 10)
        }).execute()

        # Return the newly created question so the UI can render it immediately
        return {"message": "Question created and added to quiz", "question": question_data}

    except Exception as e:
        print(f"Error creating full quiz question: {e}")
        raise HTTPException(status_code=500, detail="Failed to create question for quiz")
    

@router.post("/{class_id}/quizzes")
async def create_quiz(class_id: str, payload: QuizCreatePayload, current_user = Depends(get_current_user)):
    try:
        quiz_res = supabase.table("quizzes").insert({
            "class_id": class_id,
            "title": payload.title
        }).execute()
        return {"message": "Quiz created", "quiz_id": quiz_res.data[0]["quiz_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create quiz")
    
@router.post("/quizzes/{quiz_id}/questions")
async def add_question_to_quiz(quiz_id: str, payload: QuizQuestionAddPayload, current_user = Depends(get_current_user)):
    try:
        # 1. Create the new standalone question
        q_res = supabase.table("questions").insert({
            "trainer_id": current_user.id,
            "type": payload.type,
            "title": payload.title,
            "difficulty": "Medium"
        }).execute()
        question_data = q_res.data[0]

        # 2. Link it to the Quiz
        supabase.table("quiz_questions").insert({
            "quiz_id": quiz_id,
            "question_id": question_data["question_id"],
            "points": 10
        }).execute()

        # Return the joined data so the frontend can immediately edit it
        return {"message": "Question added", "question": question_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to add question to quiz")