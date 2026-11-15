import os
import sys
import uuid
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("neon-test")

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from app.core.db_engine import (
    PostgreSQLEngine,
    get_postgres_url,
    sanitize_postgres_url,
)
from app.core.job_store import JobStore


def run_neon_test():
    logger.info("=" * 70)
    logger.info("BHIMA NEON POSTGRESQL WORKFLOW VERIFICATION")
    logger.info("=" * 70)

    pg_url = get_postgres_url()
    if not pg_url:
        logger.warning(
            "No PostgreSQL/Neon URL found in environment (DATABASE_URL, NEON_DATABASE_URL, or POSTGRES_URL). "
            "To test against live Neon database, pass DATABASE_URL='postgresql://...' and re-run."
        )
        return True

    sanitized = sanitize_postgres_url(pg_url)
    logger.info(f"Target Neon Database: {sanitized}")

    # 1. Connect and initialize schema
    logger.info("[Step 1] Connecting to Neon and verifying schema...")
    engine = PostgreSQLEngine(connection_url=pg_url)
    stats = engine.get_storage_stats()
    logger.info(f"  -> Connected successfully! Storage stats: {stats}")

    # 2. Test job creation
    test_job_id = f"bhima-test-{uuid.uuid4().hex[:8]}"
    test_cache_key = f"cache-{uuid.uuid4().hex[:12]}"
    logger.info(f"[Step 2] Creating test job {test_job_id}...")

    created = engine.create_job(
        job_id=test_job_id,
        cache_key=test_cache_key,
        status="processing",
        progress_pct=15,
        message="Simulating Neon serverless job execution...",
        request_payload={"region": "Gujarat, India", "start_date": "2015-01", "end_date": "2020-12"},
    )
    assert created["job_id"] == test_job_id
    assert created["status"] == "processing"
    assert created["progress_pct"] == 15
    logger.info(f"  -> Job created: status={created['status']}, progress={created['progress_pct']}%")

    # 3. Test retrieving from separate request / fresh connection
    logger.info(f"[Step 3] Retrieving job {test_job_id} from a separate connection...")
    retrieved = engine.get_job(test_job_id)
    assert retrieved is not None, f"Job {test_job_id} not found in Neon!"
    assert retrieved["job_id"] == test_job_id
    assert retrieved["status"] == "processing"
    assert retrieved["progress_pct"] == 15
    assert retrieved["request_payload"]["region"] == "Gujarat, India"
    logger.info(f"  -> Job retrieved successfully from separate query: {retrieved['job_id']}")

    # 4. Test updating status
    logger.info(f"[Step 4] Updating job {test_job_id} to 'completed' with payload...")
    mock_result = {
        "analysis_id": "test-analysis-123",
        "data_provenance": "REAL_NASA_DATA",
        "summary": "Verified on Neon PostgreSQL",
    }
    updated = engine.update_job(
        job_id=test_job_id,
        status="completed",
        progress_pct=100,
        message="Analysis completed successfully on Neon.",
        result=mock_result,
    )
    assert updated is not None
    assert updated["status"] == "completed"
    assert updated["progress_pct"] == 100
    assert updated["result"] == mock_result
    logger.info(f"  -> Job updated successfully: status={updated['status']}, progress={updated['progress_pct']}%")

    # 5. Verify persistence
    final_check = engine.get_job(test_job_id)
    assert final_check["status"] == "completed"
    assert final_check["result"]["summary"] == "Verified on Neon PostgreSQL"
    logger.info("  -> Final persistence check: PASSED (100% verified)")

    # 6. Cleanup test job
    logger.info("[Step 6] Cleaning up test record...")
    conn = engine._get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM analysis_jobs WHERE job_id = %s", (test_job_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    logger.info("  -> Cleanup complete.")

    logger.info("=" * 70)
    logger.info("ALL NEON POSTGRESQL WORKFLOW TESTS PASSED SUCCESSFULLY!")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    success = run_neon_test()
    if not success:
        sys.exit(1)
