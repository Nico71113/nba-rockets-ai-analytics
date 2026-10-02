from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.analytics import router as analytics_router
from backend.app.api.coverage import router as coverage_router
from backend.app.api.health import router as health_router
from backend.app.api.query import router as query_router
from backend.app.config import get_settings

settings = get_settings()
app = FastAPI(
    title="NBA Rockets AI Analytics",
    version="0.1.0",
    description="Evidence-grounded analytics for the 2025-26 NBA season.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(coverage_router)
app.include_router(analytics_router)
app.include_router(query_router)
