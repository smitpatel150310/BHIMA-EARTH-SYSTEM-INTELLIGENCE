"""
Vercel Serverless Function entry point for BHIMA (monorepo root deployment).
Exposes the existing FastAPI application instance without route duplication.
"""
import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
if os.path.exists(backend_dir) and backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault("ENVIRONMENT", "production")

from app.main import app
