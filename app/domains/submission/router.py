from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/submissions", tags=["Submissions"])

class Submission(BaseModel):
    user_id: int
    question_id: int
    code: str
    status: str

submissions_db = []

@router.post("/")
def submit_code(sub: Submission):
    submissions_db.append(sub.dict())
    return {"message": "Submission received"}
