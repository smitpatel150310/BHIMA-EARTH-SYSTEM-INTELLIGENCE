import os
import time
import hashlib
import sqlite3
import threading
import logging
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime, timezone
import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data")
)
DB_PATH = os.path.join(CACHE_DIR, "bhima_observations.db")
PARQUET_DIR = os.path.join(CACHE_DIR, "raw_parquet")

PROCESSING_VERSION = "v1.2.0"

# In-flight request lock registry to deduplicate simultaneous requests
_inflight_locks: Dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()


def get_inflight_lock(cache_key: str) -> threading.Lock:
    with _registry_lock:
        if cache_key not in _inflight_locks:
            _inflight_locks[cache_key] = threading.Lock()
        return _inflight_locks[cache_key]


def get_effective_db_path() -> str:
    """
    Determine the active SQLite database path.
    On Vercel Serverless (where the root container filesystem is read-only),
    we automatically seed the bundled database into /tmp/bhima_observations.db
    so SQLite can execute queries, locks, and temporary journals without permission errors.
    In local development, uses workspace data/bhima_observations.db directly.
    """
    if os.environ.get("VERCEL"):
        tmp_db = "/tmp/bhima_observations.db"
        if not os.path.exists(tmp_db) or os.path.getsize(tmp_db) < 1024:
            candidates = [
                DB_PATH,
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "bhima_observations.db")),
                os.path.abspath(os.path.join(os.getcwd(), "backend", "data", "bhima_observations.db")),
                os.path.abspath(os.path.join(os.getcwd(), "data", "bhima_observations.db")),
            ]
            for cand in candidates:
                if os.path.exists(cand) and os.path.getsize(cand) > 1024:
                    try:
                        import shutil
                        os.makedirs("/tmp", exist_ok=True)
                        shutil.copy2(cand, tmp_db)
                        logger.info(f"Vercel Serverless: Seeded /tmp database from {cand} ({os.path.getsize(tmp_db)/1024:.1f} KB)")
                        break
                    except Exception as e:
                        logger.warning(f"Could not copy seed database to /tmp: {e}")
        return tmp_db
    return DB_PATH


def get_db_connection() -> sqlite3.Connection:
    effective_path = get_effective_db_path()
    os.makedirs(os.path.dirname(effective_path), exist_ok=True)
    if not os.environ.get("VERCEL"):
        os.makedirs(PARQUET_DIR, exist_ok=True)
    conn = sqlite3.connect(effective_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_persistent_store():
    """Initialize schema for metadata, monthly aggregates, annual aggregates, and raw parquet index."""
    conn = get_db_connection()
    try:
        with conn:
            # Check existing columns in regional_monthly
            existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(regional_monthly)").fetchall()}
            if existing_cols:
                col_defs = {
                    "variable": "TEXT NOT NULL DEFAULT 'precipitationCal'",
                    "aggregation_method": "TEXT NOT NULL DEFAULT 'FULL_30MIN_INTEGRAL'",
                    "processing_version": "TEXT NOT NULL DEFAULT 'v1.2.0'",
                    "units": "TEXT DEFAULT 'mm/month'",
                    "n_observations": "INTEGER DEFAULT 0",
                    "n_missing": "INTEGER DEFAULT 0",
                    "fetch_time_ms": "REAL DEFAULT 0.0",
                    "downloaded_bytes": "INTEGER DEFAULT 0",
                }
                for col_name, col_type in col_defs.items():
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE regional_monthly ADD COLUMN {col_name} {col_type}")
            else:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS regional_monthly (
                    dataset_id TEXT NOT NULL,
                    region_key TEXT NOT NULL,
                    date TEXT NOT NULL,
                    variable TEXT NOT NULL DEFAULT 'precipitationCal',
                    aggregation_method TEXT NOT NULL DEFAULT 'FULL_30MIN_INTEGRAL',
                    processing_version TEXT NOT NULL DEFAULT 'v1.2.0',
                    value REAL,
                    units TEXT DEFAULT 'mm/month',
                    valid_pixels INTEGER,
                    coverage_fraction REAL,
                    n_observations INTEGER DEFAULT 0,
                    n_missing INTEGER DEFAULT 0,
                    fetch_time_ms REAL DEFAULT 0.0,
                    downloaded_bytes INTEGER DEFAULT 0,
                    data_provenance TEXT NOT NULL DEFAULT 'REAL_NASA_DATA',
                    data_source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (dataset_id, region_key, date, variable, aggregation_method, processing_version)
                )
                """)

            # Annual aggregated datasets
            conn.execute("""
            CREATE TABLE IF NOT EXISTS regional_annual (
                dataset_id TEXT NOT NULL,
                region_key TEXT NOT NULL,
                year INTEGER NOT NULL,
                variable TEXT NOT NULL DEFAULT 'precipitationCal',
                processing_version TEXT NOT NULL DEFAULT 'v1.2.0',
                annual_mean REAL,
                annual_sum REAL,
                n_months INTEGER,
                std_dev REAL,
                cv REAL,
                data_provenance TEXT NOT NULL DEFAULT 'REAL_NASA_DATA',
                data_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (dataset_id, region_key, year, variable, processing_version)
            )
            """)

            # High-resolution daily observations
            conn.execute("""
            CREATE TABLE IF NOT EXISTS regional_daily (
                dataset_id TEXT NOT NULL,
                region_key TEXT NOT NULL,
                date TEXT NOT NULL,
                variable TEXT NOT NULL DEFAULT 'precipitationCal',
                mean_rate_mm_hr REAL,
                accum_mm REAL,
                valid_steps INTEGER DEFAULT 48,
                missing_steps INTEGER DEFAULT 0,
                data_provenance TEXT NOT NULL DEFAULT 'REAL_NASA_DATA',
                data_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (dataset_id, region_key, date, variable)
            )
            """)

            # Raw observation Parquet partition index
            conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_parquet_index (
                partition_key TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                region_key TEXT NOT NULL,
                year INTEGER NOT NULL,
                variable TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER,
                record_count INTEGER,
                min_timestamp TEXT,
                max_timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_monthly_lookup
            ON regional_monthly (dataset_id, region_key, date, variable)
            """)
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_annual_lookup
            ON regional_annual (dataset_id, region_key, year, variable)
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_jobs (
                job_id TEXT PRIMARY KEY,
                cache_key TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                progress_pct INTEGER DEFAULT 0,
                message TEXT,
                request_payload TEXT,
                result TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_cache_key ON analysis_jobs (cache_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON analysis_jobs (status)")
    finally:
        conn.close()


def get_region_key(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    """Deterministic string key for spatial bounding box formatted to 2 decimal places."""
    return f"{float(min_lon):.2f}_{float(min_lat):.2f}_{float(max_lon):.2f}_{float(max_lat):.2f}"


def generate_cache_key(
    dataset_id: str,
    variable: str,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    start_date: str,
    end_date: str,
    resolution: str = "monthly",
    version: str = PROCESSING_VERSION,
) -> str:
    """Deterministic hash key uniquely identifying the data request."""
    key_str = (
        f"{dataset_id}:{variable}:{min_lon:.2f}_{min_lat:.2f}_{max_lon:.2f}_{max_lat:.2f}:"
        f"{start_date}:{end_date}:{resolution}:{version}"
    )
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()[:16]


class PersistentObservationStore:
    """
    Production-grade persistent observation store.
    - Manages SQLite database for metadata, monthly and annual aggregates.
    - Manages compressed Parquet storage for high-resolution raw observations.
    - Deduplicates concurrent in-flight requests.
    - Transparently reports cache hit/miss, duration, storage size, and provenance.
    """

    def __init__(self):
        self.db_path = get_effective_db_path()
        self.parquet_dir = PARQUET_DIR
        init_persistent_store()
        from app.core.db_engine import create_database_engine
        self.engine = create_database_engine(self.db_path, self.parquet_dir)

    def get_monthly_series(
        self,
        dataset_id: str,
        region_key: str,
        start_date: str,
        end_date: str,
        variable: str = "precipitationCal",
    ) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
        """
        Query monthly observations.
        Delegates to active database engine (SQLite or PostgreSQL).
        Returns:
            (cached_records, missing_month_strs, audit_dict)
        """
        return self.engine.get_monthly_series(
            dataset_id=dataset_id,
            region_key=region_key,
            start_date=start_date,
            end_date=end_date,
            variable=variable,
        )

    def persist_monthly_series(
        self,
        dataset_id: str,
        region_key: str,
        records: List[Dict[str, Any]],
        variable: str = "precipitationCal",
        aggregation_method: str = "FULL_30MIN_INTEGRAL",
        data_provenance: str = "REAL_NASA_DATA",
        data_source: str = "Microsoft Planetary Computer",
        units: str = "mm/month",
    ):
        """Persist processed monthly records to active database engine."""
        return self.engine.persist_monthly_series(
            dataset_id=dataset_id,
            region_key=region_key,
            records=records,
            variable=variable,
            aggregation_method=aggregation_method,
            data_provenance=data_provenance,
            data_source=data_source,
            units=units,
        )

    def persist_annual_series(
        self,
        dataset_id: str,
        region_key: str,
        annual_records: List[Dict[str, Any]],
        variable: str = "precipitationCal",
        data_provenance: str = "REAL_NASA_DATA",
        data_source: str = "Microsoft Planetary Computer",
    ):
        """Persist aggregated annual data to active database engine."""
        return self.engine.persist_annual_series(
            dataset_id=dataset_id,
            region_key=region_key,
            annual_records=annual_records,
            variable=variable,
            data_provenance=data_provenance,
            data_source=data_source,
        )

    def persist_raw_observations_parquet(
        self,
        dataset_id: str,
        region_key: str,
        year: int,
        variable: str,
        df_raw: pd.DataFrame,
    ) -> str:
        """
        Store raw, high-resolution observations (e.g. 30-min GPM observations)
        into compressed Parquet partitioned by dataset/variable/region_key/year.parquet.
        """
        partition_dir = os.path.join(PARQUET_DIR, dataset_id, variable, region_key)
        os.makedirs(partition_dir, exist_ok=True)
        file_path = os.path.join(partition_dir, f"{year}.parquet")

        # Write compressed parquet using pyarrow
        df_raw.to_parquet(file_path, engine="pyarrow", compression="snappy", index=False)

        file_size = os.path.getsize(file_path)
        min_ts = str(df_raw["timestamp"].min()) if "timestamp" in df_raw.columns else ""
        max_ts = str(df_raw["timestamp"].max()) if "timestamp" in df_raw.columns else ""
        part_key = f"{dataset_id}:{variable}:{region_key}:{year}"

        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO raw_parquet_index (
                        partition_key, dataset_id, region_key, year, variable,
                        file_path, file_size_bytes, record_count, min_timestamp, max_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        part_key,
                        dataset_id,
                        region_key,
                        year,
                        variable,
                        file_path,
                        file_size,
                        len(df_raw),
                        min_ts,
                        max_ts,
                    ),
                )
        finally:
            conn.close()

        logger.info(f"Persisted {len(df_raw)} raw observations to Parquet: {file_path} ({file_size / 1024:.1f} KB)")
        return file_path

    def get_storage_stats(self) -> Dict[str, Any]:
        """Report storage consumption and cache metrics from active database engine."""
        return self.engine.get_storage_stats()

    def get_cache_summary(self) -> Dict[str, Any]:
        """
        Detailed audit of cached datasets and regions for Part 7.
        Reports cached month counts, target completeness (72 months),
        last extraction timestamps, and storage sizes from active engine.
        """
        return self.engine.get_cache_summary()

    def create_job(
        self,
        job_id: str,
        cache_key: str,
        status: str = "queued",
        progress_pct: int = 0,
        message: str = "",
        request_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create and persist an analysis job."""
        return self.engine.create_job(
            job_id=job_id,
            cache_key=cache_key,
            status=status,
            progress_pct=progress_pct,
            message=message,
            request_payload=request_payload,
        )

    def update_job(
        self,
        job_id: str,
        status: str,
        progress_pct: int,
        message: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update job progress and result or error."""
        return self.engine.update_job(
            job_id=job_id,
            status=status,
            progress_pct=progress_pct,
            message=message,
            result=result,
            error=error,
        )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job record by job_id."""
        return self.engine.get_job(job_id=job_id)

    def get_job_by_cache_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve active job by cache_key."""
        return self.engine.get_job_by_cache_key(cache_key=cache_key)

    def clean_expired_jobs(self, max_age_seconds: int = 86400):
        """Purge jobs older than max_age_seconds."""
        return self.engine.clean_expired_jobs(max_age_seconds=max_age_seconds)


# Global singleton instance
persistent_store = PersistentObservationStore()
