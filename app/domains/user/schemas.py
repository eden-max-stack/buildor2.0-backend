from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    role: str

class UserResponse(UserCreate):
    id: int

    class Config:
        from_attributes = True