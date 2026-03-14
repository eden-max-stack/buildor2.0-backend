from pydantic import BaseModel

class QuestionCreate(BaseModel):
    title: str
    difficulty: str
    description: str

class QuestionResponse(QuestionCreate):
    id: int

    class Config:
        from_attributes = True