
import truststore # type: ignore
truststore.inject_into_ssl()

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.profiles.models import (
    StudentProfileUpdate,
    TrainerProfileUpdate,
    TrainerAttestationCreate,
    TrainerRatingCreate,
    TrainerReviewCreate,
    get_current_user,
)
from app.infrastructure.supabase_client import supabase

router = APIRouter(prefix="/api/profile", tags=["Profiles"])

@router.put("/student")
async def update_student_profile(
    profile_data: StudentProfileUpdate,
    current_user = Depends(get_current_user)
):
    user_id = current_user.id

    # Convert Pydantic model to a dictionary, omitting any values the frontend didn't send
    update_payload = profile_data.model_dump(exclude_unset=True)

    try:
        # Update the row in Postgres where user_id matches the authenticated user
        response = supabase.table("student_profiles") \
            .update(update_payload) \
            .eq("user_id", user_id) \
            .execute()

        return {"message": "Student profile updated successfully!", "data": response.data}

    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error saving profile"
        )

@router.get("/student")
async def get_user_profile(current_user = Depends(get_current_user)):
    user_id = current_user.id

    try:
        # 1. Fetch core user data (Name, Email, etc.)
        user_response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        user_data = user_response.data[0] if user_response.data else {}

        # 2. Fetch student profile data (University, GPA, etc.)
        profile_response = supabase.table("student_profiles").select("*").eq("user_id", user_id).execute()
        profile_data = profile_response.data[0] if profile_response.data else {}

        # 3. Transform Database variables into Frontend Props
        full_name = user_data.get("full_name", "Student")
        email = user_data.get("email", "")
        # Fallback: create a username from their email if you don't have a username column
        username = email.split("@")[0] if email else "user" 

        # 4. Construct the exact JSON shape Next.js expects
        payload = {
            "leftProfileCard": {
                "fullName": full_name,
                "username": username,
                "profileDesc": profile_data.get("bio", "Passionate developer eager to learn."),
                "graduationYear": profile_data.get("expected_grad_year", "N/A"),
                "location": profile_data.get("location", "earth"), 
                "website": profile_data.get("github_url", ""),
                "skills": profile_data.get("skills", ["React", "Python", "SQL"])
            },
            "portfolioMd": profile_data.get("portfolio_md"),
            "academicInfo": {
                "university": profile_data.get("university", "Not specified"),
                "degree": profile_data.get("degree", "Not specified"),
                "gpa": str(profile_data.get("gpa", "N/A")),
                "expectedGraduation": str(profile_data.get("expected_grad_year", "N/A"))
            },
            # --- Safely Mocking Missing DB Tables ---
            # Return empty arrays/None so React doesn't crash calling .map() on undefined
            "contributionGrid": {
                "totalContributions": 0,
                "data": [0] * 365 # Empty grid
            },
            "solvedQuestions": [],
            "professorFeedback": [],
            "currentProject": None,
            "recentAchievement": None,
            "externalLinks": []
        }

        # Dynamically add Github to external links if they provided it
        if profile_data.get("github_url"):
            payload["externalLinks"].append({
                "id": "github-1",
                "platform": "GitHub",
                "url": profile_data.get("github_url")
            })

        return payload

    except Exception as e:
        print(f"Error fetching profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching profile data"
        )
    

@router.put("/trainer")
async def update_trainer_profile(
    profile_data: TrainerProfileUpdate,
    current_user = Depends(get_current_user)
):
    user_id = current_user.id

    # Convert Pydantic model to a dictionary, omitting any values the frontend didn't send
    update_payload = profile_data.model_dump(exclude_unset=True)

    try:
        # Update the row in Postgres where user_id matches the authenticated user
        response = supabase.table("trainer_profiles") \
            .update(update_payload) \
            .eq("user_id", user_id) \
            .execute()

        return {"message": "Trainer profile updated successfully!", "data": response.data}

    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error saving profile"
        )

@router.get("/me")
async def get_my_role(current_user = Depends(get_current_user)):
    user_id = current_user.id
    try:
        trainer_res = supabase.table("trainer_profiles").select("user_id").eq("user_id", user_id).execute()
        if trainer_res.data:
            return {"role": "TRAINER"}
        return {"role": "STUDENT"}
    except Exception as e:
        print(f"Error fetching role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error determining user role"
        )

@router.get("/trainer")
async def get_trainer_profile(current_user = Depends(get_current_user)):
    user_id = current_user.id

    try:
        # 1. Fetch core user data (Name, Email, etc.)
        user_response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        user_data = user_response.data[0] if user_response.data else {}

        # 2. Fetch trainer profile data (title, workplace)
        profile_response = supabase.table("trainer_profiles").select("*").eq("user_id", user_id).execute()
        profile_data = profile_response.data[0] if profile_response.data else {}

        attestations_res = supabase.table("trainer_attestations").select("attestation_id, title, description, attachment_url").eq("trainer_id", user_id).execute()
        attestations = attestations_res.data or []
        att_titles = [a.get("title") for a in attestations if a.get("title")]

        # 3. Transform Database variables into Frontend Props   
        full_name = user_data.get("full_name", "Trainer")
        email = user_data.get("email", "")
        # Fallback: create a username from their email if you don't have a username column
        username = email.split("@")[0] if email else "user" 

        # 4. Construct the exact JSON shape Next.js expects
        payload = {
            "role": "TRAINER",
            "title": profile_data.get("title", "Trainer"),
            "workplace": profile_data.get("workplace", "Buildor"),
            "leftProfileCard": {
                "fullName": full_name,
                "username": username,
                "profileDesc": profile_data.get("bio") or "",
                "graduationYear": None,
                "location": profile_data.get("location") or "",
                "website": profile_data.get("website") or "",
                "skills": att_titles,
            },
            "attestations": attestations,
            "availability_text": profile_data.get("availability_text") or "",
            "externalLinks": [],
            "portfolioMd": None,
        }
        
        if profile_data.get("github_url"):
            payload["externalLinks"].append({
                "id": "github-1",
                "platform": "GitHub",
                "url": profile_data.get("github_url")
            })
        
        # Fetch anonymous reviews for this trainer
        reviews_res = supabase.table("trainer_reviews").select(
            "review_id, content, moderation_status, created_at"
        ).eq("trainer_id", user_id).eq("moderation_status", "APPROVED").execute()
        payload["reviews"] = reviews_res.data or []

        # Fetch average rating
        payload["average_rating"] = profile_data.get("average_rating")
        payload["rating_count"] = profile_data.get("rating_count", 0)

        return payload

    except Exception as e:
        print(f"Error fetching profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching profile data"
        )


# ──────────────────────────────────────────────
# ATTESTATION ENDPOINTS (trainer credentials)
# ──────────────────────────────────────────────

@router.get("/trainer/attestations")
async def get_trainer_attestations(current_user=Depends(get_current_user)):
    user_id = current_user.id
    try:
        res = supabase.table("trainer_attestations").select("*").eq("trainer_id", user_id).execute()
        return res.data or []
    except Exception as e:
        print(f"Error fetching attestations: {e}")
        raise HTTPException(status_code=500, detail="Error fetching attestations")


@router.post("/trainer/attestations")
async def create_trainer_attestation(
    data: TrainerAttestationCreate,
    current_user=Depends(get_current_user),
):
    user_id = current_user.id
    try:
        payload = data.model_dump()
        payload["trainer_id"] = user_id
        res = supabase.table("trainer_attestations").insert(payload).execute()
        return {"message": "Attestation created", "data": res.data}
    except Exception as e:
        print(f"Error creating attestation: {e}")
        raise HTTPException(status_code=500, detail="Error creating attestation")


@router.delete("/trainer/attestations/{attestation_id}")
async def delete_trainer_attestation(
    attestation_id: str,
    current_user=Depends(get_current_user),
):
    user_id = current_user.id
    try:
        res = (
            supabase.table("trainer_attestations")
            .delete()
            .eq("attestation_id", attestation_id)
            .eq("trainer_id", user_id)
            .execute()
        )
        return {"message": "Attestation deleted", "data": res.data}
    except Exception as e:
        print(f"Error deleting attestation: {e}")
        raise HTTPException(status_code=500, detail="Error deleting attestation")


# ──────────────────────────────────────────────
# TRAINER RATING ENDPOINTS
# ──────────────────────────────────────────────

@router.post("/trainer/rate")
async def rate_trainer(
    data: TrainerRatingCreate,
    current_user=Depends(get_current_user),
):
    """Any user (except the trainer themselves) can rate a trainer (decimal 0-5)."""
    user_id = current_user.id
    trainer_id = data.trainer_id

    if str(user_id) == str(trainer_id):
        raise HTTPException(status_code=400, detail="You cannot rate yourself")

    if data.rating < 0 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")

    try:
        # Upsert into trainer_ratings (one rating per user per trainer)
        supabase.table("trainer_ratings").upsert(
            {"trainer_id": trainer_id, "user_id": user_id, "rating": data.rating},
            on_conflict="trainer_id,user_id",
        ).execute()

        # Recompute average for the trainer
        all_res = supabase.table("trainer_ratings").select("rating").eq("trainer_id", trainer_id).execute()
        ratings = [r["rating"] for r in (all_res.data or [])]
        avg = round(sum(ratings) / len(ratings), 2) if ratings else None
        count = len(ratings)

        supabase.table("trainer_profiles").update(
            {"average_rating": avg, "rating_count": count}
        ).eq("user_id", trainer_id).execute()

        return {"message": "Rating submitted", "average_rating": avg, "rating_count": count}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error rating trainer: {e}")
        raise HTTPException(status_code=500, detail="Error submitting rating")


@router.get("/trainer/{trainer_id}/rating")
async def get_trainer_rating(trainer_id: str):
    """Public: get a trainer's average rating."""
    try:
        res = supabase.table("trainer_profiles").select(
            "average_rating, rating_count"
        ).eq("user_id", trainer_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Trainer not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching rating: {e}")
        raise HTTPException(status_code=500, detail="Error fetching rating")


# ──────────────────────────────────────────────
# TRAINER REVIEW / FEEDBACK ENDPOINTS (anonymous)
# ──────────────────────────────────────────────

@router.post("/trainer/review")
async def create_trainer_review(
    data: TrainerReviewCreate,
    current_user=Depends(get_current_user),
):
    """Submit an anonymous review for a trainer. Starts as PENDING moderation."""
    user_id = current_user.id
    if str(user_id) == str(data.trainer_id):
        raise HTTPException(status_code=400, detail="You cannot review yourself")

    try:
        payload = {
            "trainer_id": data.trainer_id,
            "class_id": data.class_id,
            "content": data.content,
            "reviewer_id": user_id,
            "moderation_status": "APPROVED",  # auto-approve for now; switch to PENDING if you add moderation
        }
        res = supabase.table("trainer_reviews").insert(payload).execute()
        return {"message": "Review submitted", "data": res.data}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail="Error submitting review")


@router.get("/trainer/{trainer_id}/reviews")
async def get_trainer_reviews(trainer_id: str):
    """Public: get approved anonymous reviews for a trainer."""
    try:
        res = (
            supabase.table("trainer_reviews")
            .select("review_id, content, created_at")
            .eq("trainer_id", trainer_id)
            .eq("moderation_status", "APPROVED")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail="Error fetching reviews")


@router.get("/trainer/{trainer_id}")
async def get_trainer_profile_by_id(trainer_id: str):
    """Public: get a trainer's profile by ID."""
    try:
        # 1. Fetch core user data (Name, Email, etc.)
        user_response = supabase.table("users").select("*").eq("user_id", trainer_id).execute()
        user_data = user_response.data[0] if user_response.data else {}

        # 2. Fetch trainer profile data (title, workplace)
        profile_response = supabase.table("trainer_profiles").select("*").eq("user_id", trainer_id).execute()
        profile_data = profile_response.data[0] if profile_response.data else {}

        attestations_res = supabase.table("trainer_attestations").select("attestation_id, title, description, attachment_url").eq("trainer_id", trainer_id).execute()
        attestations = attestations_res.data or []
        att_titles = [a.get("title") for a in attestations if a.get("title")]

        # 3. Transform Database variables into Frontend Props   
        full_name = user_data.get("full_name", "Trainer")
        email = user_data.get("email", "")
        # Fallback: create a username from their email if you don't have a username column
        username = email.split("@")[0] if email else "user" 

        # 4. Construct the exact JSON shape Next.js expects
        payload = {
            "role": "TRAINER",
            "title": profile_data.get("title", "Trainer"),
            "workplace": profile_data.get("workplace", "Buildor"),
            "leftProfileCard": {
                "fullName": full_name,
                "username": username,
                "profileDesc": profile_data.get("bio") or "",
                "graduationYear": None,
                "location": profile_data.get("location") or "",
                "website": profile_data.get("website") or "",
                "skills": att_titles,
            },
            "attestations": attestations,
            "availability_text": profile_data.get("availability_text") or "",
            "externalLinks": [],
            "portfolioMd": None,
        }
        
        if profile_data.get("github_url"):
            payload["externalLinks"].append({
                "id": "github-1",
                "platform": "GitHub",
                "url": profile_data.get("github_url")
            })
        
        # Fetch anonymous reviews for this trainer
        reviews_res = supabase.table("trainer_reviews").select(
            "review_id, content, moderation_status, created_at"
        ).eq("trainer_id", trainer_id).eq("moderation_status", "APPROVED").execute()
        payload["reviews"] = reviews_res.data or []

        # Fetch average rating
        payload["average_rating"] = profile_data.get("average_rating")
        payload["rating_count"] = profile_data.get("rating_count", 0)

        return payload

    except Exception as e:
        print(f"Error fetching profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching profile data"
        )