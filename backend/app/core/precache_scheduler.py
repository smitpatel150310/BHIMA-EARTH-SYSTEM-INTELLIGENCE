import os
import time
import uuid
import sqlite3
import logging
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "bhima_observations.db")
)

# Standard presets matching frontend
PRESET_REGIONS = {
    "Gujarat, India": {"min_lon": 68.1, "max_lon": 74.5, "min_lat": 20.1, "max_lat": 24.7},
    "California, USA": {"min_lon": -124.5, "max_lon": -114.1, "min_lat": 32.5, "max_lat": 42.0},
    "Amazon Basin": {"min_lon": -73.0, "max_lon": -50.0, "min_lat": -15.0, "max_lat": 5.0},
    "Sahel (West Africa)": {"min_lon": -15.0, "max_lon": 40.0, "min_lat": 10.0, "max_lat": 20.0},
    "Murray-Darling Basin": {"min_lon": 138.0, "max_lon": 149.0, "min_lat": -37.0, "max_lat": -24.0},
}


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_precache_table():
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS precache_jobs (
                job_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                region_name TEXT NOT NULL,
                region_key TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED',
                total_items INTEGER DEFAULT 0,
                completed_items INTEGER DEFAULT 0,
                current_item TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
    finally:
        conn.close()


class PrecacheScheduler:
    def __init__(self):
        init_precache_table()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def get_region_key(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
        return f"{float(min_lon):.2f}_{float(min_lat):.2f}_{float(max_lon):.2f}_{float(max_lat):.2f}"

    def queue_job(
        self,
        dataset_id: str,
        region_name: str,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        start_date: str,
        end_date: str,
    ) -> str:
        job_id = str(uuid.uuid4())[:8]
        region_key = self.get_region_key(min_lon, min_lat, max_lon, max_lat)
        months = pd.date_range(start=start_date, end=end_date, freq="MS")
        total_items = len(months)

        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO precache_jobs (
                        job_id, dataset_id, region_name, region_key,
                        start_date, end_date, status, total_items, completed_items
                    ) VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', ?, 0)
                    """,
                    (job_id, dataset_id, region_name, region_key, start_date, end_date, total_items),
                )
        finally:
            conn.close()

        self._ensure_worker_running()
        return job_id

    def list_jobs(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM precache_jobs ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM precache_jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def _update_job_status(
        self,
        job_id: str,
        status: str,
        completed_items: Optional[int] = None,
        current_item: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        conn = get_db_connection()
        try:
            with conn:
                updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
                params: List[Any] = [status]
                if completed_items is not None:
                    updates.append("completed_items = ?")
                    params.append(completed_items)
                if current_item is not None:
                    updates.append("current_item = ?")
                    params.append(current_item)
                if error_message is not None:
                    updates.append("error_message = ?")
                    params.append(error_message)
                params.append(job_id)
                conn.execute(f"UPDATE precache_jobs SET {', '.join(updates)} WHERE job_id = ?", params)
        finally:
            conn.close()

    def _ensure_worker_running(self):
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._stop_event.clear()
                self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self._worker_thread.start()

    def _worker_loop(self):
        logger.info("Precache background worker loop started.")
        while not self._stop_event.is_set():
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM precache_jobs WHERE status = 'QUEUED' ORDER BY created_at ASC LIMIT 1")
                row = cur.fetchone()
            finally:
                conn.close()

            if not row:
                # No queued jobs, sleep briefly
                time.sleep(2.0)
                continue

            job = dict(row)
            job_id = job["job_id"]
            logger.info(f"Starting precache job {job_id} for {job['dataset_id']} ({job['region_name']})")
            self._update_job_status(job_id, "RUNNING")

            try:
                # Execute retrieval via NASADataAccessor
                from app.core.data_access import NASADataAccessor
                parts = job["region_key"].split("_")
                min_lon, min_lat, max_lon, max_lat = map(float, parts)

                accessor = NASADataAccessor()
                df, notes, prov, src = accessor.get_timeseries_data(
                    dataset_id=job["dataset_id"],
                    min_lon=min_lon,
                    max_lon=max_lon,
                    min_lat=min_lat,
                    max_lat=max_lat,
                    start_date=job["start_date"],
                    end_date=job["end_date"],
                )
                completed_count = len(df)
                self._update_job_status(
                    job_id,
                    "COMPLETED",
                    completed_items=completed_count,
                    current_item="Done",
                )
                logger.info(f"Precache job {job_id} completed successfully ({completed_count} items cached).")
            except Exception as e:
                logger.error(f"Precache job {job_id} failed: {e}", exc_info=True)
                self._update_job_status(job_id, "FAILED", error_message=str(e))

        logger.info("Precache background worker loop stopped.")


precache_engine = PrecacheScheduler()
