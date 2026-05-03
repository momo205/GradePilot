from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.classes import router as classes_router
from app.routers.integrations_google import router as google_integrations_router
from app.routers.rag import router as rag_router
from app.routers.settings import router as settings_router
from app.routers.summarise import router as summarise_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Dict

app = FastAPI(title="GradePilot API")

cors_allow_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "")
cors_allow_origin_regex_env = os.getenv("CORS_ALLOW_ORIGIN_REGEX", "")

_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
]

_origins = (
    [o.strip() for o in cors_allow_origins_env.split(",") if o.strip()]
    if cors_allow_origins_env.strip() != ""
    else _default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=(
        cors_allow_origin_regex_env if cors_allow_origin_regex_env else None
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(classes_router)
app.include_router(google_integrations_router)
app.include_router(rag_router)
app.include_router(settings_router)
app.include_router(summarise_router)


@app.get("/health", tags=["system"])
async def health() -> Dict[str, str]:
    """Simple health check endpoint used by tests and monitoring."""
    return {"status": "ok"}


@app.get("/", tags=["system"])
async def root() -> Dict[str, str]:
    """Placeholder root endpoint."""
    return {"message": "GradePilot API"}
