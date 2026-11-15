import os
from functools import lru_cache
from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Automatically load environment from current directory or backend/.env
load_dotenv()
_backend_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", ".env")
if os.path.exists(_backend_env):
    load_dotenv(_backend_env)


class Settings(BaseSettings):
    app_name: str = "BHIMA Earth System Intelligence"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Server binding (Cloud Run uses PORT environment variable)
    host: str = "0.0.0.0"
    port: int = 8080

    # Storage Architecture (Local filesystem vs Vercel Blob vs S3 vs GCS)
    storage_backend: str = "local"  # "local" | "vercel_blob" | "s3" | "gcs"
    blob_read_write_token: str = "" # Vercel Blob token (BLOB_READ_WRITE_TOKEN)
    s3_bucket: str = ""             # S3 / Cloudflare R2 bucket name
    s3_endpoint_url: str = ""       # Custom S3 endpoint URL (e.g. for Cloudflare R2)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    bhima_gcs_bucket: str = ""      # Legacy GCP bucket if configured
    gcp_project_id: str = ""

    # NASA Earthdata credentials (optional, for direct GES DISC fallback)
    nasa_earthdata_username: str = ""
    nasa_earthdata_password: str = ""

    # Gemini AI
    gemini_api_key: str = ""

    # Cache & Processing
    cache_ttl_seconds: int = 3600
    api_timeout_seconds: int = 300

    # CORS configuration (supports local dev and all Vercel preview/production domains)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080,https://*.vercel.app,*"

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    # Read PORT from environment if provided by Cloud Run
    port_env = os.environ.get("PORT")
    if port_env and port_env.isdigit():
        return Settings(port=int(port_env))
    return Settings()
