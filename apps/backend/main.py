"""SimForge Backend — FastAPI orchestration server."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import init_db
from app.db.seed import seed_database
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init DB and seed data."""
    init_db()
    if settings.ENABLE_DEMO_SEED:
        seed_database()
    # Create storage directory
    os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
    yield


app = FastAPI(
    title="SimForge API",
    description="Orchestration backend for warehouse edge-case simulation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for artifact serving
storage_root = Path(settings.STORAGE_ROOT)
storage_root.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_root)), name="storage")

app.include_router(api_router, prefix="/api")
