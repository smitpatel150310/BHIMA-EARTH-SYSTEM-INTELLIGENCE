import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.job_store import job_store

client = TestClient(app)


def test_job_store_crud():
    test_id = f"test-{uuid.uuid4().hex[:10]}"
    cache_key = f"ck-{uuid.uuid4().hex[:10]}"

    # 1. Create job
    created = job_store.create_job(
        job_id=test_id,
        cache_key=cache_key,
        status="processing",
        progress_pct=15,
        message="Starting test processing...",
        request_payload={"region": "Gujarat"},
    )
    assert created["job_id"] == test_id
    assert created["status"] == "processing"
    assert created["progress_pct"] == 15
    assert created["progress"] == 15

    # 2. Retrieve job from memory / persistent store
    retrieved = job_store.get_job(test_id)
    assert retrieved is not None
    assert retrieved["job_id"] == test_id
    assert retrieved["status"] == "processing"

    # 3. Simulate new serverless container (wipe memory cache)
    job_store._mem_cache.clear()
    job_store._cache_key_to_id.clear()

    # Must still retrieve from persistent database (SQLite / Postgres)!
    from_db = job_store.get_job(test_id)
    assert from_db is not None, "Failed cross-container persistence test: job must exist in database!"
    assert from_db["job_id"] == test_id
    assert from_db["status"] == "processing"
    assert from_db["progress_pct"] == 15

    # 4. Update job
    mock_result = {"status": "ok", "value": 42.0}
    updated = job_store.update_job(
        job_id=test_id,
        status="completed",
        progress_pct=100,
        message="Finished successfully.",
        result=mock_result,
    )
    assert updated is not None
    assert updated["status"] == "completed"
    assert updated["progress_pct"] == 100
    assert updated["result"] == mock_result

    # 5. Simulate new container again
    job_store._mem_cache.clear()
    job_store._cache_key_to_id.clear()
    final_job = job_store.get_job(test_id)
    assert final_job is not None
    assert final_job["status"] == "completed"
    assert final_job["result"] == mock_result


def test_api_timeseries_async_and_poll():
    """
    Test the exact workflow that failed in production:
    1. POST /analysis/timeseries?async_mode=true
    2. Frontend immediately polls GET /analysis/jobs/{job_id}
    Verify that GET /analysis/jobs/{job_id} NEVER returns 404 for a valid job!
    """
    payload = {
        "dataset_id": "terraclimate_ppt",
        "region": {
            "name": "Gujarat, India",
            "min_lon": 68.1,
            "max_lon": 74.5,
            "min_lat": 20.1,
            "max_lat": 24.7,
        },
        "start_date": "2015-01",
        "end_date": "2020-12",
        "temporal_resolution": "monthly",
    }

    # If already cached, this might return direct 200 or an async job if missing
    resp = client.post("/analysis/timeseries?async_mode=true", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # If it returned a job_id (async mode):
    if "job_id" in data:
        job_id = data["job_id"]
        assert data["status"] in ("processing", "queued", "completed")

        # Simulate second container receiving the poll request:
        job_store._mem_cache.clear()
        job_store._cache_key_to_id.clear()

        # Polling MUST return HTTP 200, NOT 404!
        poll_resp = client.get(f"/analysis/jobs/{job_id}")
        assert poll_resp.status_code == 200, f"Expected 200 from polling but got {poll_resp.status_code}: {poll_resp.text}"
        poll_data = poll_resp.json()
        assert poll_data["job_id"] == job_id
        assert poll_data["status"] in ("processing", "queued", "completed")
        assert "progress_pct" in poll_data
        assert "progress" in poll_data


def test_api_jobs_nonexistent_returns_404():
    """Verify that truly nonexistent jobs return 404 with standard message."""
    resp = client.get("/analysis/jobs/nonexistent-job-9999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
