import truststore # type: ignore
truststore.inject_into_ssl()

import json
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
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
        
# ============================================================
# STUDENT / DASHBOARD ENDPOINTS
# ============================================================

@router.get("/my-classes")
async def get_my_classes(current_user = Depends(get_current_user)):
    """Get all classes the current user is enrolled in (student) or owns (trainer)."""
    user_id = current_user.id
    try:
        # 1. Classes where user is trainer
        trainer_res = supabase.table("classes").select(
            "class_id, title, description, created_at, org_id, trainer_id"
        ).eq("trainer_id", user_id).execute()

        # 2. Classes where user is enrolled as student
        enrollment_res = supabase.table("class_enrollments").select(
            "class_id, enrolled_at, classes(class_id, title, description, created_at, org_id, trainer_id)"
        ).eq("user_id", user_id).execute()

        classes_map = {}

        # Add trainer classes
        for cl in (trainer_res.data or []):
            classes_map[cl["class_id"]] = {
                **cl,
                "role": "trainer",
            }

        # Add enrolled classes
        for enrollment in (enrollment_res.data or []):
            cl = enrollment.get("classes")
            if cl and cl["class_id"] not in classes_map:
                classes_map[cl["class_id"]] = {
                    **cl,
                    "role": "student",
                    "enrolled_at": enrollment.get("enrolled_at"),
                }

        # 3. For each class, get phases_count and students_count
        result = []
        for cid, cl in classes_map.items():
            phases_res = supabase.table("class_phases").select("phase_id", count="exact").eq("class_id", cid).execute()
            students_res = supabase.table("class_enrollments").select("user_id", count="exact").eq("class_id", cid).execute()
            cl["phases_count"] = phases_res.count if phases_res.count is not None else 0
            cl["students_count"] = students_res.count if students_res.count is not None else 0
            result.append(cl)

        return result

    except Exception as e:
        print(f"Error fetching my classes: {e}")
        raise HTTPException(status_code=500, detail="Error fetching user classes")


@router.get("/my-goals")
async def get_my_goals(limit: int = Query(5, ge=1, le=20), current_user = Depends(get_current_user)):
    """Get top N learning plan goals by target_date for the current user."""
    user_id = current_user.id
    try:
        res = supabase.table("learning_plan_goals").select(
            "goal_id, title, target_date, class_id, classes(title)"
        ).eq("user_id", user_id).order("target_date", desc=False).limit(limit).execute()

        goals = []
        for g in (res.data or []):
            # Check completion status via goal_items
            items_res = supabase.table("goal_items").select(
                "material_id, is_completed"
            ).eq("goal_id", g["goal_id"]).execute()

            total = len(items_res.data) if items_res.data else 0
            completed = sum(1 for i in (items_res.data or []) if i.get("is_completed"))

            goals.append({
                "goal_id": g["goal_id"],
                "title": g["title"],
                "target_date": g["target_date"],
                "class_id": g["class_id"],
                "class_title": g["classes"]["title"] if g.get("classes") else None,
                "total_items": total,
                "completed_items": completed,
            })

        return goals

    except Exception as e:
        print(f"Error fetching goals: {e}")
        raise HTTPException(status_code=500, detail="Error fetching learning goals")


@router.get("/my-submissions/recent")
async def get_my_recent_submissions(limit: int = Query(3, ge=1, le=10), current_user = Depends(get_current_user)):
    """Get the N most recent submissions for the current user, with question info."""
    user_id = current_user.id
    try:
        res = supabase.table("submissions").select(
            "submission_id, status, submitted_at, runtime_ms, memory_kb, "
            "questions(question_id, title, difficulty, tags)"
        ).eq("user_id", user_id).order("submitted_at", desc=True).limit(limit).execute()

        submissions = []
        for s in (res.data or []):
            q = s.get("questions") or {}
            submissions.append({
                "submission_id": s["submission_id"],
                "status": s["status"],
                "submitted_at": s["submitted_at"],
                "runtime_ms": s.get("runtime_ms"),
                "memory_kb": s.get("memory_kb"),
                "question_id": q.get("question_id"),
                "question_title": q.get("title"),
                "difficulty": q.get("difficulty"),
                "tags": q.get("tags", []),
            })

        return submissions

    except Exception as e:
        print(f"Error fetching recent submissions: {e}")
        raise HTTPException(status_code=500, detail="Error fetching recent submissions")


@router.get("/browse")
async def browse_all_classes(current_user = Depends(get_current_user)):
    """Browse all available classes with real counts and trainer name."""
    try:
        res = supabase.table("classes").select(
            "class_id, title, description, created_at, org_id, trainer_id, "
            "trainer_profiles!classes_trainer_id_fkey(title, workplace)"
        ).execute()

        if not res.data:
            return []

        classes_data = []
        for cl in res.data:
            cid = cl["class_id"]
            phases_res = supabase.table("class_phases").select("phase_id", count="exact").eq("class_id", cid).execute()
            students_res = supabase.table("class_enrollments").select("user_id", count="exact").eq("class_id", cid).execute()
            # Fetch real trainer name from users table
            trainer_id = cl.get("trainer_id")
            trainer_name = "Unknown"
            if trainer_id:
                user_res = supabase.table("users").select("full_name").eq("user_id", trainer_id).execute()
                if user_res.data:
                    trainer_name = user_res.data[0].get("full_name", "Unknown")
            classes_data.append({
                "title": cl.get("title", "Unnamed Class"),
                "description": cl.get("description", ""),
                "org_id": cl.get("org_id"),
                "created_at": cl.get("created_at"),
                "trainer_id": trainer_id,
                "class_id": cid,
                "trainer_name": trainer_name,
                "phases_count": phases_res.count if phases_res.count is not None else 0,
                "students_count": students_res.count if students_res.count is not None else 0,
            })

        return classes_data

    except Exception as e:
        print(f"Error browsing classes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching the class catalog"
        )


@router.get("/{class_id}/detail")
async def get_class_detail(class_id: str, current_user = Depends(get_current_user)):
    """Get full class info including trainer name and student count."""
    try:
        res = supabase.table("classes").select(
            "class_id, title, description, created_at, org_id, trainer_id, "
            "trainer_profiles!classes_trainer_id_fkey(title, workplace)"
        ).eq("class_id", class_id).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Class not found")

        cl = res.data[0]
        students_res = supabase.table("class_enrollments").select("user_id", count="exact").eq("class_id", class_id).execute()

        # Fetch real trainer name from users table
        trainer_id = cl.get("trainer_id")
        trainer_name = "Unknown"
        if trainer_id:
            user_res = supabase.table("users").select("full_name").eq("user_id", trainer_id).execute()
            if user_res.data:
                trainer_name = user_res.data[0].get("full_name", "Unknown")
        return {
            "class_id": cl["class_id"],
            "title": cl["title"],
            "description": cl["description"],
            "created_at": cl["created_at"],
            "org_id": cl["org_id"],
            "trainer_id": cl["trainer_id"],
            "trainer_name": trainer_name,
            "students_count": students_res.count if students_res.count is not None else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching class detail: {e}")
        raise HTTPException(status_code=500, detail="Error fetching class detail")


@router.get("/{class_id}/materials")
async def get_class_materials(class_id: str, current_user = Depends(get_current_user)):
    """Get all phases and materials for a class, sorted by order_index."""
    try:
        res = supabase.table("class_phases").select(
            "phase_id, title, description, order_index, "
            "materials(material_id, type, title, content_url, question_id, order_index)"
        ).eq("class_id", class_id).order("order_index", desc=False).execute()

        phases = []
        for phase in (res.data or []):
            materials = phase.get("materials", [])
            materials.sort(key=lambda m: m.get("order_index", 0))
            phases.append({
                "phase_id": phase["phase_id"],
                "title": phase["title"],
                "description": phase.get("description"),
                "order_index": phase["order_index"],
                "materials": materials,
            })

        return phases

    except Exception as e:
        print(f"Error fetching class materials: {e}")
        raise HTTPException(status_code=500, detail="Error fetching class materials")


@router.get("/{class_id}/quizzes")
async def get_class_quizzes(class_id: str, current_user = Depends(get_current_user)):
    """Get all quizzes for a class with their questions."""
    try:
        res = supabase.table("quizzes").select(
            "quiz_id, title, "
            "quiz_questions(question_id, points, questions(question_id, title, type, difficulty, tags))"
        ).eq("class_id", class_id).execute()

        quizzes = []
        for quiz in (res.data or []):
            questions = []
            for qq in (quiz.get("quiz_questions") or []):
                q = qq.get("questions") or {}
                questions.append({
                    "question_id": qq["question_id"],
                    "points": qq.get("points", 10),
                    "title": q.get("title"),
                    "type": q.get("type"),
                    "difficulty": q.get("difficulty"),
                    "tags": q.get("tags", []),
                })
            quizzes.append({
                "quiz_id": quiz["quiz_id"],
                "title": quiz["title"],
                "questions": questions,
            })

        return quizzes

    except Exception as e:
        print(f"Error fetching class quizzes: {e}")
        raise HTTPException(status_code=500, detail="Error fetching class quizzes")


@router.get("/{class_id}/students")
async def get_class_students(class_id: str, current_user = Depends(get_current_user)):
    """Get all students enrolled in a class."""
    try:
        res = supabase.table("class_enrollments").select(
            "user_id, enrolled_at, users(user_id, full_name, email, avatar_url)"
        ).eq("class_id", class_id).execute()

        students = []
        for enrollment in (res.data or []):
            user = enrollment.get("users") or {}
            students.append({
                "user_id": enrollment["user_id"],
                "enrolled_at": enrollment.get("enrolled_at"),
                "full_name": user.get("full_name", "Unknown"),
                "email": user.get("email"),
                "avatar_url": user.get("avatar_url"),
            })

        return students

    except Exception as e:
        print(f"Error fetching class students: {e}")
        raise HTTPException(status_code=500, detail="Error fetching class students")


@router.get("/{class_id}/feedback")
async def get_class_feedback(class_id: str, current_user = Depends(get_current_user)):
    """Get submission feedback for the current user's submissions in this class."""
    user_id = current_user.id
    try:
        # Get user's submissions for questions in this class
        # First get all question_ids in this class (via phases -> materials)
        phases_res = supabase.table("class_phases").select("phase_id").eq("class_id", class_id).execute()
        phase_ids = [p["phase_id"] for p in (phases_res.data or [])]

        if not phase_ids:
            return []

        materials_res = supabase.table("materials").select("question_id").in_("phase_id", phase_ids).execute()
        question_ids = list(set([m["question_id"] for m in (materials_res.data or []) if m.get("question_id")]))

        if not question_ids:
            return []

        # Get user's submissions for these questions
        submissions_res = supabase.table("submissions").select("submission_id").eq(
            "user_id", user_id
        ).in_("question_id", question_ids).execute()
        submission_ids = [s["submission_id"] for s in (submissions_res.data or [])]

        if not submission_ids:
            return []

        # Get feedback for those submissions
        feedback_res = supabase.table("submission_feedback").select(
            "feedback_id, content, created_at, submission_id, "
            "trainer_profiles!submission_feedback_trainer_id_fkey(user_id, title, "
            "users!trainer_profiles_user_id_fkey(full_name))"
        ).in_("submission_id", submission_ids).order("created_at", desc=True).execute()

        feedbacks = []
        for fb in (feedback_res.data or []):
            trainer = fb.get("trainer_profiles") or {}
            trainer_user = trainer.get("users") or {}
            feedbacks.append({
                "feedback_id": fb["feedback_id"],
                "content": fb["content"],
                "created_at": fb["created_at"],
                "submission_id": fb["submission_id"],
                "trainer_name": trainer_user.get("full_name", "Trainer"),
            })

        return feedbacks

    except Exception as e:
        print(f"Error fetching class feedback: {e}")
        raise HTTPException(status_code=500, detail="Error fetching class feedback")


@router.get("/{class_id}/tasks")
async def get_class_tasks(class_id: str, current_user = Depends(get_current_user)):
    """Get tasks assigned to the current user in this class."""
    user_id = current_user.id
    try:
        res = supabase.table("tasks").select(
            "task_id, task_type, reference_id, due_date, status"
        ).eq("class_id", class_id).eq("assigned_to_user_id", user_id).order("due_date", desc=False).execute()

        return res.data or []

    except Exception as e:
        print(f"Error fetching class tasks: {e}")
        raise HTTPException(status_code=500, detail="Error fetching class tasks")


# ============================================================
# QUIZ TAKE / SUBMIT ENDPOINTS
# ============================================================

@router.get("/{class_id}/quiz/{quiz_id}/take")
async def get_quiz_for_taking(class_id: str, quiz_id: str, current_user=Depends(get_current_user)):
    """Return ordered quiz questions with MCQ options for a student to take."""
    try:
        quiz_res = supabase.table("quizzes").select("quiz_id, title").eq("quiz_id", quiz_id).eq("class_id", class_id).execute()
        if not quiz_res.data:
            raise HTTPException(status_code=404, detail="Quiz not found in this class")
        quiz = quiz_res.data[0]

        qq_res = supabase.table("quiz_questions").select(
            "question_id, points, questions(question_id, title, description, type, difficulty, tags, constraints)"
        ).eq("quiz_id", quiz_id).execute()

        questions = []
        for qq in (qq_res.data or []):
            q = qq.get("questions") or {}
            qid = qq["question_id"]
            qtype = q.get("type")
            
            # Fetch MCQ options for MCQ questions
            mcq_options = []
            if qtype == "MCQ":
                mcq_res = supabase.table("mcq_options").select("option_id, option_text").eq("question_id", qid).execute()
                mcq_options = mcq_res.data or []
            
            # Fetch test cases for DSA questions
            test_cases = []
            if qtype != "MCQ":
                tc_res = supabase.table("test_cases").select("tc_id, input, expected_output, is_sample").eq("question_id", qid).execute()
                test_cases = tc_res.data or []
            
            # Parse constraints
            constraints = q.get("constraints")
            if isinstance(constraints, str):
                constraints = [c.strip() for c in constraints.split('\n') if c.strip()]
            elif not isinstance(constraints, list):
                constraints = []
            
            questions.append({
                "question_id": qid,
                "points": qq.get("points", 10),
                "title": q.get("title"),
                "description": q.get("description"),
                "type": qtype,
                "difficulty": q.get("difficulty"),
                "tags": q.get("tags", []),
                "mcq_options": mcq_options,
                "test_cases": test_cases,
                "constraints": constraints,
            })

        return {"quiz_id": quiz["quiz_id"], "title": quiz["title"], "questions": questions}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching quiz for taking: {e}")
        raise HTTPException(status_code=500, detail="Error fetching quiz")


@router.post("/{class_id}/quiz/{quiz_id}/submit")
async def submit_quiz(class_id: str, quiz_id: str, body: dict = Body(...), current_user=Depends(get_current_user)):
    """Submit a full quiz attempt. Body: { "answers": { "<question_id>": "<selected_option_id>", ... } }"""
    user_id = current_user.id
    answers = body.get("answers", {})
    try:
        quiz_res = supabase.table("quizzes").select("quiz_id").eq("quiz_id", quiz_id).eq("class_id", class_id).execute()
        if not quiz_res.data:
            raise HTTPException(status_code=404, detail="Quiz not found in this class")

        qq_res = supabase.table("quiz_questions").select("question_id, points").eq("quiz_id", quiz_id).execute()
        question_ids = [qq["question_id"] for qq in (qq_res.data or [])]
        points_map = {qq["question_id"]: qq.get("points", 10) for qq in (qq_res.data or [])}
        if not question_ids:
            raise HTTPException(status_code=400, detail="Quiz has no questions")

        correct_map = {}
        for qid in question_ids:
            opts_res = supabase.table("mcq_options").select("option_id").eq("question_id", qid).eq("is_correct", True).execute()
            correct_map[qid] = set(o["option_id"] for o in (opts_res.data or []))

        score = 0
        max_score = 0
        results = []
        for qid in question_ids:
            pts = points_map.get(qid, 10)
            max_score += pts
            selected = answers.get(qid)
            is_correct = selected in correct_map.get(qid, set()) if selected else False
            if is_correct:
                score += pts
            results.append({
                "question_id": qid, "selected_option_id": selected,
                "is_correct": is_correct, "points_earned": pts if is_correct else 0, "points_possible": pts,
            })

        supabase.table("quiz_attempts").insert({
            "quiz_id": quiz_id, "user_id": user_id,
            "score": score, "max_score": max_score, "answers": json.dumps(answers),
        }).execute()

        for qid in question_ids:
            selected = answers.get(qid)
            is_correct = selected in correct_map.get(qid, set()) if selected else False
            try:
                supabase.table("submissions").insert({
                    "user_id": user_id, "question_id": qid,
                    "submitted_code": selected or "", "status": "accepted" if is_correct else "wrong_answer",
                }).execute()
            except Exception:
                pass

        return {
            "quiz_id": quiz_id, "score": score, "max_score": max_score,
            "percentage": round((score / max_score) * 100, 1) if max_score > 0 else 0,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error submitting quiz: {e}")
        raise HTTPException(status_code=500, detail="Error submitting quiz")


@router.get("/{class_id}/quiz/{quiz_id}/attempts")
async def get_quiz_attempts(class_id: str, quiz_id: str, current_user=Depends(get_current_user)):
    """Get all quiz attempts for the current user."""
    user_id = current_user.id
    try:
        res = supabase.table("quiz_attempts").select(
            "attempt_id, score, max_score, submitted_at"
        ).eq("quiz_id", quiz_id).eq("user_id", user_id).order("submitted_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"Error fetching quiz attempts: {e}")
        raise HTTPException(status_code=500, detail="Error fetching quiz attempts")

@router.get("/{class_id}/editor")
async def get_class_editor_data(class_id: str, current_user = Depends(get_current_user)):
    """Fetch all class data needed for the Trainer Editor Dashboard."""
    trainer_id = current_user.id
    try:
        # 1. Get Class Details + Verify Ownership
        class_res = supabase.table("classes").select("*").eq("class_id", class_id).execute()
        if not class_res.data:
            raise HTTPException(status_code=404, detail="Class not found")
        
        class_data = class_res.data[0]
        if str(class_data["trainer_id"]) != str(trainer_id):
            raise HTTPException(status_code=403, detail="Not authorized to edit this class")

        # 2. Get Phases and Materials (Deep join to grab question details, test cases, and options)
        phases_res = supabase.table("class_phases").select(
            "phase_id, title, description, order_index, "
            "materials(material_id, type, title, content_url, question_id, order_index, "
            "questions(question_id, title, description, type, difficulty, tags, optimal_solution, constraints, "
            "mcq_options(option_id, option_text, is_correct), "
            "test_cases(tc_id, input, expected_output, is_sample)))"
        ).eq("class_id", class_id).order("order_index").execute()

        # Sort materials properly
        phases = phases_res.data or []
        for phase in phases:
            if phase.get("materials"):
                phase["materials"].sort(key=lambda m: m.get("order_index", 0))

        # 3. Get Quizzes (Deep join for quiz questions)
        quizzes_res = supabase.table("quizzes").select(
            "quiz_id, title, "
            "quiz_questions(question_id, points, "
            "questions(question_id, title, description, type, difficulty, tags, optimal_solution, constraints, "
            "mcq_options(option_id, option_text, is_correct), "
            "test_cases(tc_id, input, expected_output, is_sample)))"
        ).eq("class_id", class_id).execute()
        
        quizzes = quizzes_res.data or []

        return {
            "class_id": class_data["class_id"],
            "title": class_data["title"],
            "description": class_data["description"],
            "class_phases": phases,
            "quizzes": quizzes
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching editor data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching editor data")
    
# ============================================================
# EDITOR SAVE / UPDATE ENDPOINTS
# ============================================================

@router.put("/materials/{material_id}")
async def update_material(
    material_id: str, 
    payload: MaterialUpdatePayload, 
    current_user = Depends(get_current_user)
):
    """Update an existing material (Title and Content URL)."""
    try:
        # Pydantic model_dump handles extracting the fields safely
        update_data = payload.model_dump(exclude_unset=True)
        
        res = supabase.table("materials").update(update_data).eq("material_id", material_id).execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Material not found")
            
        return {"message": "Material updated", "data": res.data[0]}
    except Exception as e:
        print(f"Error updating material: {e}")
        raise HTTPException(status_code=500, detail="Error updating material")


@router.post("/phases/{phase_id}/materials")
async def add_material_to_phase(
    phase_id: str, 
    payload: MaterialAddPayload, 
    current_user = Depends(get_current_user)
):
    """Add a new material (Video/Article) to a specific phase."""
    try:
        insert_data = {
            "phase_id": phase_id,
            "type": payload.type,
            "title": payload.title,
            "content_url": payload.content_url,
            "order_index": payload.order_index
        }
        
        res = supabase.table("materials").insert(insert_data).execute()
        return {"message": "Material added", "data": res.data[0]}
    except Exception as e:
        print(f"Error adding material: {e}")
        raise HTTPException(status_code=500, detail="Error adding material")


@router.put("/phases/{phase_id}")
async def update_phase(
    phase_id: str, 
    payload: PhaseUpdatePayload, 
    current_user = Depends(get_current_user)
):
    """Update an existing phase (e.g., renaming the title)."""
    try:
        update_data = payload.model_dump(exclude_unset=True)
        res = supabase.table("class_phases").update(update_data).eq("phase_id", phase_id).execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Phase not found")
            
        return {"message": "Phase updated", "data": res.data[0]}
    except Exception as e:
        print(f"Error updating phase: {e}")
        raise HTTPException(status_code=500, detail="Error updating phase")


@router.put("/{class_id}")
async def update_class_settings(
    class_id: str, 
    payload: ClassUpdatePayload, 
    current_user = Depends(get_current_user)
):
    """Update class general settings (Title and Description)."""
    trainer_id = current_user.id
    try:
        # Optional: Verify ownership again
        verify = supabase.table("classes").select("trainer_id").eq("class_id", class_id).execute()
        if not verify.data or str(verify.data[0]["trainer_id"]) != str(trainer_id):
            raise HTTPException(status_code=403, detail="Not authorized to edit this class")

        update_data = payload.model_dump(exclude_unset=True)
        res = supabase.table("classes").update(update_data).eq("class_id", class_id).execute()
        
        return {"message": "Class settings updated", "data": res.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating class settings: {e}")
        raise HTTPException(status_code=500, detail="Error updating class settings")
    
# ============================================================
# QUESTION EDITOR ENDPOINTS
# ============================================================

@router.put("/questions/{question_id}")
async def update_question(
    question_id: str, 
    payload: dict = Body(...), 
    current_user = Depends(get_current_user)
):
    """Update an existing question, including its options or test cases."""
    try:
        # 1. Update Core Question Fields
        update_data = {
            "title": payload.get("title"),
            "description": payload.get("description"),
            "difficulty": payload.get("difficulty"),
            "type": payload.get("type"),
            "optimal_solution": payload.get("optimal_solution", ""),
            "constraints": payload.get("constraints", "")
        }
        supabase.table("questions").update(update_data).eq("question_id", question_id).execute()

        # 2. Update Quiz Points (Only if this was edited from inside a Quiz)
        quiz_id = payload.get("quiz_id")
        points = payload.get("points")
        if quiz_id and points is not None:
            supabase.table("quiz_questions").update({"points": points}).eq("quiz_id", quiz_id).eq("question_id", question_id).execute()

        # 3. Handle MCQ Options (Wipe old, insert new for safety)
        if payload.get("type") == "MCQ" and "options" in payload:
            supabase.table("mcq_options").delete().eq("question_id", question_id).execute()
            
            new_options = []
            for opt in payload["options"]:
                new_options.append({
                    "question_id": question_id,
                    "option_text": opt.get("text", ""),
                    "is_correct": opt.get("isCorrect", False)
                })
            if new_options:
                supabase.table("mcq_options").insert(new_options).execute()

        # 4. Handle DSA Test Cases (Wipe old, insert new for safety)
        if payload.get("type") == "DSA" and "testCases" in payload:
            supabase.table("test_cases").delete().eq("question_id", question_id).execute()
            
            new_tcs = []
            for tc in payload["testCases"]:
                # Safely parse the JSON strings from the frontend
                try:
                    parsed_input = json.loads(tc.get("input", "{}"))
                except:
                    parsed_input = {"raw": tc.get("input", "")}
                    
                try:
                    parsed_output = json.loads(tc.get("expectedOutput", "{}"))
                except:
                    parsed_output = {"raw": tc.get("expectedOutput", "")}

                new_tcs.append({
                    "question_id": question_id,
                    "input": parsed_input,
                    "expected_output": parsed_output,
                    "is_sample": tc.get("isSample", False)
                })
            if new_tcs:
                supabase.table("test_cases").insert(new_tcs).execute()

        return {"message": "Question updated successfully"}

    except Exception as e:
        print(f"Error updating question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quizzes/{quiz_id}/questions")
async def add_question_to_quiz(
    quiz_id: str, 
    payload: dict = Body(...), 
    current_user = Depends(get_current_user)
):
    """Create a completely new question and link it directly to a quiz."""
    trainer_id = current_user.id
    try:
        # 1. Create the Question
        question_data = {
            "trainer_id": trainer_id,
            "type": payload.get("type"),
            "title": payload.get("title"),
            "description": payload.get("description"),
            "difficulty": payload.get("difficulty", "Medium"),
            "optimal_solution": payload.get("optimal_solution", ""),
            "constraints": payload.get("constraints", "")
        }
        q_res = supabase.table("questions").insert(question_data).execute()
        question_id = q_res.data[0]["question_id"]

        # 2. Link the question to the Quiz
        points = payload.get("points") or 10
        supabase.table("quiz_questions").insert({
            "quiz_id": quiz_id,
            "question_id": question_id,
            "points": points
        }).execute()

        # 3. Insert MCQ Options
        if payload.get("type") == "MCQ" and payload.get("options"):
            new_options = []
            for opt in payload["options"]:
                new_options.append({
                    "question_id": question_id,
                    "option_text": opt.get("text", ""),
                    "is_correct": opt.get("isCorrect", False)
                })
            if new_options:
                supabase.table("mcq_options").insert(new_options).execute()

        # 4. Insert DSA Test Cases
        if payload.get("type") == "DSA" and payload.get("testCases"):
            new_tcs = []
            for tc in payload["testCases"]:
                try:
                    parsed_input = json.loads(tc.get("input", "{}"))
                except:
                    parsed_input = {"raw": tc.get("input", "")}
                    
                try:
                    parsed_output = json.loads(tc.get("expectedOutput", "{}"))
                except:
                    parsed_output = {"raw": tc.get("expectedOutput", "")}

                new_tcs.append({
                    "question_id": question_id,
                    "input": parsed_input,
                    "expected_output": parsed_output,
                    "is_sample": tc.get("isSample", False)
                })
            if new_tcs:
                supabase.table("test_cases").insert(new_tcs).execute()

        # Return the raw question data so the frontend can append it to the state cleanly
        return {"message": "Question added to quiz", "question": q_res.data[0]}

    except Exception as e:
        print(f"Error adding question to quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/{class_id}/enrollment-status")
async def get_enrollment_status(class_id: str, current_user = Depends(get_current_user)):
    """Check if the current user is enrolled in or teaches the class."""
    user_id = current_user.id
    try:
        # 1. Check if they are the trainer
        class_res = supabase.table("classes").select("trainer_id").eq("class_id", class_id).execute()
        if not class_res.data:
            raise HTTPException(status_code=404, detail="Class not found")
        
        is_trainer = str(class_res.data[0]["trainer_id"]) == str(user_id)

        # 2. Check if they are enrolled as a student
        enroll_res = supabase.table("class_enrollments").select("enrolled_at").eq("class_id", class_id).eq("user_id", user_id).execute()
        
        is_enrolled = len(enroll_res.data) > 0
        enrolled_at = enroll_res.data[0]["enrolled_at"] if is_enrolled else None

        return {
            "is_trainer": is_trainer,
            "is_enrolled": is_enrolled,
            "enrolled_at": enrolled_at
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error checking enrollment: {e}")
        raise HTTPException(status_code=500, detail="Error checking enrollment status")
    
@router.post("/{class_id}/enroll")
async def enroll_in_class(class_id: str, current_user = Depends(get_current_user)):
    """Enroll a student in a class."""
    user_id = current_user.id
    try:
        # 1. Verify class exists and check the trainer
        class_res = supabase.table("classes").select("trainer_id").eq("class_id", class_id).execute()
        if not class_res.data:
            raise HTTPException(status_code=404, detail="Class not found")
        
        # Prevent trainers from enrolling in their own classes
        if str(class_res.data[0]["trainer_id"]) == str(user_id):
            raise HTTPException(status_code=400, detail="You are the trainer for this class and do not need to enroll.")

        # 2. Check if the user is already enrolled
        enroll_res = supabase.table("class_enrollments").select("enrolled_at").eq("class_id", class_id).eq("user_id", user_id).execute()
        if len(enroll_res.data) > 0:
            return {"message": "You are already enrolled in this class.", "status": "already_enrolled"}

        # 3. Insert the enrollment record
        supabase.table("class_enrollments").insert({
            "class_id": class_id,
            "user_id": user_id
        }).execute()

        return {"message": "Successfully enrolled in the class!", "status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error enrolling in class: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while trying to enroll.")
    
@router.get("/materials/{material_id}/view")
async def get_material_view(material_id: str, current_user = Depends(get_current_user)):
    """Fetch data for the Material Viewer page (Video/Article/Question)"""
    try:
        # 1. Fetch material + phase info + question info
        mat_res = supabase.table("materials").select(
            "*, class_phases(class_id, classes(title, trainer_id)), questions(difficulty, tags)"
        ).eq("material_id", material_id).execute()

        if not mat_res.data:
            raise HTTPException(status_code=404, detail="Material not found")
        
        mat = mat_res.data[0]

        # 2. Extract nested class info
        phase = mat.get("class_phases") or {}
        cls = phase.get("classes") or {}
        trainer_id = cls.get("trainer_id")
        
        # 3. Fetch trainer name
        trainer_name = "Instructor"
        if trainer_id:
            user_res = supabase.table("users").select("full_name").eq("user_id", trainer_id).execute()
            if user_res.data:
                trainer_name = user_res.data[0]["full_name"]

        # 4. Return clean, flat JSON for the frontend
        return {
            "id": mat["material_id"],
            "classId": phase.get("class_id"),
            "className": cls.get("title", "Unknown Class"),
            "title": mat["title"],
            "type": mat["type"], # "VIDEO", "ARTICLE", "QUESTION"
            "content_url": mat.get("content_url"),
            "question_id": mat.get("question_id"),
            "postedBy": trainer_name,
            "difficulty": mat.get("questions", {}).get("difficulty") if mat.get("questions") else "Medium",
            "tags": mat.get("questions", {}).get("tags") if mat.get("questions") else [],
        }

    except Exception as e:
        print(f"Error fetching material view: {e}")
        raise HTTPException(status_code=500, detail="Error fetching material details")