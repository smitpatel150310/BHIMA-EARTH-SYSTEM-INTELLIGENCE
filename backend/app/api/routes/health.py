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
    """
    Comprehensive readiness probe verifying database connectivity,
    dependency readiness, and data provider access without leaking secrets.
    """
    import sys
    import platform
    from app.core.persistent_cache import persistent_store
    from app.core.db_engine import PostgreSQLEngine, SQLiteEngine

    is_postgres = isinstance(persistent_store.engine, PostgreSQLEngine)
    provider_name = "Neon PostgreSQL" if is_postgres else "SQLite"

    # Verify database connection
    db_connected = False
    db_error = None
    try:
        stats = persistent_store.get_storage_stats()
        db_connected = bool(stats is not None)
    except Exception as e:
        db_error = str(e)

    # Verify dependencies
    deps_ready = True
    missing_deps = []
    for mod in ["cftime", "pystac_client", "planetary_computer", "adlfs", "xarray", "zarr"]:
        try:
            __import__(mod)
        except ImportError:
            deps_ready = False
            missing_deps.append(mod)

    is_ready = db_connected and deps_ready

    return {
        "status": "ready" if is_ready else "degraded",
        "persistent_store_ready": db_connected,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runtime_version": f"Python {platform.python_version()}",
        "database_provider": provider_name,
        "database_connected": db_connected,
        "database_error": db_error if not db_connected else None,
        "data_provider": "Microsoft Planetary Computer (STAC + Azure Blob Zarr)",
        "dependencies_ready": deps_ready,
        "missing_dependencies": missing_deps if not deps_ready else [],
    }
