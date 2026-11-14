import os
import sqlite3
import logging
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "bhima_observations.db")
)


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_cache_db():
    """Ensure database and tables are created with comprehensive provenance and metadata."""
    conn = get_db_connection()
    try:
        with conn:
            # Regional monthly/period observations
            conn.execute("""
            CREATE TABLE IF NOT EXISTS regional_monthly (
                dataset_id TEXT NOT NULL,
                region_key TEXT NOT NULL,
                date TEXT NOT NULL,
                variable TEXT NOT NULL DEFAULT 'precipitationCal',
                aggregation_method TEXT NOT NULL DEFAULT 'FULL_30MIN_INTEGRAL',
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
                PRIMARY KEY (dataset_id, region_key, date, variable, aggregation_method)
            )
            """)

            # High-resolution daily observations for granular validation
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
            CREATE INDEX IF NOT EXISTS idx_reg_monthly_lookup
            ON regional_monthly (dataset_id, region_key, date, variable, aggregation_method)
            """)
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reg_daily_lookup
            ON regional_daily (dataset_id, region_key, date, variable)
            """)
    finally:
        conn.close()


def get_region_key(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    """Deterministic string key for spatial bounding box formatted to 2 decimal places."""
    return f"{float(min_lon):.2f}_{float(min_lat):.2f}_{float(max_lon):.2f}_{float(max_lat):.2f}"


def get_cached_monthly_records(
    dataset_id: str,
    region_key: str,
    start_date: str,
    end_date: str,
    variable: str = "precipitationCal",
    aggregation_method: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Look up monthly records in SQLite.
    Returns:
        (cached_records, missing_month_strings)
    """
    init_cache_db()
    months = pd.date_range(start=start_date, end=end_date, freq="MS")
    all_month_strs = [m.strftime("%Y-%m") for m in months]

    if not all_month_strs:
        return [], []

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if aggregation_method:
            query = """
                SELECT * FROM regional_monthly
                WHERE dataset_id = ? AND region_key = ? AND date >= ? AND date <= ?
                  AND variable = ? AND aggregation_method = ?
                ORDER BY date ASC
            """
            params = (dataset_id, region_key, all_month_strs[0], all_month_strs[-1], variable, aggregation_method)
        else:
            query = """
                SELECT * FROM regional_monthly
                WHERE dataset_id = ? AND region_key = ? AND date >= ? AND date <= ?
                  AND variable = ?
                ORDER BY date ASC, aggregation_method ASC
            """
            params = (dataset_id, region_key, all_month_strs[0], all_month_strs[-1], variable)

        cur.execute(query, params)
        rows = cur.fetchall()
        cached_dict = {}
        for r in rows:
            # If multiple methods exist, prefer FULL_30MIN_INTEGRAL over sampling
            m_date = r["date"]
            if m_date not in cached_dict or r["aggregation_method"] == "FULL_30MIN_INTEGRAL":
                cached_dict[m_date] = dict(r)

        cached_records = []
        missing_months = []
        for m_str in all_month_strs:
            if m_str in cached_dict:
                cached_records.append(cached_dict[m_str])
            else:
                missing_months.append(m_str)

        return cached_records, missing_months
    finally:
        conn.close()


def save_monthly_records(
    dataset_id: str,
    region_key: str,
    records: List[Dict[str, Any]],
    variable: str = "precipitationCal",
    aggregation_method: str = "FULL_30MIN_INTEGRAL",
    data_provenance: str = "REAL_NASA_DATA",
    data_source: str = "Microsoft Planetary Computer",
    units: str = "mm/month",
):
    """Save or update observation records into the SQLite cache with full provenance."""
    if not records:
        return

    init_cache_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO regional_monthly (
                    dataset_id, region_key, date, variable, aggregation_method,
                    value, units, valid_pixels, coverage_fraction, n_observations, n_missing,
                    fetch_time_ms, downloaded_bytes, data_provenance, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        dataset_id,
                        region_key,
                        r["date"],
                        r.get("variable", variable),
                        r.get("aggregation_method", aggregation_method),
                        r.get("value"),
                        r.get("units", units),
                        r.get("valid_pixels", 0),
                        r.get("coverage_fraction", 0.0),
                        r.get("n_observations", 0),
                        r.get("n_missing", 0),
                        r.get("fetch_time_ms", 0.0),
                        r.get("downloaded_bytes", 0),
                        r.get("data_provenance", data_provenance),
                        r.get("data_source", data_source),
                    )
                    for r in records
                ],
            )
        logger.info(
            f"Persisted {len(records)} observations for {dataset_id}:{region_key} "
            f"(method={aggregation_method}) into SQLite."
        )
    finally:
        conn.close()


def save_daily_records(
    dataset_id: str,
    region_key: str,
    daily_records: List[Dict[str, Any]],
    variable: str = "precipitationCal",
    data_provenance: str = "REAL_NASA_DATA",
    data_source: str = "Microsoft Planetary Computer",
):
    """Save daily observations for granular aggregation and audit."""
    if not daily_records:
        return

    init_cache_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO regional_daily (
                    dataset_id, region_key, date, variable, mean_rate_mm_hr,
                    accum_mm, valid_steps, missing_steps, data_provenance, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        dataset_id,
                        region_key,
                        d["date"],
                        variable,
                        d.get("mean_rate_mm_hr"),
                        d.get("accum_mm"),
                        d.get("valid_steps", 48),
                        d.get("missing_steps", 0),
                        data_provenance,
                        data_source,
                    )
                    for d in daily_records
                ],
            )
    finally:
        conn.close()
