from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.infrastructure.database import get_db

router = APIRouter(prefix="/trainer-analytics", tags=["Trainer Analytics"])

@router.get("/overview/{trainer_id}")
def get_trainer_overview(
    trainer_id: str,
    db: Session = Depends(get_db)
):
    """
    Get trainer analytics overview including:
    - Total classes
    - Total students across all classes
    - Pending tasks (grading, overdue)
    - Unread feedback count
    - List of classes with details
    - Upcoming tasks
    - Recent feedback
    """
    
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail=(
                "Backend is connected to SQLite, but these routes require the Supabase Postgres schema. "
                "Start the server with DATABASE_URL set to your Supabase Postgres connection string."
            ),
        )

    # Verify trainer exists
    trainer_check = db.execute(
        text("SELECT id, full_name FROM users WHERE id = :trainer_id AND role = 'trainer'"),
        {"trainer_id": trainer_id}
    ).fetchone()
    
    if not trainer_check:
        raise HTTPException(status_code=404, detail="Trainer not found")
    
    # Get overview stats
    stats_query = text("""
        SELECT 
            COUNT(DISTINCT c.id) as total_classes,
            COUNT(DISTINCT ce.student_id) as total_students,
            COUNT(DISTINCT CASE WHEN t.status IN ('grading', 'overdue') THEN t.id END) as pending_tasks,
            COUNT(DISTINCT CASE WHEN f.is_read = false THEN f.id END) as unread_feedback
        FROM classes c
        LEFT JOIN class_enrollments ce ON ce.class_id = c.id AND ce.status = 'active'
        LEFT JOIN tasks t ON t.class_id = c.id
        LEFT JOIN feedback f ON f.class_id = c.id
        WHERE c.trainer_id = :trainer_id
    """)
    
    stats = db.execute(stats_query, {"trainer_id": trainer_id}).fetchone()
    
    # Get classes with student counts
    classes_query = text("""
        SELECT 
            c.id,
            c.name,
            c.code,
            c.next_session,
            c.progress,
            COUNT(DISTINCT ce.student_id) as student_count
        FROM classes c
        LEFT JOIN class_enrollments ce ON ce.class_id = c.id AND ce.status = 'active'
        WHERE c.trainer_id = :trainer_id
        GROUP BY c.id, c.name, c.code, c.next_session, c.progress
        ORDER BY c.created_at DESC
    """)
    
    classes = db.execute(classes_query, {"trainer_id": trainer_id}).fetchall()
    
    # Get upcoming tasks
    tasks_query = text("""
        SELECT 
            t.id,
            t.title,
            t.type,
            t.status,
            t.due_date,
            c.code as class_code
        FROM tasks t
        JOIN classes c ON c.id = t.class_id
        WHERE c.trainer_id = :trainer_id
        ORDER BY 
            CASE t.status
                WHEN 'overdue' THEN 1
                WHEN 'grading' THEN 2
                WHEN 'pending' THEN 3
                ELSE 4
            END,
            (t.due_date IS NULL) ASC,
            t.due_date ASC
        LIMIT 10
    """)
    
    tasks = db.execute(tasks_query, {"trainer_id": trainer_id}).fetchall()
    
    # Get recent feedback
    feedback_query = text("""
        SELECT 
            f.id,
            f.type,
            f.message,
            f.is_read,
            f.created_at,
            u.full_name as student_name,
            c.code as class_code
        FROM feedback f
        JOIN users u ON u.id = f.student_id
        JOIN classes c ON c.id = f.class_id
        WHERE c.trainer_id = :trainer_id
        ORDER BY f.created_at DESC
        LIMIT 20
    """)
    
    feedback = db.execute(feedback_query, {"trainer_id": trainer_id}).fetchall()
    
    # Format response
    return {
        "trainer": {
            "id": str(trainer_check.id),
            "name": trainer_check.full_name
        },
        "stats": {
            "totalClasses": stats.total_classes or 0,
            "totalStudents": stats.total_students or 0,
            "pendingTasks": stats.pending_tasks or 0,
            "unreadFeedback": stats.unread_feedback or 0
        },
        "classes": [
            {
                "id": cls.id,
                "name": cls.name,
                "code": cls.code,
                "studentCount": cls.student_count or 0,
                "nextSession": cls.next_session,
                "progress": cls.progress
            }
            for cls in classes
        ],
        "tasks": [
            {
                "id": str(task.id),
                "title": task.title,
                "classCode": task.class_code,
                "type": task.type,
                "status": task.status,
                "dueDate": task.due_date.isoformat() if task.due_date else None
            }
            for task in tasks
        ],
        "feedback": [
            {
                "id": str(fb.id),
                "studentName": fb.student_name,
                "classCode": fb.class_code,
                "type": fb.type,
                "message": fb.message,
                "read": fb.is_read,
                "date": fb.created_at.isoformat() if fb.created_at else None
            }
            for fb in feedback
        ]
    }


@router.get("/classes/{class_id}")
def get_class_details(
    class_id: str,
    trainer_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific class including:
    - Class metadata (name, code, student count, avg score, etc.)
    - List of enrolled students with their performance
    - Student rankings within the class
    """
    
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail=(
                "Backend is connected to SQLite, but these routes require the Supabase Postgres schema. "
                "Start the server with DATABASE_URL set to your Supabase Postgres connection string."
            ),
        )

    # Get class details
    class_query = text("""
        SELECT 
            c.id,
            c.name,
            c.code,
            c.trainer_id,
            c.progress as completion_rate,
            COUNT(DISTINCT ce.student_id) as student_count,
            u.full_name as trainer_name
        FROM classes c
        LEFT JOIN class_enrollments ce ON ce.class_id = c.id AND ce.status = 'active'
        LEFT JOIN users u ON u.id = c.trainer_id
        WHERE c.id = :class_id
        GROUP BY c.id, c.name, c.code, c.trainer_id, c.progress, u.full_name
    """)
    
    class_info = db.execute(class_query, {"class_id": class_id}).fetchone()
    
    if not class_info:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Verify trainer access if trainer_id provided
    if trainer_id and str(class_info.trainer_id) != trainer_id:
        raise HTTPException(status_code=403, detail="Access denied: Not your class")
    
    # Get students enrolled in this class with their performance
    students_query = text("""
        SELECT 
            u.id,
            u.full_name as name,
            u.email,
            u.skill_level,
            u.problems_solved,
            ce.individual_progress,
            ce.enrolled_at,
            (
                SELECT COUNT(*) 
                FROM user_question_progress uqp 
                WHERE uqp.user_id = u.id AND uqp.status = 'solved'
            ) as total_problems_solved,
            (
                SELECT COUNT(*) 
                FROM questions q 
                WHERE q.is_active = true
            ) as total_problems
        FROM class_enrollments ce
        JOIN users u ON u.id = ce.student_id
        WHERE ce.class_id = :class_id AND ce.status = 'active'
        ORDER BY u.problems_solved DESC, u.created_at ASC
    """)
    
    students = db.execute(students_query, {"class_id": class_id}).fetchall()
    
    # Calculate average score and find top performer
    avg_score = 0
    top_performer = None
    if students:
        total_progress = sum(s.individual_progress or 0 for s in students)
        avg_score = round(total_progress / len(students)) if len(students) > 0 else 0
        top_performer = students[0].name if students else None
    
    # Format students with rank
    formatted_students = []
    for idx, student in enumerate(students, start=1):
        formatted_students.append({
            "id": str(student.id),
            "name": student.name,
            "email": student.email,
            "rank": idx,
            "problemsSolved": student.total_problems_solved or 0,
            "totalProblems": student.total_problems or 0,
            "skillLevel": student.skill_level,
            "individualProgress": student.individual_progress or 0,
            "enrolledAt": student.enrolled_at.isoformat() if student.enrolled_at else None
        })
    
    return {
        "classInfo": {
            "id": class_info.id,
            "name": class_info.name,
            "code": class_info.code,
            "studentCount": class_info.student_count or 0,
            "avgScore": avg_score,
            "topPerformer": top_performer,
            "completionRate": class_info.completion_rate or 0,
            "trainerName": class_info.trainer_name
        },
        "students": formatted_students
    }


@router.post("/feedback/{feedback_id}/mark-read")
def mark_feedback_as_read(
    feedback_id: str,
    trainer_id: str,
    db: Session = Depends(get_db)
):
    """
    Mark a feedback item as read by the trainer.
    """
    
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail=(
                "Backend is connected to SQLite, but these routes require the Supabase Postgres schema. "
                "Start the server with DATABASE_URL set to your Supabase Postgres connection string."
            ),
        )

    # Verify feedback belongs to trainer's class
    verify_query = text("""
        SELECT f.id
        FROM feedback f
        JOIN classes c ON c.id = f.class_id
        WHERE f.id = :feedback_id AND c.trainer_id = :trainer_id
    """)
    
    feedback = db.execute(verify_query, {"feedback_id": feedback_id, "trainer_id": trainer_id}).fetchone()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found or access denied")
    
    # Mark as read
    update_query = text("""
        UPDATE feedback
        SET is_read = true, updated_at = NOW()
        WHERE id = :feedback_id
    """)
    
    db.execute(update_query, {"feedback_id": feedback_id})
    db.commit()
    
    return {"success": True, "message": "Feedback marked as read"}


@router.post("/feedback/{feedback_id}/respond")
def respond_to_feedback(
    feedback_id: str,
    trainer_id: str,
    response: str,
    db: Session = Depends(get_db)
):
    """
    Respond to student feedback.
    """
    
    # Verify feedback belongs to trainer's class
    verify_query = text("""
        SELECT f.id
        FROM feedback f
        JOIN classes c ON c.id = f.class_id
        WHERE f.id = :feedback_id AND c.trainer_id = :trainer_id
    """)
    
    feedback = db.execute(verify_query, {"feedback_id": feedback_id, "trainer_id": trainer_id}).fetchone()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found or access denied")
    
    # Add response
    update_query = text("""
        UPDATE feedback
        SET 
            response = :response,
            responded_at = NOW(),
            responded_by = :trainer_id,
            is_read = true,
            updated_at = NOW()
        WHERE id = :feedback_id
    """)
    
    db.execute(update_query, {
        "feedback_id": feedback_id,
        "trainer_id": trainer_id,
        "response": response
    })
    db.commit()
    
    return {"success": True, "message": "Response added successfully"}