from datetime import datetime

from pydantic import BaseModel
from typing import List, Optional, Any

# --- Sub-models for Questions ---
class TestCaseCreate(BaseModel):
    input: str
    expectedOutput: str
    isSample: bool

class McqOptionCreate(BaseModel):
    text: str
    isCorrect: bool

class QuestionCreate(BaseModel):
    title: str
    type: str
    description: str
    difficulty: str
    tags: str
    optimalSolution: Optional[str] = None
    constraints: Optional[str] = None
    testCases: Optional[List[TestCaseCreate]] = []
    options: Optional[List[McqOptionCreate]] = []

# --- Sub-models for Materials ---
class MaterialCreate(BaseModel):
    title: str
    type: str
    content_url: Optional[str] = None
    order_index: int

# --- Sub-models for Phases ---
class PhaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int
    materials: List[MaterialCreate] = []
    questions: List[QuestionCreate] = []

# --- The Master Payload ---
class ClassCreatePayload(BaseModel):
    title: str
    description: Optional[str] = None
    phases: List[PhaseCreate] = []

class ClassResponse(BaseModel):
    title: str
    description: str
    created_at: str
    trainer_id: str
    org_id: str
    class_id: str
    phases_count: int
    students_count: int

# --- Pydantic Models for the new routes ---
class MaterialUpdatePayload(BaseModel):
    title: Optional[str] = None
    content_url: Optional[str] = None
    order_index: Optional[int] = None


class PhaseUpdatePayload(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None

class MaterialAddPayload(BaseModel):
    type: str
    title: str
    content_url: Optional[str] = ""
    order_index: int

class ClassUpdatePayload(BaseModel):
    title: str
    description: Optional[str] = ""

class QuestionUpdatePayload(BaseModel):
    title: str
    description: Optional[str] = ""
    difficulty: Optional[str] = "Medium"
    optimal_solution: Optional[str] = ""
    constraints: Optional[str] = ""
    testCases: Optional[List[TestCaseCreate]] = []
    options: Optional[List[McqOptionCreate]] = []
    type: str
    points: int

class QuizQuestionsUpdatePayload(BaseModel):
    question_ids: list[str]

class QuizCreatePayload(BaseModel):
    title: str

class QuizQuestionAddPayload(BaseModel):
    type: str # "MCQ" or "DSA"
    title: str