from fastapi import FastAPI

app = FastAPI()

from app.api.graph_analysis import router as graph_router

app.include_router(
    graph_router,
    prefix="/api/v1/graph",
    tags=["Graph Analysis"]
)
