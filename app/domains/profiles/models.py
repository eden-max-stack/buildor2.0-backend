from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi import security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from app.infrastructure.supabase_client import supabase

security = HTTPBearer()

class StudentProfileUpdate(BaseModel):
    university: Optional[str] = None
    degree: Optional[str] = None
    expected_grad_year: Optional[int] = None
    gpa: Optional[float] = None
    bio: Optional[str] = None
    portfolio_md: Optional[str] = None
    github_url: Optional[str] = None # Or use HttpUrl if you want strict URL validation

class TrainerProfileUpdate(BaseModel):
    title: Optional[str] = None
    workplace: Optional[str] = None

class TrainerAttestationCreate(BaseModel):
    """
    Model for creating a new trainer attestation.
    Note: trainer_id is omitted here because it is securely extracted 
    from the current_user token in the router.
    """
    title: str = Field(..., description="The title of the attestation/certification")
    description: Optional[str] = Field(None, description="Optional description of the attestation")
    attachment_url: Optional[str] = Field(None, description="Optional URL to the certificate or proof")

class TrainerRatingCreate(BaseModel):
    """
    Model for a student/user rating a trainer.
    Includes validation to ensure the rating stays between 0 and 5,
    matching your endpoint's manual check.
    """
    trainer_id: str = Field(..., description="The UUID of the trainer being rated")
    rating: float = Field(..., ge=0, le=5, description="A rating between 0 and 5")

class TrainerReviewCreate(BaseModel):
    """
    Model for submitting an anonymous review for a trainer.
    Note: reviewer_id and moderation_status are handled securely 
    by the backend router.
    """
    trainer_id: str = Field(..., description="The UUID of the trainer being reviewed")
    class_id: str = Field(..., description="The UUID of the class this review is associated with")
    content: str = Field(..., min_length=1, description="The text content of the review")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifies the JWT token with Supabase and returns the user object."""
    token = credentials.credentials
    try:
        # Get user securely using the JWT token
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
            raise ValueError("User not found")
        return auth_response.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired session token: {str(e)}"
        )