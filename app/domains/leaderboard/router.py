from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Literal
from uuid import UUID
from app.infrastructure.database import get_db

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

@router.get("/")
def get_leaderboard(
    ranking_type: Literal["overall", "skill", "problems"] = Query(
        "overall",
        description="Type of ranking: 'overall' (default rank), 'skill' (by skill level), 'problems' (by problems solved)"
    ),
    search: Optional[str] = Query(None, description="Search students by name"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of students to return"),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard with different ranking algorithms.
    
    **Ranking Types:**
    - `overall`: Uses the pre-calculated rank from the database (based on problems solved)
    - `skill`: Ranks by skill level (Expert > Advanced > Intermediate > Beginner), then by problems solved
    - `problems`: Ranks purely by number of problems solved (descending)
    
    **Returns:**
    - List of students with their rank, name, problems solved, skill level, and university info
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

    # Base query - get all students with their data
    base_query = """
        SELECT 
            u.id,
            u.full_name as name,
            u.rank,
            u.problems_solved,
            u.skill_level,
            u.university,
            u.department,
            u.avatar_url
        FROM users u
        WHERE u.role = 'student'
    """
    
    # Add search filter if provided
    params = {"limit": limit}
    if search:
        base_query += " AND LOWER(u.full_name) LIKE LOWER(:search)"
        params["search"] = f"%{search}%"
    
    # Apply ranking logic based on type
    if ranking_type == "overall":
        # Use pre-calculated rank from database
        # Portable replacement for "NULLS LAST": ORDER BY (rank IS NULL), rank
        base_query += " ORDER BY (u.rank IS NULL) ASC, u.rank ASC"
    
    elif ranking_type == "skill":
        # Rank by skill level (Expert > Advanced > Intermediate > Beginner)
        # Then by problems solved as tiebreaker
        base_query += """
            ORDER BY 
                CASE u.skill_level
                    WHEN 'Expert' THEN 4
                    WHEN 'Advanced' THEN 3
                    WHEN 'Intermediate' THEN 2
                    WHEN 'Beginner' THEN 1
                    ELSE 0
                END DESC,
                u.problems_solved DESC,
                u.created_at ASC
        """
    
    elif ranking_type == "problems":
        # Rank purely by problems solved
        base_query += " ORDER BY u.problems_solved DESC, u.created_at ASC"
    
    # Add limit
    base_query += " LIMIT :limit"
    
    # Execute query
    result = db.execute(text(base_query), params)
    students = result.fetchall()
    
    # Format response
    leaderboard = []
    for idx, student in enumerate(students, start=1):
        leaderboard.append({
            "id": str(student.id),
            "name": student.name,
            "rank": idx if ranking_type != "overall" else student.rank,  # Recalculate rank for non-overall views
            "problemsSolved": student.problems_solved,
            "skillLevel": student.skill_level,
            "university": student.university,
            "department": student.department,
            "avatarUrl": student.avatar_url
        })
    
    return {
        "rankingType": ranking_type,
        "totalStudents": len(leaderboard),
        "students": leaderboard
    }


@router.get("/user/{user_id}")
def get_user_leaderboard_position(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific user's leaderboard position and stats.
    
    **Returns:**
    - User's current rank, problems solved, skill level, and other stats
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

    query = text("""
        SELECT 
            u.id,
            u.full_name as name,
            u.rank,
            u.problems_solved,
            u.skill_level,
            u.university,
            u.department,
            u.avatar_url,
            (
                SELECT COUNT(*) 
                FROM user_question_progress uqp 
                WHERE uqp.user_id = u.id AND uqp.status = 'solved'
            ) as total_solved,
            (
                SELECT COUNT(*) 
                FROM questions q 
                WHERE q.is_active = true
            ) as total_questions
        FROM users u
        WHERE u.id = :user_id AND u.role = 'student'
    """)
    
    result = db.execute(query, {"user_id": str(user_id)})
    user = result.fetchone()
    
    if not user:
        return {"error": "User not found or not a student"}
    
    return {
        "id": str(user.id),
        "name": user.name,
        "rank": user.rank,
        "problemsSolved": user.problems_solved,
        "skillLevel": user.skill_level,
        "university": user.university,
        "department": user.department,
        "avatarUrl": user.avatar_url,
        "totalQuestions": user.total_questions,
        "completionRate": round((user.total_solved / user.total_questions * 100), 2) if user.total_questions > 0 else 0
    }