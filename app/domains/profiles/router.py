from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.profiles.models import StudentProfileUpdate, get_current_user
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