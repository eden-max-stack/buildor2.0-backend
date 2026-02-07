from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["Professor Analytics"])

@router.get("/summary")
def get_summary():
    return {
        "total_students": 120,
        "avg_score": 75,
        "most_failed_question": 3
    }
