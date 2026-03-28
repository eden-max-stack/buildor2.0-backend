from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi import security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
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