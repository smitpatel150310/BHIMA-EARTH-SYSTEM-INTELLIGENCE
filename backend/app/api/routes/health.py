import os
from fastapi import APIRouter
from datetime import datetime, timezone
from app.config import get_settings

router = APIRouter()


@router.get("/health")
@router.get("/healthz")
async def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/readiness")
async def readiness_check():
    """Cloud Run container readiness probe."""
    from app.core.persistent_cache import persistent_store
    db_exists = os.path.exists(persistent_store.db_path)
    return {
        "status": "ready" if db_exists else "initializing",
        "persistent_store_ready": db_exists,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
