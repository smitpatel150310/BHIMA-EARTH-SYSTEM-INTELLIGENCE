import os
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import pandas as pd

logger = logging.getLogger(__name__)

PROCESSING_VERSION = "v1.2.0"


class BaseDatabaseEngine(ABC):
    """Abstract interface for BHIMA observation cache database engine."""

    @abstractmethod
    def init_schema(self):
        """Initialize required relational tables and indices."""
        pass

    @abstractmethod
    def get_monthly_series(
        self,
        dataset_id: str,
        region_key: str,
        start_date: str,
        end_date: str,
        variable: str = "precipitationCal",
    ) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
        """Retrieve cached monthly observations and audit metrics."""
        pass

    @abstractmethod
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
        """Persist or upsert monthly observation records."""
        pass

    @abstractmethod
    def persist_annual_series(
        self,
        dataset_id: str,
        region_key: str,
        annual_records: List[Dict[str, Any]],
        variable: str = "precipitationCal",
        data_provenance: str = "REAL_NASA_DATA",
        data_source: str = "Microsoft Planetary Computer",
    ):
        """Persist or upsert annual aggregated records."""
        pass

    @abstractmethod
    def get_storage_stats(self) -> Dict[str, Any]:
        """Report storage volume and record counts."""
        pass

    @abstractmethod
    def get_cache_summary(self) -> Dict[str, Any]:
        """Report audit summary of all cached series."""
        pass

    @abstractmethod
    def create_job(
        self,
        job_id: str,
        cache_key: str,
        status: str = "queued",
        progress_pct: int = 0,
        message: str = "",
        request_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create and persist an analysis job record."""
        pass

    @abstractmethod
    def update_job(
        self,
        job_id: str,
        status: str,
        progress_pct: int,
        message: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update job status, progress, message, and result or error."""
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job record by job_id."""
        pass

    @abstractmethod
    def get_job_by_cache_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve active job by cache_key."""
        pass

    @abstractmethod
    def clean_expired_jobs(self, max_age_seconds: int = 86400):
        """Purge jobs older than max_age_seconds."""
        pass


class SQLiteEngine(BaseDatabaseEngine):
    """
    SQLite database engine for local development and bundled baseline storage.
    Automatically handles Vercel Serverless /tmp seeding.
    """

    def __init__(self, db_path: str, parquet_dir: str):
        self.db_path = db_path
        self.parquet_dir = parquet_dir
        self.init_schema()

    def _get_connection(self):
        import sqlite3
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        conn = self._get_connection()
        try:
            with conn:
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

                conn.execute("CREATE INDEX IF NOT EXISTS idx_monthly_lookup ON regional_monthly (dataset_id, region_key, date, variable)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_annual_lookup ON regional_annual (dataset_id, region_key, year, variable)")

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

    def get_monthly_series(
        self,
        dataset_id: str,
        region_key: str,
        start_date: str,
        end_date: str,
        variable: str = "precipitationCal",
    ) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
        months = pd.date_range(start=start_date, end=end_date, freq="MS")
        all_month_strs = [m.strftime("%Y-%m") for m in months]

        t0 = time.perf_counter()
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM regional_monthly
                WHERE dataset_id = ? AND region_key = ? AND date >= ? AND date <= ?
                  AND variable = ?
                ORDER BY date ASC, aggregation_method ASC
                """,
                (dataset_id, region_key, all_month_strs[0], all_month_strs[-1], variable),
            )
            rows = cur.fetchall()

            cached_map = {}
            for r in rows:
                m_date = r["date"]
                if m_date not in cached_map or r["aggregation_method"] == "FULL_30MIN_INTEGRAL":
                    cached_map[m_date] = dict(r)

            cached_records = []
            missing_months = []
            for m_str in all_month_strs:
                if m_str in cached_map:
                    cached_records.append(cached_map[m_str])
                else:
                    missing_months.append(m_str)

            lookup_ms = (time.perf_counter() - t0) * 1000.0

            if len(missing_months) == 0:
                cache_status = "HIT"
            elif len(cached_records) > 0:
                cache_status = "PARTIAL"
            else:
                cache_status = "MISS"

            audit = {
                "cache_status": cache_status,
                "cache_hit": cache_status == "HIT",
                "cached_months_count": len(cached_records),
                "missing_months_count": len(missing_months),
                "lookup_duration_ms": round(lookup_ms, 3),
                "storage_type": "SQLite (Indexed B-Tree)",
                "data_provenance": cached_records[0]["data_provenance"] if cached_records else "REAL_NASA_DATA",
                "data_source": cached_records[0]["data_source"] if cached_records else "Microsoft Planetary Computer",
            }
            return cached_records, missing_months, audit
        finally:
            conn.close()

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
        if not records:
            return
        conn = self._get_connection()
        try:
            with conn:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO regional_monthly (
                        dataset_id, region_key, date, variable, aggregation_method, processing_version,
                        value, units, valid_pixels, coverage_fraction, n_observations, n_missing,
                        fetch_time_ms, downloaded_bytes, data_provenance, data_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            dataset_id,
                            region_key,
                            r["date"],
                            variable,
                            aggregation_method,
                            PROCESSING_VERSION,
                            r.get("value"),
                            r.get("units", units),
                            r.get("valid_pixels", 0),
                            r.get("coverage_fraction", 0.0),
                            r.get("n_observations", 0),
                            r.get("n_missing", 0),
                            r.get("fetch_time_ms", 0.0),
                            r.get("downloaded_bytes", 0),
                            data_provenance,
                            data_source,
                        )
                        for r in records
                    ],
                )
        finally:
            conn.close()

    def persist_annual_series(
        self,
        dataset_id: str,
        region_key: str,
        annual_records: List[Dict[str, Any]],
        variable: str = "precipitationCal",
        data_provenance: str = "REAL_NASA_DATA",
        data_source: str = "Microsoft Planetary Computer",
    ):
        if not annual_records:
            return
        conn = self._get_connection()
        try:
            with conn:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO regional_annual (
                        dataset_id, region_key, year, variable, processing_version,
                        annual_mean, annual_sum, n_months, std_dev, cv,
                        data_provenance, data_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            dataset_id,
                            region_key,
                            int(a["year"]),
                            variable,
                            PROCESSING_VERSION,
                            a.get("annual_mean"),
                            a.get("annual_sum"),
                            a.get("n_months"),
                            a.get("std_dev"),
                            a.get("cv"),
                            data_provenance,
                            data_source,
                        )
                        for a in annual_records
                    ],
                )
        finally:
            conn.close()

    def get_storage_stats(self) -> Dict[str, Any]:
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        parquet_size = 0
        parquet_files = 0
        if os.path.exists(self.parquet_dir):
            for root, _, files in os.walk(self.parquet_dir):
                for f in files:
                    if f.endswith(".parquet"):
                        parquet_size += os.path.getsize(os.path.join(root, f))
                        parquet_files += 1

        conn = self._get_connection()
        try:
            m_count = conn.execute("SELECT count(*) FROM regional_monthly").fetchone()[0]
            a_count = conn.execute("SELECT count(*) FROM regional_annual").fetchone()[0]
            d_count = conn.execute("SELECT count(*) FROM regional_daily").fetchone()[0]
            raw_count = conn.execute("SELECT count(*) FROM raw_parquet_index").fetchone()[0]
        finally:
            conn.close()

        return {
            "engine": "sqlite",
            "sqlite_db_size_kb": round(db_size / 1024, 2),
            "parquet_storage_size_kb": round(parquet_size / 1024, 2),
            "total_storage_size_kb": round((db_size + parquet_size) / 1024, 2),
            "cached_monthly_records": m_count,
            "cached_annual_records": a_count,
            "cached_daily_records": d_count,
            "raw_parquet_partitions": raw_count,
            "processing_version": PROCESSING_VERSION,
        }

    def get_cache_summary(self) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            rows = conn.execute("""
                SELECT dataset_id, region_key, variable,
                       COUNT(*) as cached_months,
                       MIN(date) as min_date,
                       MAX(date) as max_date,
                       MAX(created_at) as last_updated
                FROM regional_monthly
                GROUP BY dataset_id, region_key, variable
                ORDER BY dataset_id, region_key
            """).fetchall()

            entries = []
            for r in rows:
                c_months = int(r["cached_months"])
                entries.append({
                    "dataset_id": r["dataset_id"],
                    "region_key": r["region_key"],
                    "variable": r["variable"],
                    "cached_months": c_months,
                    "target_period": "2015-01 to 2020-12 (72 months)",
                    "is_72_complete": c_months >= 72,
                    "min_date": r["min_date"],
                    "max_date": r["max_date"],
                    "last_updated": r["last_updated"],
                })

            stats = self.get_storage_stats()
            return {
                "status": "ok",
                "engine": "sqlite",
                "storage": stats,
                "cached_series_count": len(entries),
                "series": entries,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            conn.close()

    def create_job(
        self,
        job_id: str,
        cache_key: str,
        status: str = "queued",
        progress_pct: int = 0,
        message: str = "",
        request_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        import json
        payload_str = json.dumps(request_payload) if request_payload is not None else None
        now_ts = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO analysis_jobs (
                        job_id, cache_key, status, progress_pct, message,
                        request_payload, result, error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                    ON CONFLICT(job_id) DO UPDATE SET
                        status = excluded.status,
                        progress_pct = excluded.progress_pct,
                        message = excluded.message,
                        request_payload = excluded.request_payload,
                        updated_at = excluded.updated_at
                    """,
                    (job_id, cache_key, status, progress_pct, message, payload_str, now_ts, now_ts),
                )
            return {
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
        finally:
            conn.close()

    def update_job(
        self,
        job_id: str,
        status: str,
        progress_pct: int,
        message: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        import json
        now_ts = datetime.now(timezone.utc).isoformat()
        res_str = json.dumps(result, default=str) if result is not None else None
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE analysis_jobs
                    SET status = ?,
                        progress_pct = ?,
                        message = ?,
                        result = COALESCE(?, result),
                        error = COALESCE(?, error),
                        updated_at = ?
                    WHERE job_id = ?
                    """,
                    (status, progress_pct, message, res_str, error, now_ts, job_id),
                )
            return self.get_job(job_id)
        finally:
            conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        import json
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT job_id, cache_key, status, progress_pct, message,
                       request_payload, result, error, created_at, updated_at
                FROM analysis_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["progress"] = res.get("progress_pct", 0)
            if res.get("result"):
                try:
                    res["result"] = json.loads(res["result"])
                except Exception:
                    pass
            if res.get("request_payload"):
                try:
                    res["request_payload"] = json.loads(res["request_payload"])
                except Exception:
                    pass
            return res
        finally:
            conn.close()

    def get_job_by_cache_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        import json
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT job_id, cache_key, status, progress_pct, message,
                       request_payload, result, error, created_at, updated_at
                FROM analysis_jobs
                WHERE cache_key = ? AND status IN ('queued', 'processing', 'running', 'completed')
                ORDER BY created_at DESC LIMIT 1
                """,
                (cache_key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["progress"] = res.get("progress_pct", 0)
            if res.get("result"):
                try:
                    res["result"] = json.loads(res["result"])
                except Exception:
                    pass
            if res.get("request_payload"):
                try:
                    res["request_payload"] = json.loads(res["request_payload"])
                except Exception:
                    pass
            return res
        finally:
            conn.close()

    def clean_expired_jobs(self, max_age_seconds: int = 86400):
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    "DELETE FROM analysis_jobs WHERE datetime(created_at) < datetime('now', ?)",
                    (f"-{max_age_seconds} seconds",),
                )
        except Exception as e:
            logger.warning(f"Error cleaning expired SQLite jobs: {e}")
        finally:
            conn.close()


class PostgreSQLEngine(BaseDatabaseEngine):
    """
    Managed PostgreSQL database engine (Vercel Postgres, Neon, Supabase, AWS RDS).
    Guarantees cross-instance persistent writes and read replication across Vercel Functions.
    """

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self._driver = self._determine_driver()
        logger.info(f"PostgreSQLEngine initialized using driver '{self._driver}'")
        self.init_schema()

    def _determine_driver(self) -> str:
        try:
            import psycopg2
            return "psycopg2"
        except ImportError:
            try:
                import pg8000
                return "pg8000"
            except ImportError:
                raise ImportError("PostgreSQL engine requires psycopg2-binary or pg8000. Install via pip install psycopg2-binary pg8000")

    def _get_connection(self):
        # Normalize connection url
        url = self.connection_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        if self._driver == "psycopg2":
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(url, connect_timeout=10)
            return conn
        else:
            import pg8000.native
            # Parse url for pg8000
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            conn = pg8000.native.Connection(
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path.lstrip("/"),
                ssl_context=True,
                timeout=10,
            )
            return conn

    def init_schema(self):
        conn = self._get_connection()
        try:
            ddl = """
            CREATE TABLE IF NOT EXISTS regional_monthly (
                dataset_id VARCHAR(64) NOT NULL,
                region_key VARCHAR(64) NOT NULL,
                date VARCHAR(16) NOT NULL,
                variable VARCHAR(64) NOT NULL DEFAULT 'precipitationCal',
                aggregation_method VARCHAR(64) NOT NULL DEFAULT 'FULL_30MIN_INTEGRAL',
                processing_version VARCHAR(32) NOT NULL DEFAULT 'v1.2.0',
                value DOUBLE PRECISION,
                units VARCHAR(32) DEFAULT 'mm/month',
                valid_pixels INTEGER,
                coverage_fraction REAL,
                n_observations INTEGER DEFAULT 0,
                n_missing INTEGER DEFAULT 0,
                fetch_time_ms REAL DEFAULT 0.0,
                downloaded_bytes BIGINT DEFAULT 0,
                data_provenance VARCHAR(64) NOT NULL DEFAULT 'REAL_NASA_DATA',
                data_source TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (dataset_id, region_key, date, variable, aggregation_method, processing_version)
            );

            CREATE TABLE IF NOT EXISTS regional_annual (
                dataset_id VARCHAR(64) NOT NULL,
                region_key VARCHAR(64) NOT NULL,
                year INTEGER NOT NULL,
                variable VARCHAR(64) NOT NULL DEFAULT 'precipitationCal',
                processing_version VARCHAR(32) NOT NULL DEFAULT 'v1.2.0',
                annual_mean DOUBLE PRECISION,
                annual_sum DOUBLE PRECISION,
                n_months INTEGER,
                std_dev DOUBLE PRECISION,
                cv DOUBLE PRECISION,
                data_provenance VARCHAR(64) NOT NULL DEFAULT 'REAL_NASA_DATA',
                data_source TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (dataset_id, region_key, year, variable, processing_version)
            );

            CREATE TABLE IF NOT EXISTS regional_daily (
                dataset_id VARCHAR(64) NOT NULL,
                region_key VARCHAR(64) NOT NULL,
                date VARCHAR(16) NOT NULL,
                variable VARCHAR(64) NOT NULL DEFAULT 'precipitationCal',
                mean_rate_mm_hr DOUBLE PRECISION,
                accum_mm DOUBLE PRECISION,
                valid_steps INTEGER DEFAULT 48,
                missing_steps INTEGER DEFAULT 0,
                data_provenance VARCHAR(64) NOT NULL DEFAULT 'REAL_NASA_DATA',
                data_source TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (dataset_id, region_key, date, variable)
            );

            CREATE TABLE IF NOT EXISTS raw_parquet_index (
                partition_key VARCHAR(128) PRIMARY KEY,
                dataset_id VARCHAR(64) NOT NULL,
                region_key VARCHAR(64) NOT NULL,
                year INTEGER NOT NULL,
                variable VARCHAR(64) NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes BIGINT,
                record_count INTEGER,
                min_timestamp VARCHAR(32),
                max_timestamp VARCHAR(32),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_pg_monthly_lookup ON regional_monthly (dataset_id, region_key, date, variable);
            CREATE INDEX IF NOT EXISTS idx_pg_annual_lookup ON regional_annual (dataset_id, region_key, year, variable);

            CREATE TABLE IF NOT EXISTS analysis_jobs (
                job_id VARCHAR(64) PRIMARY KEY,
                cache_key VARCHAR(128),
                status VARCHAR(32) NOT NULL DEFAULT 'queued',
                progress_pct INTEGER DEFAULT 0,
                message TEXT,
                request_payload TEXT,
                result TEXT,
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_pg_jobs_cache_key ON analysis_jobs (cache_key);
            CREATE INDEX IF NOT EXISTS idx_pg_jobs_status ON analysis_jobs (status);
            """
            if self._driver == "psycopg2":
                with conn.cursor() as cur:
                    cur.execute(ddl)
                conn.commit()
            else:
                for statement in ddl.split(";"):
                    s = statement.strip()
                    if s:
                        conn.run(s)
            logger.info("PostgreSQL observation tables verified successfully.")
        except Exception as e:
            logger.error(f"PostgreSQL schema initialization error: {e}")
        finally:
            conn.close()

    def get_monthly_series(
        self,
        dataset_id: str,
        region_key: str,
        start_date: str,
        end_date: str,
        variable: str = "precipitationCal",
    ) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
        months = pd.date_range(start=start_date, end=end_date, freq="MS")
        all_month_strs = [m.strftime("%Y-%m") for m in months]

        t0 = time.perf_counter()
        conn = self._get_connection()
        try:
            sql = """
            SELECT dataset_id, region_key, date, variable, aggregation_method,
                   processing_version, value, units, valid_pixels, coverage_fraction,
                   n_observations, n_missing, fetch_time_ms, downloaded_bytes,
                   data_provenance, data_source
            FROM regional_monthly
            WHERE dataset_id = %s AND region_key = %s AND date >= %s AND date <= %s
              AND variable = %s
            ORDER BY date ASC, aggregation_method ASC
            """
            rows = []
            if self._driver == "psycopg2":
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (dataset_id, region_key, all_month_strs[0], all_month_strs[-1], variable))
                    rows = [dict(r) for r in cur.fetchall()]
            else:
                # pg8000
                cols = [
                    "dataset_id", "region_key", "date", "variable", "aggregation_method",
                    "processing_version", "value", "units", "valid_pixels", "coverage_fraction",
                    "n_observations", "n_missing", "fetch_time_ms", "downloaded_bytes",
                    "data_provenance", "data_source"
                ]
                res = conn.run(sql, dataset_id, region_key, all_month_strs[0], all_month_strs[-1], variable)
                rows = [dict(zip(cols, r)) for r in res]

            cached_map = {}
            for r in rows:
                m_date = r["date"]
                if m_date not in cached_map or r["aggregation_method"] == "FULL_30MIN_INTEGRAL":
                    cached_map[m_date] = dict(r)

            cached_records = []
            missing_months = []
            for m_str in all_month_strs:
                if m_str in cached_map:
                    cached_records.append(cached_map[m_str])
                else:
                    missing_months.append(m_str)

            lookup_ms = (time.perf_counter() - t0) * 1000.0
            cache_status = "HIT" if not missing_months else ("PARTIAL" if cached_records else "MISS")

            audit = {
                "cache_status": cache_status,
                "cache_hit": cache_status == "HIT",
                "cached_months_count": len(cached_records),
                "missing_months_count": len(missing_months),
                "lookup_duration_ms": round(lookup_ms, 3),
                "storage_type": "PostgreSQL (Managed External Database)",
                "data_provenance": cached_records[0]["data_provenance"] if cached_records else "REAL_NASA_DATA",
                "data_source": cached_records[0]["data_source"] if cached_records else "Microsoft Planetary Computer",
            }
            return cached_records, missing_months, audit
        finally:
            conn.close()

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
        if not records:
            return
        conn = self._get_connection()
        try:
            sql = """
            INSERT INTO regional_monthly (
                dataset_id, region_key, date, variable, aggregation_method, processing_version,
                value, units, valid_pixels, coverage_fraction, n_observations, n_missing,
                fetch_time_ms, downloaded_bytes, data_provenance, data_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (dataset_id, region_key, date, variable, aggregation_method, processing_version)
            DO UPDATE SET
                value = EXCLUDED.value,
                units = EXCLUDED.units,
                valid_pixels = EXCLUDED.valid_pixels,
                coverage_fraction = EXCLUDED.coverage_fraction,
                n_observations = EXCLUDED.n_observations,
                n_missing = EXCLUDED.n_missing,
                fetch_time_ms = EXCLUDED.fetch_time_ms,
                downloaded_bytes = EXCLUDED.downloaded_bytes,
                data_provenance = EXCLUDED.data_provenance,
                data_source = EXCLUDED.data_source,
                created_at = CURRENT_TIMESTAMP
            """
            params_list = [
                (
                    dataset_id,
                    region_key,
                    r["date"],
                    variable,
                    aggregation_method,
                    PROCESSING_VERSION,
                    r.get("value"),
                    r.get("units", units),
                    r.get("valid_pixels", 0),
                    r.get("coverage_fraction", 0.0),
                    r.get("n_observations", 0),
                    r.get("n_missing", 0),
                    r.get("fetch_time_ms", 0.0),
                    r.get("downloaded_bytes", 0),
                    data_provenance,
                    data_source,
                )
                for r in records
            ]
            if self._driver == "psycopg2":
                import psycopg2.extras
                with conn.cursor() as cur:
                    psycopg2.extras.execute_batch(cur, sql, params_list)
                conn.commit()
            else:
                for p in params_list:
                    conn.run(sql, *p)
            logger.info(f"Persisted {len(records)} observations into PostgreSQL ({dataset_id} | {region_key})")
        finally:
            conn.close()

    def persist_annual_series(
        self,
        dataset_id: str,
        region_key: str,
        annual_records: List[Dict[str, Any]],
        variable: str = "precipitationCal",
        data_provenance: str = "REAL_NASA_DATA",
        data_source: str = "Microsoft Planetary Computer",
    ):
        if not annual_records:
            return
        conn = self._get_connection()
        try:
            sql = """
            INSERT INTO regional_annual (
                dataset_id, region_key, year, variable, processing_version,
                annual_mean, annual_sum, n_months, std_dev, cv,
                data_provenance, data_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (dataset_id, region_key, year, variable, processing_version)
            DO UPDATE SET
                annual_mean = EXCLUDED.annual_mean,
                annual_sum = EXCLUDED.annual_sum,
                n_months = EXCLUDED.n_months,
                std_dev = EXCLUDED.std_dev,
                cv = EXCLUDED.cv,
                data_provenance = EXCLUDED.data_provenance,
                data_source = EXCLUDED.data_source,
                created_at = CURRENT_TIMESTAMP
            """
            params_list = [
                (
                    dataset_id,
                    region_key,
                    int(a["year"]),
                    variable,
                    PROCESSING_VERSION,
                    a.get("annual_mean"),
                    a.get("annual_sum"),
                    a.get("n_months"),
                    a.get("std_dev"),
                    a.get("cv"),
                    data_provenance,
                    data_source,
                )
                for a in annual_records
            ]
            if self._driver == "psycopg2":
                import psycopg2.extras
                with conn.cursor() as cur:
                    psycopg2.extras.execute_batch(cur, sql, params_list)
                conn.commit()
            else:
                for p in params_list:
                    conn.run(sql, *p)
        finally:
            conn.close()

    def get_storage_stats(self) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            if self._driver == "psycopg2":
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM regional_monthly")
                    m_count = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM regional_annual")
                    a_count = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM regional_daily")
                    d_count = cur.fetchone()[0]
            else:
                m_count = conn.run("SELECT count(*) FROM regional_monthly")[0][0]
                a_count = conn.run("SELECT count(*) FROM regional_annual")[0][0]
                d_count = conn.run("SELECT count(*) FROM regional_daily")[0][0]
            return {
                "engine": "postgresql",
                "cached_monthly_records": m_count,
                "cached_annual_records": a_count,
                "cached_daily_records": d_count,
                "processing_version": PROCESSING_VERSION,
            }
        finally:
            conn.close()

    def get_cache_summary(self) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            sql = """
            SELECT dataset_id, region_key, variable,
                   COUNT(*) as cached_months,
                   MIN(date) as min_date,
                   MAX(date) as max_date,
                   MAX(created_at) as last_updated
            FROM regional_monthly
            GROUP BY dataset_id, region_key, variable
            ORDER BY dataset_id, region_key
            """
            entries = []
            if self._driver == "psycopg2":
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql)
                    for r in cur.fetchall():
                        entries.append({
                            "dataset_id": r["dataset_id"],
                            "region_key": r["region_key"],
                            "variable": r["variable"],
                            "cached_months": int(r["cached_months"]),
                            "target_period": "2015-01 to 2020-12 (72 months)",
                            "is_72_complete": int(r["cached_months"]) >= 72,
                            "min_date": r["min_date"],
                            "max_date": r["max_date"],
                            "last_updated": str(r["last_updated"]),
                        })
            else:
                res = conn.run(sql)
                for r in res:
                    entries.append({
                        "dataset_id": r[0],
                        "region_key": r[1],
                        "variable": r[2],
                        "cached_months": int(r[3]),
                        "target_period": "2015-01 to 2020-12 (72 months)",
                        "is_72_complete": int(r[3]) >= 72,
                        "min_date": r[4],
                        "max_date": r[5],
                        "last_updated": str(r[6]),
                    })
            stats = self.get_storage_stats()
            return {
                "status": "ok",
                "engine": "postgresql",
                "storage": stats,
                "cached_series_count": len(entries),
                "series": entries,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            conn.close()

    def create_job(
        self,
        job_id: str,
        cache_key: str,
        status: str = "queued",
        progress_pct: int = 0,
        message: str = "",
        request_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        import json
        payload_str = json.dumps(request_payload, default=str) if request_payload else None
        now_ts = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            sql = """
            INSERT INTO analysis_jobs (
                job_id, cache_key, status, progress_pct, message,
                request_payload, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (job_id) DO UPDATE SET
                cache_key = EXCLUDED.cache_key,
                status = EXCLUDED.status,
                progress_pct = EXCLUDED.progress_pct,
                message = EXCLUDED.message,
                request_payload = EXCLUDED.request_payload,
                updated_at = CURRENT_TIMESTAMP
            """
            if self._driver == "psycopg2":
                with conn.cursor() as cur:
                    cur.execute(sql, (job_id, cache_key, status, progress_pct, message, payload_str))
                conn.commit()
            else:
                conn.run(sql, job_id, cache_key, status, progress_pct, message, payload_str)
            return {
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
        finally:
            conn.close()

    def update_job(
        self,
        job_id: str,
        status: str,
        progress_pct: int,
        message: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        import json
        res_str = json.dumps(result, default=str) if result is not None else None
        conn = self._get_connection()
        try:
            sql = """
            UPDATE analysis_jobs
            SET status = %s,
                progress_pct = %s,
                message = %s,
                result = COALESCE(%s, result),
                error = COALESCE(%s, error),
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = %s
            """
            if self._driver == "psycopg2":
                with conn.cursor() as cur:
                    cur.execute(sql, (status, progress_pct, message, res_str, error, job_id))
                conn.commit()
            else:
                conn.run(sql, status, progress_pct, message, res_str, error, job_id)
            return self.get_job(job_id)
        finally:
            conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        import json
        conn = self._get_connection()
        try:
            sql = """
            SELECT job_id, cache_key, status, progress_pct, message,
                   request_payload, result, error, created_at, updated_at
            FROM analysis_jobs
            WHERE job_id = %s
            """
            row = None
            if self._driver == "psycopg2":
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (job_id,))
                    res = cur.fetchone()
                    if res:
                        row = dict(res)
            else:
                cols = [
                    "job_id", "cache_key", "status", "progress_pct", "message",
                    "request_payload", "result", "error", "created_at", "updated_at"
                ]
                res = conn.run(sql, job_id)
                if res:
                    row = dict(zip(cols, res[0]))

            if not row:
                return None

            row["progress"] = row.get("progress_pct", 0)
            if row.get("result"):
                try:
                    row["result"] = json.loads(row["result"])
                except Exception:
                    pass
            if row.get("request_payload"):
                try:
                    row["request_payload"] = json.loads(row["request_payload"])
                except Exception:
                    pass
            if row.get("created_at"):
                row["created_at"] = str(row["created_at"])
            if row.get("updated_at"):
                row["updated_at"] = str(row["updated_at"])
            return row
        finally:
            conn.close()

    def get_job_by_cache_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        import json
        conn = self._get_connection()
        try:
            sql = """
            SELECT job_id, cache_key, status, progress_pct, message,
                   request_payload, result, error, created_at, updated_at
            FROM analysis_jobs
            WHERE cache_key = %s AND status IN ('queued', 'processing', 'running', 'completed')
            ORDER BY created_at DESC LIMIT 1
            """
            row = None
            if self._driver == "psycopg2":
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (cache_key,))
                    res = cur.fetchone()
                    if res:
                        row = dict(res)
            else:
                cols = [
                    "job_id", "cache_key", "status", "progress_pct", "message",
                    "request_payload", "result", "error", "created_at", "updated_at"
                ]
                res = conn.run(sql, cache_key)
                if res:
                    row = dict(zip(cols, res[0]))

            if not row:
                return None

            row["progress"] = row.get("progress_pct", 0)
            if row.get("result"):
                try:
                    row["result"] = json.loads(row["result"])
                except Exception:
                    pass
            if row.get("request_payload"):
                try:
                    row["request_payload"] = json.loads(row["request_payload"])
                except Exception:
                    pass
            if row.get("created_at"):
                row["created_at"] = str(row["created_at"])
            if row.get("updated_at"):
                row["updated_at"] = str(row["updated_at"])
            return row
        finally:
            conn.close()

    def clean_expired_jobs(self, max_age_seconds: int = 86400):
        conn = self._get_connection()
        try:
            sql = f"DELETE FROM analysis_jobs WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '{int(max_age_seconds)} seconds'"
            if self._driver == "psycopg2":
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
            else:
                conn.run(sql)
        except Exception as e:
            logger.warning(f"Error cleaning expired PostgreSQL jobs: {e}")
        finally:
            conn.close()



def create_database_engine(db_path: str, parquet_dir: str) -> BaseDatabaseEngine:
    """
    Factory to instantiate the appropriate database engine.
    If DATABASE_URL or POSTGRES_URL is set, switches to PostgreSQLEngine for permanent cloud persistence.
    Otherwise, defaults to SQLiteEngine for zero-configuration local development.
    """
    pg_url = (
        os.environ.get("POSTGRES_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("BHIMA_POSTGRES_URL")
    )
    if pg_url:
        try:
            return PostgreSQLEngine(connection_url=pg_url)
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL ({e}). Falling back to SQLite.")

    return SQLiteEngine(db_path=db_path, parquet_dir=parquet_dir)
