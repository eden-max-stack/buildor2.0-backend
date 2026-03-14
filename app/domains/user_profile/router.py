from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import date, datetime
from app.infrastructure.database import get_db

router = APIRouter(prefix="/profile", tags=["User Profile"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

# --- Profile Card Models ---
class ProfileCardResponse(BaseModel):
    user_id: str
    full_name: str
    username: str
    email: str
    role: str
    profile_description: Optional[str]
    location: Optional[str]
    website: Optional[str]
    github_username: Optional[str]
    graduation_year: Optional[int]
    avatar_url: Optional[str]
    banner_url: Optional[str]
    skill_level: Optional[str]
    problems_solved: int
    rank: Optional[int]
    university: Optional[str]
    department: Optional[str]


class ProfileCardUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    profile_description: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = None
    website: Optional[str] = None
    github_username: Optional[str] = None
    graduation_year: Optional[int] = None
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None


# --- Portfolio README Models ---
class PortfolioReadmeResponse(BaseModel):
    user_id: str
    portfolio_readme: Optional[str]
    readme_updated_at: Optional[str]


class PortfolioReadmeUpdate(BaseModel):
    portfolio_readme: str = Field(..., max_length=50000)


# --- Academic Info Models ---
class AcademicInfoResponse(BaseModel):
    id: str
    user_id: str
    university: str
    degree: str
    major: Optional[str]
    minor: Optional[str]
    gpa: Optional[float]
    expected_graduation: Optional[str]
    honors: List[str]
    relevant_coursework: List[str]
    created_at: str
    updated_at: str


class AcademicInfoCreate(BaseModel):
    university: str = Field(..., min_length=1)
    degree: str = Field(..., min_length=1)
    major: Optional[str] = None
    minor: Optional[str] = None
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    expected_graduation: Optional[str] = None
    honors: List[str] = []
    relevant_coursework: List[str] = []


class AcademicInfoUpdate(BaseModel):
    university: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    minor: Optional[str] = None
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    expected_graduation: Optional[str] = None
    honors: Optional[List[str]] = None
    relevant_coursework: Optional[List[str]] = None


# --- External Links Models ---
class ExternalLinkResponse(BaseModel):
    id: str
    user_id: str
    platform: str
    url: str
    display_name: Optional[str]
    order_index: int


class ExternalLinkCreate(BaseModel):
    platform: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    display_name: Optional[str] = None
    order_index: int = 0


class ExternalLinkUpdate(BaseModel):
    platform: Optional[str] = None
    url: Optional[str] = None
    display_name: Optional[str] = None
    order_index: Optional[int] = None


# --- Contribution Activity Models ---
class ContributionDayResponse(BaseModel):
    date: str
    count: int
    level: int  # 0-4 for visualization


class ContributionGraphResponse(BaseModel):
    user_id: str
    contributions: List[ContributionDayResponse]
    total_contributions: int
    current_streak: int
    longest_streak: int


# --- Questions Solved History Models ---
class QuestionSolvedHistoryResponse(BaseModel):
    question_id: str
    question_title: str
    difficulty: str
    tags: List[str]
    solved_at: str
    best_runtime_ms: Optional[int]
    best_memory_kb: Optional[int]
    runtime_percentile: Optional[float]
    memory_percentile: Optional[float]
    hints_used: int
    language: str
    attempts: int


# --- Professor Feedback Models ---
class ProfessorFeedbackResponse(BaseModel):
    id: str
    student_id: str
    professor_id: str
    professor_name: str
    course_name: str
    course_code: Optional[str]
    feedback_text: str
    rating: Optional[int]
    is_visible: bool
    is_pinned: bool
    created_at: str


class ProfessorFeedbackCreate(BaseModel):
    student_id: UUID
    course_name: str = Field(..., min_length=1)
    course_code: Optional[str] = None
    feedback_text: str = Field(..., min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)


class ProfessorFeedbackUpdate(BaseModel):
    is_visible: Optional[bool] = None
    is_pinned: Optional[bool] = None


# ============================================
# ENDPOINTS
# ============================================

@router.get("/{user_id}", response_model=ProfileCardResponse)
def get_profile_card(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get complete profile card information for a user.
    
    Combines data from users and user_profiles tables.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    query = text("""
        SELECT 
            u.id, u.email, u.full_name, u.role, u.university, u.department,
            u.skill_level, u.problems_solved, u.rank,
            up.username, up.profile_description, up.location, up.website,
            up.github_username, up.graduation_year, up.avatar_url, up.banner_url
        FROM users u
        LEFT JOIN user_profiles up ON u.id = up.user_id
        WHERE u.id = :user_id
    """)
    
    result = db.execute(query, {"user_id": str(user_id)}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    return ProfileCardResponse(
        user_id=str(result.id),
        full_name=result.full_name,
        username=result.username or "user",
        email=result.email,
        role=result.role,
        profile_description=result.profile_description,
        location=result.location,
        website=result.website,
        github_username=result.github_username,
        graduation_year=result.graduation_year,
        avatar_url=result.avatar_url,
        banner_url=result.banner_url,
        skill_level=result.skill_level,
        problems_solved=result.problems_solved or 0,
        rank=result.rank,
        university=result.university,
        department=result.department
    )


@router.patch("/{user_id}", response_model=ProfileCardResponse)
def update_profile_card(
    user_id: UUID,
    profile_update: ProfileCardUpdate,
    db: Session = Depends(get_db)
):
    """
    Update profile card information.
    
    Updates user_profiles table. Creates profile if it doesn't exist.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Check if user exists
    user_check = db.execute(
        text("SELECT id FROM users WHERE id = :user_id"),
        {"user_id": str(user_id)}
    ).fetchone()
    
    if not user_check:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if profile exists
    profile_check = db.execute(
        text("SELECT user_id FROM user_profiles WHERE user_id = :user_id"),
        {"user_id": str(user_id)}
    ).fetchone()
    
    # Build update fields
    update_data = profile_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    if not profile_check:
        # Create new profile
        # Username is required for new profiles
        if 'username' not in update_data:
            raise HTTPException(status_code=400, detail="Username is required for new profiles")
        
        insert_query = text("""
            INSERT INTO user_profiles (
                user_id, username, profile_description, location, website,
                github_username, graduation_year, avatar_url, banner_url
            )
            VALUES (
                :user_id, :username, :profile_description, :location, :website,
                :github_username, :graduation_year, :avatar_url, :banner_url
            )
        """)
        
        db.execute(insert_query, {
            "user_id": str(user_id),
            "username": update_data.get('username'),
            "profile_description": update_data.get('profile_description'),
            "location": update_data.get('location'),
            "website": update_data.get('website'),
            "github_username": update_data.get('github_username'),
            "graduation_year": update_data.get('graduation_year'),
            "avatar_url": update_data.get('avatar_url'),
            "banner_url": update_data.get('banner_url')
        })
    else:
        # Update existing profile
        set_clauses = []
        params = {"user_id": str(user_id)}
        
        for field, value in update_data.items():
            set_clauses.append(f"{field} = :{field}")
            params[field] = value
        
        update_query = text(f"""
            UPDATE user_profiles
            SET {', '.join(set_clauses)}
            WHERE user_id = :user_id
        """)
        
        db.execute(update_query, params)
    
    db.commit()
    
    # Return updated profile
    return get_profile_card(user_id, db)


@router.get("/{user_id}/readme", response_model=PortfolioReadmeResponse)
def get_portfolio_readme(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get portfolio README markdown content for a user.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    query = text("""
        SELECT user_id, portfolio_readme, readme_updated_at
        FROM user_profiles
        WHERE user_id = :user_id
    """)
    
    result = db.execute(query, {"user_id": str(user_id)}).fetchone()
    
    if not result:
        # Return empty readme if profile doesn't exist
        return PortfolioReadmeResponse(
            user_id=str(user_id),
            portfolio_readme=None,
            readme_updated_at=None
        )
    
    return PortfolioReadmeResponse(
        user_id=str(result.user_id),
        portfolio_readme=result.portfolio_readme,
        readme_updated_at=result.readme_updated_at.isoformat() if result.readme_updated_at else None
    )


@router.patch("/{user_id}/readme", response_model=PortfolioReadmeResponse)
def update_portfolio_readme(
    user_id: UUID,
    readme_update: PortfolioReadmeUpdate,
    db: Session = Depends(get_db)
):
    """
    Update portfolio README markdown content.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Check if profile exists
    profile_check = db.execute(
        text("SELECT user_id FROM user_profiles WHERE user_id = :user_id"),
        {"user_id": str(user_id)}
    ).fetchone()
    
    if not profile_check:
        raise HTTPException(
            status_code=404,
            detail="User profile not found. Create profile first."
        )
    
    update_query = text("""
        UPDATE user_profiles
        SET portfolio_readme = :readme, readme_updated_at = NOW()
        WHERE user_id = :user_id
    """)
    
    db.execute(update_query, {
        "user_id": str(user_id),
        "readme": readme_update.portfolio_readme
    })
    
    db.commit()
    
    return get_portfolio_readme(user_id, db)


@router.get("/{user_id}/contributions", response_model=ContributionGraphResponse)
def get_contribution_graph(
    user_id: UUID,
    days: int = 365,
    db: Session = Depends(get_db)
):
    """
    Get contribution activity graph data for a user.
    
    Returns daily contribution counts for the specified number of days.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    query = text("""
        SELECT activity_date, contribution_count
        FROM contribution_activity
        WHERE user_id = :user_id
            AND activity_date >= CURRENT_DATE - INTERVAL ':days days'
        ORDER BY activity_date ASC
    """)
    
    results = db.execute(query, {"user_id": str(user_id), "days": days}).fetchall()
    
    # Calculate contribution levels (0-4 for visualization)
    contributions = []
    max_count = max([r.contribution_count for r in results], default=0)
    
    for row in results:
        level = 0
        if max_count > 0:
            ratio = row.contribution_count / max_count
            if ratio > 0.75:
                level = 4
            elif ratio > 0.5:
                level = 3
            elif ratio > 0.25:
                level = 2
            elif ratio > 0:
                level = 1
        
        contributions.append(ContributionDayResponse(
            date=row.activity_date.isoformat(),
            count=row.contribution_count,
            level=level
        ))
    
    # Calculate streaks
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    for i, contrib in enumerate(contributions):
        if contrib.count > 0:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
            if i == len(contributions) - 1:
                current_streak = temp_streak
        else:
            temp_streak = 0
    
    total_contributions = sum(c.count for c in contributions)
    
    return ContributionGraphResponse(
        user_id=str(user_id),
        contributions=contributions,
        total_contributions=total_contributions,
        current_streak=current_streak,
        longest_streak=longest_streak
    )


@router.get("/{user_id}/questions-solved", response_model=List[QuestionSolvedHistoryResponse])
def get_questions_solved_history(
    user_id: UUID,
    limit: int = 100,
    offset: int = 0,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get detailed history of questions solved by a user.
    
    Includes runtime, memory, ranking, and hints used for each solved question.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    difficulty_filter = ""
    if difficulty:
        difficulty_filter = "AND q.difficulty = :difficulty"
    
    query = text(f"""
        SELECT 
            q.id AS question_id,
            q.title AS question_title,
            q.difficulty,
            q.tags,
            uqp.solved_at,
            uqp.best_runtime_ms,
            uqp.best_memory_kb,
            uqp.hints_used_total,
            uqp.attempts,
            sr.runtime_percentile,
            sr.memory_percentile
        FROM user_question_progress uqp
        JOIN questions q ON uqp.question_id = q.id
        LEFT JOIN submissions s ON s.user_id = uqp.user_id 
            AND s.question_id = uqp.question_id 
            AND s.status = 'accepted'
            AND s.runtime_ms = uqp.best_runtime_ms
        LEFT JOIN submission_rankings sr ON sr.submission_id = s.id
        WHERE uqp.user_id = :user_id
            AND uqp.status = 'solved'
            {difficulty_filter}
        ORDER BY uqp.solved_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    params = {
        "user_id": str(user_id),
        "limit": limit,
        "offset": offset
    }
    if difficulty:
        params["difficulty"] = difficulty
    
    results = db.execute(query, params).fetchall()
    
    questions_solved = []
    for row in results:
        questions_solved.append(QuestionSolvedHistoryResponse(
            question_id=str(row.question_id),
            question_title=row.question_title,
            difficulty=row.difficulty,
            tags=row.tags or [],
            solved_at=row.solved_at.isoformat() if row.solved_at else "",
            best_runtime_ms=row.best_runtime_ms,
            best_memory_kb=row.best_memory_kb,
            runtime_percentile=float(row.runtime_percentile) if row.runtime_percentile else None,
            memory_percentile=float(row.memory_percentile) if row.memory_percentile else None,
            hints_used=row.hints_used_total or 0,
            language="python",  # Always Python as per requirements
            attempts=row.attempts or 0
        ))
    
    return questions_solved


@router.get("/{user_id}/academic-info", response_model=Optional[AcademicInfoResponse])
def get_academic_info(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get academic information for a user.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    query = text("""
        SELECT 
            id, user_id, university, degree, major, minor, gpa,
            expected_graduation, honors, relevant_coursework,
            created_at, updated_at
        FROM academic_info
        WHERE user_id = :user_id
    """)
    
    result = db.execute(query, {"user_id": str(user_id)}).fetchone()
    
    if not result:
        return None
    
    return AcademicInfoResponse(
        id=str(result.id),
        user_id=str(result.user_id),
        university=result.university,
        degree=result.degree,
        major=result.major,
        minor=result.minor,
        gpa=float(result.gpa) if result.gpa else None,
        expected_graduation=result.expected_graduation,
        honors=result.honors or [],
        relevant_coursework=result.relevant_coursework or [],
        created_at=result.created_at.isoformat(),
        updated_at=result.updated_at.isoformat()
    )


@router.post("/{user_id}/academic-info", response_model=AcademicInfoResponse, status_code=201)
def create_academic_info(
    user_id: UUID,
    academic_data: AcademicInfoCreate,
    db: Session = Depends(get_db)
):
    """
    Create academic information for a user.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Check if already exists
    existing = db.execute(
        text("SELECT id FROM academic_info WHERE user_id = :user_id"),
        {"user_id": str(user_id)}
    ).fetchone()
    
    if existing:
        raise HTTPException(status_code=400, detail="Academic info already exists. Use PATCH to update.")
    
    insert_query = text("""
        INSERT INTO academic_info (
            user_id, university, degree, major, minor, gpa,
            expected_graduation, honors, relevant_coursework
        )
        VALUES (
            :user_id, :university, :degree, :major, :minor, :gpa,
            :expected_graduation, :honors, :relevant_coursework
        )
        RETURNING id, created_at, updated_at
    """)
    
    result = db.execute(insert_query, {
        "user_id": str(user_id),
        "university": academic_data.university,
        "degree": academic_data.degree,
        "major": academic_data.major,
        "minor": academic_data.minor,
        "gpa": academic_data.gpa,
        "expected_graduation": academic_data.expected_graduation,
        "honors": academic_data.honors,
        "relevant_coursework": academic_data.relevant_coursework
    }).fetchone()
    
    db.commit()
    
    return AcademicInfoResponse(
        id=str(result.id),
        user_id=str(user_id),
        university=academic_data.university,
        degree=academic_data.degree,
        major=academic_data.major,
        minor=academic_data.minor,
        gpa=academic_data.gpa,
        expected_graduation=academic_data.expected_graduation,
        honors=academic_data.honors,
        relevant_coursework=academic_data.relevant_coursework,
        created_at=result.created_at.isoformat(),
        updated_at=result.updated_at.isoformat()
    )


@router.patch("/{user_id}/academic-info", response_model=AcademicInfoResponse)
def update_academic_info(
    user_id: UUID,
    academic_update: AcademicInfoUpdate,
    db: Session = Depends(get_db)
):
    """
    Update academic information for a user.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Check if exists
    existing = db.execute(
        text("SELECT id FROM academic_info WHERE user_id = :user_id"),
        {"user_id": str(user_id)}
    ).fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Academic info not found. Use POST to create.")
    
    update_data = academic_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clauses = []
    params = {"user_id": str(user_id)}
    
    for field, value in update_data.items():
        set_clauses.append(f"{field} = :{field}")
        params[field] = value
    
    update_query = text(f"""
        UPDATE academic_info
        SET {', '.join(set_clauses)}
        WHERE user_id = :user_id
    """)
    
    db.execute(update_query, params)
    db.commit()
    
    return get_academic_info(user_id, db)


@router.get("/{user_id}/external-links", response_model=List[ExternalLinkResponse])
def get_external_links(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get all external links for a user.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    query = text("""
        SELECT id, user_id, platform, url, display_name, order_index
        FROM external_links
        WHERE user_id = :user_id
        ORDER BY order_index ASC, created_at ASC
    """)
    
    results = db.execute(query, {"user_id": str(user_id)}).fetchall()
    
    return [
        ExternalLinkResponse(
            id=str(row.id),
            user_id=str(row.user_id),
            platform=row.platform,
            url=row.url,
            display_name=row.display_name,
            order_index=row.order_index
        )
        for row in results
    ]


@router.post("/{user_id}/external-links", response_model=ExternalLinkResponse, status_code=201)
def create_external_link(
    user_id: UUID,
    link_data: ExternalLinkCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new external link for a user.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    insert_query = text("""
        INSERT INTO external_links (
            user_id, platform, url, display_name, order_index
        )
        VALUES (
            :user_id, :platform, :url, :display_name, :order_index
        )
        RETURNING id
    """)
    
    result = db.execute(insert_query, {
        "user_id": str(user_id),
        "platform": link_data.platform,
        "url": link_data.url,
        "display_name": link_data.display_name,
        "order_index": link_data.order_index
    }).fetchone()
    
    db.commit()
    
    return ExternalLinkResponse(
        id=str(result.id),
        user_id=str(user_id),
        platform=link_data.platform,
        url=link_data.url,
        display_name=link_data.display_name,
        order_index=link_data.order_index
    )


@router.patch("/external-links/{link_id}", response_model=ExternalLinkResponse)
def update_external_link(
    link_id: UUID,
    link_update: ExternalLinkUpdate,
    user_id: UUID = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Update an external link.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify ownership
    link_check = db.execute(
        text("SELECT user_id FROM external_links WHERE id = :link_id"),
        {"link_id": str(link_id)}
    ).fetchone()
    
    if not link_check:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if str(link_check.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied: Not your link")
    
    update_data = link_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clauses = []
    params = {"link_id": str(link_id)}
    
    for field, value in update_data.items():
        set_clauses.append(f"{field} = :{field}")
        params[field] = value
    
    update_query = text(f"""
        UPDATE external_links
        SET {', '.join(set_clauses)}
        WHERE id = :link_id
        RETURNING user_id, platform, url, display_name, order_index
    """)
    
    result = db.execute(update_query, params).fetchone()
    db.commit()
    
    return ExternalLinkResponse(
        id=str(link_id),
        user_id=str(result.user_id),
        platform=result.platform,
        url=result.url,
        display_name=result.display_name,
        order_index=result.order_index
    )


@router.delete("/external-links/{link_id}", status_code=204)
def delete_external_link(
    link_id: UUID,
    user_id: UUID = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Delete an external link.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify ownership
    link_check = db.execute(
        text("SELECT user_id FROM external_links WHERE id = :link_id"),
        {"link_id": str(link_id)}
    ).fetchone()
    
    if not link_check:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if str(link_check.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied: Not your link")
    
    db.execute(
        text("DELETE FROM external_links WHERE id = :link_id"),
        {"link_id": str(link_id)}
    )
    db.commit()
    
    return None


@router.get("/{student_id}/professor-feedback", response_model=List[ProfessorFeedbackResponse])
def get_professor_feedback(
    student_id: UUID,
    include_hidden: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get professor feedback for a student's profile.
    
    By default, only returns visible feedback.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    visibility_filter = "" if include_hidden else "AND pf.is_visible = true"
    
    query = text(f"""
        SELECT 
            pf.id, pf.student_id, pf.professor_id, pf.course_name,
            pf.course_code, pf.feedback_text, pf.rating, pf.is_visible,
            pf.is_pinned, pf.created_at,
            u.full_name AS professor_name
        FROM professor_feedback_profile pf
        JOIN users u ON pf.professor_id = u.id
        WHERE pf.student_id = :student_id {visibility_filter}
        ORDER BY pf.is_pinned DESC, pf.created_at DESC
    """)
    
    results = db.execute(query, {"student_id": str(student_id)}).fetchall()
    
    return [
        ProfessorFeedbackResponse(
            id=str(row.id),
            student_id=str(row.student_id),
            professor_id=str(row.professor_id),
            professor_name=row.professor_name,
            course_name=row.course_name,
            course_code=row.course_code,
            feedback_text=row.feedback_text,
            rating=row.rating,
            is_visible=row.is_visible,
            is_pinned=row.is_pinned,
            created_at=row.created_at.isoformat()
        )
        for row in results
    ]


@router.post("/professor-feedback", response_model=ProfessorFeedbackResponse, status_code=201)
def create_professor_feedback(
    feedback_data: ProfessorFeedbackCreate,
    professor_id: UUID = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Create professor feedback for a student's profile.
    
    Only professors/trainers can create feedback.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify professor exists and is a trainer
    prof_check = db.execute(
        text("SELECT id, role, full_name FROM users WHERE id = :professor_id"),
        {"professor_id": str(professor_id)}
    ).fetchone()
    
    if not prof_check:
        raise HTTPException(status_code=404, detail="Professor not found")
    
    if prof_check.role != 'trainer':
        raise HTTPException(status_code=403, detail="Only trainers can create feedback")
    
    # Verify student exists
    student_check = db.execute(
        text("SELECT id FROM users WHERE id = :student_id"),
        {"student_id": str(feedback_data.student_id)}
    ).fetchone()
    
    if not student_check:
        raise HTTPException(status_code=404, detail="Student not found")
    
    insert_query = text("""
        INSERT INTO professor_feedback_profile (
            student_id, professor_id, course_name, course_code,
            feedback_text, rating
        )
        VALUES (
            :student_id, :professor_id, :course_name, :course_code,
            :feedback_text, :rating
        )
        RETURNING id, created_at
    """)
    
    result = db.execute(insert_query, {
        "student_id": str(feedback_data.student_id),
        "professor_id": str(professor_id),
        "course_name": feedback_data.course_name,
        "course_code": feedback_data.course_code,
        "feedback_text": feedback_data.feedback_text,
        "rating": feedback_data.rating
    }).fetchone()
    
    db.commit()
    
    return ProfessorFeedbackResponse(
        id=str(result.id),
        student_id=str(feedback_data.student_id),
        professor_id=str(professor_id),
        professor_name=prof_check.full_name,
        course_name=feedback_data.course_name,
        course_code=feedback_data.course_code,
        feedback_text=feedback_data.feedback_text,
        rating=feedback_data.rating,
        is_visible=True,
        is_pinned=False,
        created_at=result.created_at.isoformat()
    )


@router.patch("/professor-feedback/{feedback_id}", response_model=ProfessorFeedbackResponse)
def update_professor_feedback_visibility(
    feedback_id: UUID,
    feedback_update: ProfessorFeedbackUpdate,
    student_id: UUID = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Update professor feedback visibility/pinned status.
    
    Only the student can update their own feedback visibility.
    """
    
    # Check SQLite guard
    db_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=500,
            detail="Backend is connected to SQLite, but these routes require the Supabase Postgres schema."
        )
    
    # Verify ownership
    feedback_check = db.execute(
        text("SELECT student_id FROM professor_feedback_profile WHERE id = :feedback_id"),
        {"feedback_id": str(feedback_id)}
    ).fetchone()
    
    if not feedback_check:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    if str(feedback_check.student_id) != str(student_id):
        raise HTTPException(status_code=403, detail="Access denied: Not your feedback")
    
    update_data = feedback_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clauses = []
    params = {"feedback_id": str(feedback_id)}
    
    for field, value in update_data.items():
        set_clauses.append(f"{field} = :{field}")
        params[field] = value
    
    update_query = text(f"""
        UPDATE professor_feedback_profile
        SET {', '.join(set_clauses)}
        WHERE id = :feedback_id
        RETURNING student_id, professor_id, course_name, course_code,
                  feedback_text, rating, is_visible, is_pinned, created_at
    """)
    
    result = db.execute(update_query, params).fetchone()
    db.commit()
    
    # Get professor name
    prof_name = db.execute(
        text("SELECT full_name FROM users WHERE id = :professor_id"),
        {"professor_id": str(result.professor_id)}
    ).fetchone().full_name
    
    return ProfessorFeedbackResponse(
        id=str(feedback_id),
        student_id=str(result.student_id),
        professor_id=str(result.professor_id),
        professor_name=prof_name,
        course_name=result.course_name,
        course_code=result.course_code,
        feedback_text=result.feedback_text,
        rating=result.rating,
        is_visible=result.is_visible,
        is_pinned=result.is_pinned,
        created_at=result.created_at.isoformat()
    )
