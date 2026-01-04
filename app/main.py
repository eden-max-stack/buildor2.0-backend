from fastapi import FastAPI

app = FastAPI(title="Buildor Backend")

from app.api.graph import router as graph_router

app.include_router(
    graph_router,
    prefix="/api/v1/graph",
    tags=["Graph Analysis"]
)
