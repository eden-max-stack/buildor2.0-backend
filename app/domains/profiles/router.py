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