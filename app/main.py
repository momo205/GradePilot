from app.routers.auth import router as auth_router
from app.routers.classes import router as classes_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

app = FastAPI(title="GradePilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(classes_router)


@app.get("/health", tags=["system"])
async def health() -> Dict[str, str]:
    """Simple health check endpoint used by tests and monitoring."""
    return {"status": "ok"}


@app.get("/", tags=["system"])
async def root() -> Dict[str, str]:
    """Placeholder root endpoint."""
    return {"message": "GradePilot API"}
