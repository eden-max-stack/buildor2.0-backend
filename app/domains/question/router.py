from fastapi import APIRouter
from .schemas import QuestionCreate, QuestionResponse
from typing import List

router = APIRouter(prefix="/questions", tags=["Questions"])

questions_db = []

@router.post("/", response_model=QuestionResponse)
def create_question(q: QuestionCreate):
    new_q = q.dict()
    new_q["id"] = len(questions_db) + 1
    questions_db.append(new_q)
    return new_q

@router.get("/", response_model=List[QuestionResponse])
def list_questions():
    return questions_db
