from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import Base, engine, get_database_url_redacted
import time

from app.domains.user.router import router as user_router
from app.domains.question.router import router as question_router
from app.domains.submission.router import router as submission_router
from app.domains.leaderboard.router import router as leaderboard_router
from app.domains.professor_analytics.router import router as analytics_router
from app.domains.code_analysis.router import router as analysis_router
from app.domains.class_questions.router import router as class_questions_router
from app.domains.user_profile.router import router as user_profile_router
from app.domains.profiles.router import router as profile_router

app = FastAPI(title="Buildor Backend")

@app.on_event("startup")
def _startup_debug_db():
    try:
        url = get_database_url_redacted()
        dialect = str(getattr(getattr(engine, "url", None), "drivername", ""))
        print(f"[db] dialect={dialect} url={url}")
    except Exception:
        pass

@app.get("/debug/env")
def debug_env():
    return {
        "database_url": get_database_url_redacted(),
        "database_dialect": str(getattr(getattr(engine, "url", None), "drivername", "")),
    }

@app.middleware("http")
async def _request_timing(request: Request, call_next):
    start = time.perf_counter()
    try:
        response: Response = await call_next(request)
        return response
    finally:
        dur_ms = (time.perf_counter() - start) * 1000
        status = getattr(locals().get("response", None), "status_code", "-")
        print(f"[req] {request.method} {request.url.path} -> {status} ({dur_ms:.1f}ms)")

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

if str(getattr(getattr(engine, "url", None), "drivername", "")).startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

app.include_router(user_router)
app.include_router(question_router)
app.include_router(submission_router)
app.include_router(leaderboard_router)
app.include_router(analytics_router)
app.include_router(analysis_router)
app.include_router(class_questions_router)
# app.include_router(user_profile_router)
app.include_router(profile_router)