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


def test_julian_calendar_decoding_and_slicing():
    """
    Regression test for:
    'Failed to decode variable time: unable to decode time units minutes since 2000-06-01 00:00:00 with calendar julian'
    Verifies that cftime correctly decodes Julian calendar time coordinates and enables xarray time slicing.
    """
    import cftime
    import xarray as xr
    import numpy as np

    units = "minutes since 2000-06-01 00:00:00"
    calendar_name = "julian"

    # Half-hourly steps for 2 days (48 steps/day = 96 steps)
    minute_offsets = np.arange(0, 96 * 30, 30, dtype=np.int64)
    decoded_times = cftime.num2date(minute_offsets, units=units, calendar=calendar_name)

    assert len(decoded_times) == 96
    assert isinstance(decoded_times[0], cftime.DatetimeJulian)
    assert decoded_times[0].year == 2000
    assert decoded_times[0].month == 6
    assert decoded_times[0].day == 1
    assert decoded_times[0].hour == 0
    assert decoded_times[0].minute == 0

    # Build xarray dataset with DatetimeJulian coordinate
    ds = xr.Dataset(
        {"precipitationCal": (["time", "lat", "lon"], np.random.uniform(0, 10, size=(96, 2, 2)))},
        coords={
            "time": decoded_times,
            "lat": [20.0, 20.1],
            "lon": [70.0, 70.1],
        },
    )

    # Test time string slicing on cftime.DatetimeJulian
    sub = ds.sel(time=slice("2000-06-01 00:00", "2000-06-01 05:30"))
    assert len(sub.time) == 12  # 12 half-hourly steps in 6 hours
    assert sub["precipitationCal"].mean() >= 0.0

    # Test decode_times=False fallback simulation
    ds_raw = xr.Dataset(
        {"precipitationCal": (["time"], np.arange(10, dtype=float))},
        coords={"time": np.arange(0, 300, 30, dtype=np.int64)},
    )
    ds_raw.time.attrs["units"] = units
    ds_raw.time.attrs["calendar"] = calendar_name

    # Decode via fallback path
    fallback_decoded = cftime.num2date(
        ds_raw.time.values,
        units=ds_raw.time.attrs["units"],
        calendar=ds_raw.time.attrs["calendar"],
    )
    ds_raw["time"] = ("time", fallback_decoded, ds_raw.time.attrs)
    assert isinstance(ds_raw.time.values[0], cftime.DatetimeJulian)
    assert str(ds_raw.time.values[0]) == "2000-06-01 00:00:00"


def test_sanitize_postgres_url():
    """Verify that credentials and tokens are always masked in diagnostic logging."""
    from app.core.db_engine import sanitize_postgres_url

    raw_url = "postgresql://neondb_owner:npg_SecretPass123!@ep-cool-fog-123456.us-east-2.aws.neon.tech:5432/neondb?sslmode=require"
    sanitized = sanitize_postgres_url(raw_url)

    assert "npg_SecretPass123!" not in sanitized
    assert "****" in sanitized
    assert "neondb_owner" in sanitized
    assert "ep-cool-fog-123456.us-east-2.aws.neon.tech" in sanitized
    assert "neondb" in sanitized

    # Empty / none check
    assert sanitize_postgres_url(None) == "<none>"
    assert sanitize_postgres_url("") == "<none>"


def test_neon_env_detection(monkeypatch):
    """Verify that get_postgres_url reads Neon and Vercel variables in priority order."""
    from app.core.db_engine import get_postgres_url

    # Clean existing
    for k in ["NEON_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL", "POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD"]:
        monkeypatch.delenv(k, raising=False)

    assert get_postgres_url() is None

    # NEON_DATABASE_URL
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql://user:pass@neon.tech/db")
    assert get_postgres_url() == "postgresql://user:pass@neon.tech/db"

    # DATABASE_URL override
    monkeypatch.delenv("NEON_DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@neon-pooler.tech/db?sslmode=require")
    assert get_postgres_url() == "postgres://user:pass@neon-pooler.tech/db?sslmode=require"

    # POSTGRES_URL override
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.setenv("POSTGRES_URL", "postgres://user:pass@vercel.tech/db")
    assert get_postgres_url() == "postgres://user:pass@vercel.tech/db"

