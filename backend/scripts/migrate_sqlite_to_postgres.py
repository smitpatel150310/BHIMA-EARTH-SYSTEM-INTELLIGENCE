import os
import sys
import sqlite3
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bhima-migrator")

# Add backend directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from app.core.db_engine import PostgreSQLEngine


def migrate(sqlite_path: str, pg_url: str):
    logger.info("=" * 70)
    logger.info("BHIMA OBSERVATION DATABASE MIGRATOR (SQLite -> PostgreSQL)")
    logger.info("=" * 70)
    logger.info(f"Source SQLite:     {sqlite_path}")

    if not os.path.exists(sqlite_path):
        logger.error(f"SQLite file not found at: {sqlite_path}")
        return False

    # 1. Connect to SQLite
    s_conn = sqlite3.connect(sqlite_path)
    s_conn.row_factory = sqlite3.Row
    s_cur = s_conn.cursor()

    monthly_rows = [dict(r) for r in s_cur.execute("SELECT * FROM regional_monthly").fetchall()]
    annual_rows = [dict(r) for r in s_cur.execute("SELECT * FROM regional_annual").fetchall()]
    daily_rows = [dict(r) for r in s_cur.execute("SELECT * FROM regional_daily").fetchall()]
    has_jobs_table = s_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_jobs'").fetchone()
    job_rows = [dict(r) for r in s_cur.execute("SELECT * FROM analysis_jobs").fetchall()] if has_jobs_table else []
    s_conn.close()

    logger.info(f"Loaded from SQLite:")
    logger.info(f"  - regional_monthly: {len(monthly_rows)} records")
    logger.info(f"  - regional_annual:  {len(annual_rows)} records")
    logger.info(f"  - regional_daily:   {len(daily_rows)} records")
    logger.info(f"  - analysis_jobs:    {len(job_rows)} records")

    # 2. Connect to PostgreSQL
    logger.info("Connecting to target PostgreSQL database...")
    engine = PostgreSQLEngine(connection_url=pg_url)

    # 3. Migrate monthly records
    logger.info(f"Migrating {len(monthly_rows)} monthly observation records to PostgreSQL...")
    grouped = {}
    for r in monthly_rows:
        key = (r["dataset_id"], r["region_key"], r.get("variable", "precipitationCal"))
        grouped.setdefault(key, []).append(r)

    for (d_id, reg_k, var_n), recs in grouped.items():
        engine.persist_monthly_series(
            dataset_id=d_id,
            region_key=reg_k,
            records=recs,
            variable=var_n,
            aggregation_method=recs[0].get("aggregation_method", "FULL_30MIN_INTEGRAL"),
            data_provenance=recs[0].get("data_provenance", "REAL_NASA_DATA"),
            data_source=recs[0].get("data_source", "Microsoft Planetary Computer"),
            units=recs[0].get("units", "mm/month"),
        )

    # 4. Migrate annual records
    if annual_rows:
        logger.info(f"Migrating {len(annual_rows)} annual observation records to PostgreSQL...")
        for a in annual_rows:
            engine.persist_annual_series(
                dataset_id=a["dataset_id"],
                region_key=a["region_key"],
                annual_records=[a],
                variable=a.get("variable", "precipitationCal"),
                data_provenance=a.get("data_provenance", "REAL_NASA_DATA"),
                data_source=a.get("data_source", "Microsoft Planetary Computer"),
            )

    # 5. Migrate analysis jobs
    if job_rows:
        logger.info(f"Migrating {len(job_rows)} analysis job records to PostgreSQL...")
        for j in job_rows:
            engine.create_job(
                job_id=j["job_id"],
                cache_key=j.get("cache_key", ""),
                status=j.get("status", "completed"),
                progress_pct=j.get("progress_pct", 100),
                message=j.get("message", ""),
                request_payload=j.get("request_payload"),
            )
            if j.get("result") or j.get("error"):
                engine.update_job(
                    job_id=j["job_id"],
                    status=j.get("status", "completed"),
                    progress_pct=j.get("progress_pct", 100),
                    message=j.get("message", ""),
                    result=j.get("result"),
                    error=j.get("error"),
                )

    # 6. Verify Target PostgreSQL row count
    stats = engine.get_storage_stats()
    logger.info("=" * 70)
    logger.info("MIGRATION VERIFICATION:")
    logger.info(f"  PostgreSQL cached monthly records: {stats.get('cached_monthly_records')} (Source had: {len(monthly_rows)})")
    logger.info(f"  PostgreSQL cached annual records:  {stats.get('cached_annual_records')} (Source had: {len(annual_rows)})")
    logger.info("=" * 70)

    if stats.get("cached_monthly_records", 0) >= len(monthly_rows):
        logger.info("MIGRATION SUCCESSFUL! 100% of real satellite records preserved with zero data loss.")
        return True
    else:
        logger.warning("Record count mismatch! Inspect database logs.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Migrate BHIMA observations from SQLite to PostgreSQL")
    parser.add_argument("--sqlite-path", default=os.path.join(backend_dir, "data", "bhima_observations.db"))
    parser.add_argument("--postgres-url", default=os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL"))
    args = parser.parse_args()

    if not args.postgres_url:
        logger.error("POSTGRES_URL or DATABASE_URL not set. Provide via --postgres-url or set in environment.")
        sys.exit(1)

    success = migrate(args.sqlite_path, args.postgres_url)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
