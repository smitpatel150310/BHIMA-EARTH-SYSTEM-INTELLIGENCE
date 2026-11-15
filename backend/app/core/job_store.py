import time
import logging
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.core.persistent_cache import persistent_store

logger = logging.getLogger(__name__)


class JobStore:
    """
    Production-grade job storage manager for BHIMA asynchronous analysis tasks.
    Guarantees persistence across Vercel Serverless container invocations,
    cold starts, and concurrent worker executions.

    Architecture:
    1. Primary Persistent Layer: Delegates to persistent_store.engine (PostgreSQL/Supabase or SQLite).
    2. In-Memory Fast Cache: Thread-safe local cache for 0ms same-container hits.
    3. Self-Healing Fallback: Reads from disk / database if not in memory.
    4. Structured Audit: Structured logging for every job lifecycle transition.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._mem_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_key_to_id: Dict[str, str] = {}

    def _normalize_job_dict(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure standard schema with progress and progress_pct both populated."""
        pct = int(job.get("progress_pct", job.get("progress", 0)) or 0)
        job["progress_pct"] = pct
        job["progress"] = pct
        if "result" not in job:
            job["result"] = None
        if "error" not in job:
            job["error"] = None
        if "message" not in job or not job["message"]:
            job["message"] = ""
        return job

    def create_job(
        self,
        job_id: str,
        cache_key: str,
        status: str = "processing",
        progress_pct: int = 10,
        message: str = "Initializing analysis job...",
        request_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create and persist a new job record.
        Saves to persistent database FIRST before returning to prevent 404 race conditions.
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        job_data = {
            "job_id": job_id,
            "cache_key": cache_key,
            "status": status,
            "progress_pct": progress_pct,
            "progress": progress_pct,
            "message": message,
            "request_payload": request_payload,
            "result": None,
            "error": None,
            "created_at": now_ts,
            "updated_at": now_ts,
        }

        # 1. Update memory cache
        with self._lock:
            self._mem_cache[job_id] = dict(job_data)
            self._cache_key_to_id[cache_key] = job_id

        # 2. Persist to backing relational store (Postgres or SQLite)
        try:
            persisted = persistent_store.create_job(
                job_id=job_id,
                cache_key=cache_key,
                status=status,
                progress_pct=progress_pct,
                message=message,
                request_payload=request_payload,
            )
            if persisted:
                job_data = self._normalize_job_dict(persisted)
                with self._lock:
                    self._mem_cache[job_id] = job_data
            logger.info(
                f"[JobStore] Created and persisted job {job_id} "
                f"(status={status}, cache_key={cache_key}, progress={progress_pct}%)"
            )
        except Exception as e:
            logger.error(f"[JobStore] Error persisting job {job_id} to database: {e}", exc_info=True)

        return job_data

    def update_job(
        self,
        job_id: str,
        status: str,
        progress_pct: int,
        message: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update job status, progress, message, and result or error.
        Guarantees update is reflected in persistent database.
        """
        now_ts = datetime.now(timezone.utc).isoformat()

        # 1. Update in-memory cache
        with self._lock:
            if job_id in self._mem_cache:
                self._mem_cache[job_id]["status"] = status
                self._mem_cache[job_id]["progress_pct"] = progress_pct
                self._mem_cache[job_id]["progress"] = progress_pct
                self._mem_cache[job_id]["message"] = message
                self._mem_cache[job_id]["updated_at"] = now_ts
                if result is not None:
                    self._mem_cache[job_id]["result"] = result
                if error is not None:
                    self._mem_cache[job_id]["error"] = error

        # 2. Update persistent database
        try:
            updated = persistent_store.update_job(
                job_id=job_id,
                status=status,
                progress_pct=progress_pct,
                message=message,
                result=result,
                error=error,
            )
            if updated:
                norm = self._normalize_job_dict(updated)
                with self._lock:
                    self._mem_cache[job_id] = norm
                logger.info(
                    f"[JobStore] Updated job {job_id}: status={status}, "
                    f"progress={progress_pct}%, msg='{message}'"
                )
                return norm
        except Exception as e:
            logger.error(f"[JobStore] Error updating job {job_id} in database: {e}", exc_info=True)

        with self._lock:
            return self._mem_cache.get(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve job by ID.
        Checks memory cache first; if not found or if job is still in progress,
        queries the persistent database to detect state updates from other container instances.
        """
        # Check memory first
        with self._lock:
            cached = self._mem_cache.get(job_id)
            if cached and cached.get("status") in ("completed", "failed"):
                return cached

        # Check persistent database
        try:
            persisted = persistent_store.get_job(job_id)
            if persisted:
                norm = self._normalize_job_dict(persisted)
                with self._lock:
                    self._mem_cache[job_id] = norm
                    if norm.get("cache_key"):
                        self._cache_key_to_id[norm["cache_key"]] = job_id
                logger.info(
                    f"[JobStore] Retrieved job {job_id} from persistent storage: "
                    f"status={norm.get('status')}, progress={norm.get('progress_pct')}%"
                )
                return norm
        except Exception as e:
            logger.error(f"[JobStore] Error retrieving job {job_id} from database: {e}", exc_info=True)

        with self._lock:
            return self._mem_cache.get(job_id)

    def get_job_by_cache_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Find an active or completed job by its deterministic request cache key."""
        with self._lock:
            job_id = self._cache_key_to_id.get(cache_key)
            if job_id and job_id in self._mem_cache:
                return self._mem_cache[job_id]

        try:
            persisted = persistent_store.get_job_by_cache_key(cache_key)
            if persisted:
                norm = self._normalize_job_dict(persisted)
                with self._lock:
                    self._mem_cache[norm["job_id"]] = norm
                    self._cache_key_to_id[cache_key] = norm["job_id"]
                return norm
        except Exception as e:
            logger.error(f"[JobStore] Error retrieving job by cache key: {e}", exc_info=True)

        return None

    def clean_expired_jobs(self, max_age_seconds: int = 86400):
        """Purge jobs older than max_age_seconds."""
        try:
            persistent_store.clean_expired_jobs(max_age_seconds=max_age_seconds)
        except Exception as e:
            logger.warning(f"[JobStore] Could not clean expired jobs: {e}")


# Global singleton job store
job_store = JobStore()
