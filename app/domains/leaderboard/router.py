from fastapi import APIRouter

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

@router.get("/")
def get_leaderboard():
    return [
        {"user": "Alice", "score": 120},
        {"user": "Bob", "score": 100}
    ]
