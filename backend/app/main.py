import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, datasets, analysis, agent
from app.config import get_settings
from app.core.persistent_cache import init_persistent_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bhima")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure SQLite tables exist and WAL mode is active
    logger.info(f"Starting {settings.app_name} v{settings.app_version} [{settings.environment}]")
    try:
        init_persistent_store()
        logger.info("Persistent observation store verified successfully.")
    except Exception as e:
        logger.warning(f"Note during persistent store initialization: {e}")
    yield
    # Shutdown
    logger.info("BHIMA service shutting down cleanly.")


app = FastAPI(
    title="BHIMA Earth System Intelligence API",
    description="NASA Space Apps Challenge - Earth System Trend Detective",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Dynamic CORS configured from settings / environment variables
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(datasets.router)
app.include_router(analysis.router)
app.include_router(agent.router)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "storage_backend": settings.storage_backend,
        "docs": "/docs",
        "health": "/health",
    }
