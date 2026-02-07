from fastapi import APIRouter
from .schemas import UserCreate, UserResponse
from .service import UserService
from typing import List

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate):
    return UserService().create_user(user)

@router.get("/", response_model=List[UserResponse])
def list_users():
    return UserService().list_users()
