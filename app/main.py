from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import Base, engine

from app.domains.user.router import router as user_router
from app.domains.question.router import router as question_router
from app.domains.submission.router import router as submission_router
from app.domains.leaderboard.router import router as leaderboard_router
from app.domains.professor_analytics.router import router as analytics_router
from app.domains.code_analysis.router import router as analysis_router

app = FastAPI(title="Buildor Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

from app.api.graph_api import router as graph_router

app.include_router(
    graph_router,
    prefix="/api/v1/graph",
    tags=["Graph Analysis"]
)

Base.metadata.create_all(bind=engine)

app.include_router(user_router)
app.include_router(question_router)
app.include_router(submission_router)
app.include_router(leaderboard_router)
app.include_router(analytics_router)
app.include_router(analysis_router)